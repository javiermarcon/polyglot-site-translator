"""BDD steps for PO processing workflows."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shelve
import tempfile
from typing import Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]
import polib

from polyglot_site_translator.domain.framework_detection.models import FrameworkDetectionResult
from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingCompilationError,
    POProcessingTranslationError,
)
from polyglot_site_translator.domain.po_processing.models import (
    POFileData,
    POProcessingProgress,
)
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionTestResult,
)
from polyglot_site_translator.domain.site_registry.errors import SiteRegistryNotFoundError
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.domain.sync.models import (
    SyncDirection,
    SyncProgressEvent,
    SyncResult,
    SyncSummary,
)
from polyglot_site_translator.infrastructure.po_files import PolibPOCatalogRepository
from polyglot_site_translator.presentation.site_registry_services import (
    SiteRegistryPresentationWorkflowService,
)
from polyglot_site_translator.presentation.view_models import (
    TranslationOptionsViewModel,
    TranslationWorkflowRequestViewModel,
)
from polyglot_site_translator.services.po_processing import POProcessingService

StepFunction = TypeVar("StepFunction", bound=Callable[..., object])
_TWO_FAMILIES = 2

given = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.given)
when = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.when)
then = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.then)


class _BehavePOContext(Protocol):
    workflow_service: SiteRegistryPresentationWorkflowService
    po_result_status: str
    po_result_families: int
    po_result_summary: str
    processed_po_text: str
    compiled_mo_paths: tuple[Path, ...]
    po_progress_events: list[POProcessingProgress]
    temp_dir: tempfile.TemporaryDirectory[str]
    site_id: str
    site: RegisteredSite


class _InMemorySiteWorkflowService:
    def __init__(self, site: RegisteredSite) -> None:
        self._site = site

    def get_site(self, site_id: str) -> RegisteredSite:
        if site_id != self._site.id:
            msg = f"Unknown site id: {site_id}"
            raise SiteRegistryNotFoundError(msg)
        return self._site

    @staticmethod
    def detect_framework(project_path: str) -> FrameworkDetectionResult:
        return FrameworkDetectionResult.unmatched(
            project_path=project_path,
            warnings=["Framework detection not required for PO workflow BDD."],
        )

    @staticmethod
    def test_remote_connection(registration: object) -> RemoteConnectionTestResult:
        return RemoteConnectionTestResult(
            success=True,
            connection_type="none",
            host="",
            port=0,
            message="Remote connection test is not required for this BDD flow.",
            error_code=None,
        )


class _SyncStub:
    @staticmethod
    def sync_remote_to_local(
        site: RegisteredSite,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncResult:
        return SyncResult(
            direction=SyncDirection.REMOTE_TO_LOCAL,
            success=True,
            project_id=site.id,
            connection_type=None,
            local_path=site.local_path,
            summary=SyncSummary(
                files_discovered=0,
                files_downloaded=0,
                directories_created=0,
                bytes_downloaded=0,
            ),
            error=None,
        )

    @staticmethod
    def sync_local_to_remote(
        site: RegisteredSite,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncResult:
        return SyncResult(
            direction=SyncDirection.LOCAL_TO_REMOTE,
            success=True,
            project_id=site.id,
            connection_type=None,
            local_path=site.local_path,
            summary=SyncSummary(
                files_discovered=0,
                files_downloaded=0,
                directories_created=0,
                bytes_downloaded=0,
                files_uploaded=0,
                bytes_uploaded=0,
            ),
            error=None,
        )


class _BehaveTranslationProvider:
    @staticmethod
    def translate_text(*, text: str, target_locale: str) -> str:
        translations = {
            ("es_ES", "Save"): "Guardar",
            ("es_AR", "Save"): "Guardar",
            ("es_ES", "Title"): "Titulo",
            ("es_ES", "Price"): "Precio",
        }
        return translations[(target_locale, text)]


class _BehavePartiallyFailingTranslationProvider:
    @staticmethod
    def translate_text(*, text: str, target_locale: str) -> str:
        if text == "Broken":
            msg = f"provider exploded for {target_locale}:{text}"
            raise POProcessingTranslationError(msg)
        translations = {
            ("es_ES", "Save"): "Guardar",
        }
        return translations[(target_locale, text)]


class _CompileFailingRepository:
    def __init__(self) -> None:
        self._repository = PolibPOCatalogRepository()

    def discover_po_files(self, workspace_root: Path) -> tuple[POFileData, ...]:
        return self._repository.discover_po_files(workspace_root)

    def save_po_files(self, files: tuple[POFileData, ...]) -> None:
        self._repository.save_po_files(files)

    def compile_mo_file(self, file_data: POFileData) -> None:
        if file_data.locale == "es_ES":
            msg = f"PO file '{file_data.source_path}' could not be compiled in the BDD stub."
            raise POProcessingCompilationError(msg)
        self._repository.compile_mo_file(file_data)


def _seed_translation_cache(workspace: Path, *, text: str, translated_text: str) -> None:
    cache_path = workspace / ".po_translation_cache"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with shelve.open(str(cache_path), writeback=False) as cache:
        cache[f"es\x1f{text}"] = translated_text


def _context(context: object) -> _BehavePOContext:
    return cast(_BehavePOContext, context)


@given("a site project with PO locale variants in the local workspace")
def step_given_site_with_variants(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(
        locale_dir / "messages-es_ES.po",
        [
            ("Hello", "Hola"),
        ],
    )
    _write_po(
        locale_dir / "messages-es_AR.po",
        [
            ("Hello", ""),
        ],
    )
    site = _build_site(workspace)
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(),
    )


@given("a site project with untranslated PO locale variants in the local workspace")
def step_given_site_with_untranslated_variants(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Save", "")])
    _write_po(locale_dir / "messages-es_AR.po", [("Save", "")])
    site = _build_site(workspace)
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(
            translation_provider=_BehaveTranslationProvider()
        ),
    )


@given("a site project with untranslated PO locale variants and MO compilation disabled")
def step_given_site_with_untranslated_variants_and_disabled_mo(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Save", "")])
    _write_po(locale_dir / "messages-es_AR.po", [("Save", "")])
    site = _build_site(workspace, modes={"compile_mo": False})
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(
            translation_provider=_BehaveTranslationProvider()
        ),
    )


@given("a site project with untranslated PO locale variants and external translator disabled")
def step_given_site_with_untranslated_variants_and_disabled_external_translator(
    context: object,
) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Save", "")])
    _write_po(locale_dir / "messages-es_AR.po", [("Save", "")])
    site = _build_site(workspace, modes={"use_external_translator": False})
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(
            translation_provider=_BehaveTranslationProvider()
        ),
    )


@given("a site project with untranslated PO locale variants and dry-run enabled")
def step_given_site_with_untranslated_variants_and_dry_run(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Save", "")])
    _write_po(locale_dir / "messages-es_AR.po", [("Save", "")])
    site = _build_site(workspace, modes={"dry_run": True})
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(
            translation_provider=_BehaveTranslationProvider()
        ),
    )


@given("a site project with untranslated PO locale variants and stats-only enabled")
def step_given_site_with_untranslated_variants_and_stats_only(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Save", "")])
    _write_po(locale_dir / "messages-es_AR.po", [("Save", "")])
    site = _build_site(workspace, modes={"stats_only": True})
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(
            translation_provider=_BehaveTranslationProvider()
        ),
    )


@given("a site project with fuzzy and non-fuzzy untranslated PO entries")
def step_given_site_with_fuzzy_and_non_fuzzy_entries(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    po_file = polib.POFile()
    po_file.metadata = {"Language": "es_ES"}
    po_file.append(polib.POEntry(msgid="Save", msgstr="", flags=["fuzzy"]))
    po_file.append(polib.POEntry(msgid="Title", msgstr=""))
    po_file.save(str(locale_dir / "messages-es_ES.po"))
    site = _build_site(workspace, modes={"only_fuzzy": True})
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(
            translation_provider=_BehaveTranslationProvider()
        ),
    )


@given("a site project with untranslated PO locale variants and a preseeded translation cache")
def step_given_site_with_untranslated_variants_and_cache(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Save", "")])
    _write_po(locale_dir / "messages-es_AR.po", [("Save", "")])
    _seed_translation_cache(workspace, text="Save", translated_text="Guardar")
    site = _build_site(workspace)
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(
            translation_provider=_BehaveTranslationProvider()
        ),
    )


@given("a site project with inconsistent translated PO locale variants")
def step_given_site_with_inconsistent_translated_variants(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Hello", "Hola")])
    _write_po(locale_dir / "messages-es_AR.po", [("Hello", "Che hola")])
    site = _build_site(workspace, modes={"report_inconsistencies": True})
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(),
    )


@given("a site project with reusable translations across locale families")
def step_given_site_with_reusable_translations_across_families(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    first_dir = workspace / "plugin_a"
    second_dir = workspace / "plugin_b"
    first_dir.mkdir(parents=True, exist_ok=True)
    second_dir.mkdir(parents=True, exist_ok=True)
    _write_po(first_dir / "messages-es_ES.po", [("Hello", "Hola")])
    _write_po(first_dir / "messages-es_AR.po", [("Hello", "")])
    _write_po(second_dir / "checkout-es_ES.po", [("Hello", "")])
    _write_po(second_dir / "checkout-es_AR.po", [("Hello", "")])
    site = _build_site(workspace)
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(),
    )


@given("a site project with several untranslated entries in one PO file")
def step_given_site_with_multiple_untranslated_entries(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(
        locale_dir / "messages-es_ES.po",
        [("Save", ""), ("Title", ""), ("Price", "")],
    )
    site = _build_site(workspace)
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(
            translation_provider=_BehaveTranslationProvider()
        ),
    )


@given("a site project without PO locale variants in the local workspace")
def step_given_site_without_variants(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    site = _build_site(workspace)
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(),
    )


@given("a site project with Portuguese PO locale variants in the local workspace")
def step_given_site_with_portuguese_variants(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(
        locale_dir / "messages-pt_BR.po",
        [
            ("Hello", "Ola"),
        ],
    )
    _write_po(
        locale_dir / "messages-pt_PT.po",
        [
            ("Hello", ""),
        ],
    )
    site = _build_site(workspace)
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(),
    )


@given("a site project with one failing PO entry and one translatable entry")
def step_given_site_with_partial_translation_failure(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Broken", ""), ("Save", "")])
    site = _build_site(workspace)
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(
            translation_provider=_BehavePartiallyFailingTranslationProvider()
        ),
    )


@given("a site project with one MO compilation failure and one compilable locale variant")
def step_given_site_with_partial_mo_compilation_failure(context: object) -> None:
    typed = _context(context)
    typed.temp_dir = tempfile.TemporaryDirectory()
    workspace = Path(typed.temp_dir.name)
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Hello", "Hola")])
    _write_po(locale_dir / "messages-es_AR.po", [("Hello", "Hola")])
    site = _build_site(workspace)
    typed.site = site
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(repository=_CompileFailingRepository()),
    )


@when("the operator runs the PO processing workflow for that site")
def step_when_run_po(context: object) -> None:
    typed = _context(context)
    typed.po_progress_events = []
    result = typed.workflow_service.start_po_processing(
        typed.site_id,
        TranslationWorkflowRequestViewModel(
            locales=typed.site.default_locale,
            options=TranslationOptionsViewModel(
                compile_mo=typed.site.compile_mo,
                use_external_translator=typed.site.use_external_translator,
                use_translation_cache=typed.site.use_translation_cache,
                only_fuzzy=typed.site.only_fuzzy,
                dry_run=typed.site.dry_run,
                stats_only=typed.site.stats_only,
                report_inconsistencies=typed.site.report_inconsistencies,
            ),
        ),
        progress_callback=typed.po_progress_events.append,
    )
    typed.po_result_status = result.status
    typed.po_result_families = result.processed_families
    typed.po_result_summary = result.summary
    typed.compiled_mo_paths = tuple(sorted(Path(typed.temp_dir.name).rglob("*.mo")))
    translated_path = Path(typed.temp_dir.name) / "locale" / "messages-es_ES.po"
    if not translated_path.exists():
        typed.processed_po_text = ""
        return
    translated_po = polib.pofile(str(translated_path))
    typed.processed_po_text = "\n".join(f"{entry.msgid}={entry.msgstr}" for entry in translated_po)


@when('the operator runs the PO processing workflow for that site with selected locale "{locale}"')
def step_when_run_po_with_selected_locale(context: object, locale: str) -> None:
    typed = _context(context)
    typed.po_progress_events = []
    result = typed.workflow_service.start_po_processing(
        typed.site_id,
        TranslationWorkflowRequestViewModel(
            locales=locale,
            options=TranslationOptionsViewModel(
                compile_mo=typed.site.compile_mo,
                use_external_translator=typed.site.use_external_translator,
                use_translation_cache=typed.site.use_translation_cache,
                only_fuzzy=typed.site.only_fuzzy,
                dry_run=typed.site.dry_run,
                stats_only=typed.site.stats_only,
                report_inconsistencies=typed.site.report_inconsistencies,
            ),
        ),
        progress_callback=typed.po_progress_events.append,
    )
    typed.po_result_status = result.status
    typed.po_result_families = result.processed_families
    typed.po_result_summary = result.summary
    typed.compiled_mo_paths = tuple(sorted(Path(typed.temp_dir.name).rglob("*.mo")))


@when("the operator runs the PO processing workflow with inconsistency reporting enabled")
def step_when_run_po_with_inconsistency_reporting_enabled(context: object) -> None:
    typed = _context(context)
    typed.po_progress_events = []
    result = typed.workflow_service.start_po_processing(
        typed.site_id,
        TranslationWorkflowRequestViewModel(
            locales=typed.site.default_locale,
            options=TranslationOptionsViewModel(
                compile_mo=typed.site.compile_mo,
                use_external_translator=typed.site.use_external_translator,
                use_translation_cache=typed.site.use_translation_cache,
                only_fuzzy=typed.site.only_fuzzy,
                dry_run=typed.site.dry_run,
                stats_only=typed.site.stats_only,
                report_inconsistencies=True,
            ),
        ),
        progress_callback=typed.po_progress_events.append,
    )
    typed.po_result_status = result.status
    typed.po_result_families = result.processed_families
    typed.po_result_summary = result.summary
    typed.compiled_mo_paths = tuple(sorted(Path(typed.temp_dir.name).rglob("*.mo")))


@when("the operator runs the PO processing workflow with translation cache disabled")
def step_when_run_po_with_translation_cache_disabled(context: object) -> None:
    typed = _context(context)
    typed.po_progress_events = []
    result = typed.workflow_service.start_po_processing(
        typed.site_id,
        TranslationWorkflowRequestViewModel(
            locales=typed.site.default_locale,
            options=TranslationOptionsViewModel(
                compile_mo=typed.site.compile_mo,
                use_external_translator=typed.site.use_external_translator,
                use_translation_cache=False,
                only_fuzzy=typed.site.only_fuzzy,
                dry_run=typed.site.dry_run,
                stats_only=typed.site.stats_only,
                report_inconsistencies=typed.site.report_inconsistencies,
            ),
        ),
        progress_callback=typed.po_progress_events.append,
    )
    typed.po_result_status = result.status
    typed.po_result_families = result.processed_families
    typed.po_result_summary = result.summary
    typed.compiled_mo_paths = tuple(sorted(Path(typed.temp_dir.name).rglob("*.mo")))
    translated_path = Path(typed.temp_dir.name) / "locale" / "messages-es_ES.po"
    if not translated_path.exists():
        typed.processed_po_text = ""
        return
    translated_po = polib.pofile(str(translated_path))
    typed.processed_po_text = "\n".join(f"{entry.msgid}={entry.msgstr}" for entry in translated_po)


@then("the PO processing result reports completed status")
def step_then_completed(context: object) -> None:
    typed = _context(context)
    if typed.po_result_status != "completed":
        raise AssertionError


@then("the PO processing result reports completed with errors status")
def step_then_completed_with_errors(context: object) -> None:
    typed = _context(context)
    if typed.po_result_status != "completed_with_errors":
        raise AssertionError


@then("the PO processing result reports one processed family")
def step_then_one_family(context: object) -> None:
    typed = _context(context)
    if typed.po_result_families != 1:
        raise AssertionError


@then("the PO processing result reports two processed families")
def step_then_two_families(context: object) -> None:
    typed = _context(context)
    if typed.po_result_families != _TWO_FAMILIES:
        raise AssertionError


@then("the PO processing result reports one found family")
def step_then_one_found_family(context: object) -> None:
    typed = _context(context)
    if "Families found: 1" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports two found families")
def step_then_two_found_families(context: object) -> None:
    typed = _context(context)
    if "Families found: 2" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports one entry completed from initial sync")
def step_then_one_completed_from_initial_sync(context: object) -> None:
    typed = _context(context)
    if "Completed from initial sync: 1" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports synchronized entries")
def step_then_synced_entries(context: object) -> None:
    typed = _context(context)
    if "Synchronized entries: 1" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports translated entries")
def step_then_translated_entries(context: object) -> None:
    typed = _context(context)
    if "Translated entries: 1" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports zero translated entries")
def step_then_zero_translated_entries(context: object) -> None:
    typed = _context(context)
    if "Translated entries: 0" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports three translated entries")
def step_then_three_translated_entries(context: object) -> None:
    typed = _context(context)
    if "Translated entries: 3" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports failed entries for the source file")
def step_then_failed_entries_for_source_file(context: object) -> None:
    typed = _context(context)
    if "Failed entries: 1" not in typed.po_result_summary:
        raise AssertionError
    if "locale/messages-es_ES.po" not in typed.po_result_summary:
        raise AssertionError
    if "Broken" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports failed mo files for the source file")
def step_then_failed_mo_files_for_source_file(context: object) -> None:
    typed = _context(context)
    if "Failed MO files:" not in typed.po_result_summary:
        raise AssertionError
    if "locale/messages-es_ES.po" not in typed.po_result_summary:
        raise AssertionError
    if "messages-es_ES.mo" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports compiled mo files")
def step_then_compiled_mo_files(context: object) -> None:
    typed = _context(context)
    if "Compiled MO files: 2" not in typed.po_result_summary:
        raise AssertionError


@then("the processed locale variants contain compiled mo files")
def step_then_compiled_mo_files_exist(context: object) -> None:
    typed = _context(context)
    if typed.compiled_mo_paths != (
        Path(typed.temp_dir.name) / "locale" / "messages-es_AR.mo",
        Path(typed.temp_dir.name) / "locale" / "messages-es_ES.mo",
    ):
        raise AssertionError


@then("the PO processing result reports zero compiled mo files")
def step_then_zero_compiled_mo_files(context: object) -> None:
    typed = _context(context)
    if "Compiled MO files: 0" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports zero written PO files")
def step_then_zero_written_po_files(context: object) -> None:
    typed = _context(context)
    if "Written PO files: 0" not in typed.po_result_summary:
        raise AssertionError


@then("the processed locale variants do not contain compiled mo files")
def step_then_no_compiled_mo_files_exist(context: object) -> None:
    typed = _context(context)
    if typed.compiled_mo_paths != ():
        raise AssertionError


@then("the processed PO file contains the translated text")
def step_then_processed_po_contains_translation(context: object) -> None:
    typed = _context(context)
    if "Save=Guardar" not in typed.processed_po_text:
        raise AssertionError


@then("the processed PO file keeps the untranslated text")
def step_then_processed_po_keeps_untranslated_text(context: object) -> None:
    typed = _context(context)
    if "Save=" not in typed.processed_po_text:
        raise AssertionError
    if "Save=Guardar" in typed.processed_po_text:
        raise AssertionError


@then("the processed PO file translates only fuzzy entries")
def step_then_processed_po_translates_only_fuzzy_entries(context: object) -> None:
    typed = _context(context)
    if "Save=Guardar" not in typed.processed_po_text:
        raise AssertionError
    if "Title=" not in typed.processed_po_text:
        raise AssertionError
    if "Title=Titulo" in typed.processed_po_text:
        raise AssertionError


@then("the processed PO file contains all translated texts")
def step_then_processed_po_contains_all_translations(context: object) -> None:
    typed = _context(context)
    if "Save=Guardar" not in typed.processed_po_text:
        raise AssertionError
    if "Title=Titulo" not in typed.processed_po_text:
        raise AssertionError
    if "Price=Precio" not in typed.processed_po_text:
        raise AssertionError


@then("the PO processing progress reports the current file and entry")
def step_then_progress_reports_current_file_and_entry(context: object) -> None:
    typed = _context(context)
    if not any(
        event.current_file == "locale/messages-es_ES.po" and event.current_entry == "Save"
        for event in typed.po_progress_events
    ):
        raise AssertionError
    if not any(
        event.current_file == "locale/messages-es_ES.po" and event.current_entry == "Title"
        for event in typed.po_progress_events
    ):
        raise AssertionError


@then("the PO processing result reports zero processed families")
def step_then_zero_family(context: object) -> None:
    typed = _context(context)
    if typed.po_result_families != 0:
        raise AssertionError


@then("the PO processing result reports one translation inconsistency")
def step_then_one_translation_inconsistency(context: object) -> None:
    typed = _context(context)
    if "Translation inconsistencies: 1" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports one variant difference")
def step_then_one_variant_difference(context: object) -> None:
    typed = _context(context)
    if "Variant differences found: 1" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports zero translation inconsistencies")
def step_then_zero_translation_inconsistencies(context: object) -> None:
    typed = _context(context)
    if "Translation inconsistencies: 0" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports one cached translation")
def step_then_one_cached_translation(context: object) -> None:
    typed = _context(context)
    if "Translated from cache: 1" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports zero cached translations")
def step_then_zero_cached_translations(context: object) -> None:
    typed = _context(context)
    if "Translated from cache: 0" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports one provider translation")
def step_then_one_provider_translation(context: object) -> None:
    typed = _context(context)
    if "Translated via provider: 1" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports zero provider translations")
def step_then_zero_provider_translations(context: object) -> None:
    typed = _context(context)
    if "Translated via provider: 0" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports only-fuzzy mode enabled")
def step_then_only_fuzzy_mode_enabled(context: object) -> None:
    typed = _context(context)
    if "Only fuzzy: enabled" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports one fuzzy entry")
def step_then_one_fuzzy_entry(context: object) -> None:
    typed = _context(context)
    if "Fuzzy entries: 1" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports two skipped sync-only entries")
def step_then_skipped_sync_only_entries(context: object) -> None:
    typed = _context(context)
    if "Skipped by sync-only: 2" not in typed.po_result_summary:
        raise AssertionError


@then("the PO processing result reports one reused translation from another variant")
def step_then_one_reused_translation_from_another_variant(context: object) -> None:
    typed = _context(context)
    if "Reused from other variant: 1" not in typed.po_result_summary:
        raise AssertionError


@then('the PO processing result reports the inconsistency detail for "{msgid}"')
def step_then_inconsistency_detail(context: object, msgid: str) -> None:
    typed = _context(context)
    if "Variant difference details:" not in typed.po_result_summary:
        raise AssertionError
    if f"msgid='{msgid}'" not in typed.po_result_summary:
        raise AssertionError


def _build_site(
    workspace: Path,
    *,
    modes: dict[str, bool] | None = None,
) -> RegisteredSite:
    resolved_modes = {
        "compile_mo": True,
        "use_external_translator": True,
        "use_translation_cache": True,
        "only_fuzzy": False,
        "dry_run": False,
        "stats_only": False,
        "report_inconsistencies": False,
    }
    if modes is not None:
        resolved_modes.update(modes)
    options = TranslationOptionsViewModel(**resolved_modes)
    return RegisteredSite(
        project=SiteProject(
            id="site-po",
            name="PO Site",
            framework_type="wordpress",
            local_path=str(workspace),
            default_locale="es_ES",
            is_active=True,
            compile_mo=options.compile_mo,
            use_external_translator=options.use_external_translator,
            use_translation_cache=options.use_translation_cache,
            only_fuzzy=options.only_fuzzy,
            dry_run=options.dry_run,
            stats_only=options.stats_only,
            report_inconsistencies=options.report_inconsistencies,
        ),
        remote_connection=None,
    )


def _write_po(path: Path, entries: list[tuple[str, str]]) -> None:
    po_file = polib.POFile()
    po_file.metadata = {"Language": path.stem.split("-")[-1]}
    for msgid, msgstr in entries:
        po_file.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    po_file.save(str(path))
