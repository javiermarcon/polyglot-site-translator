"""BDD steps for PO processing workflows."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
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
from polyglot_site_translator.services.po_processing import POProcessingService

StepFunction = TypeVar("StepFunction", bound=Callable[..., object])

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


class _InMemorySiteWorkflowService:
    def __init__(self, site: RegisteredSite) -> None:
        self._site = site

    def get_site(self, site_id: str) -> RegisteredSite:
        if site_id != self._site.id:
            msg = f"Unknown site id: {site_id}"
            raise SiteRegistryNotFoundError(msg)
        return self._site

    def detect_framework(self, project_path: str) -> FrameworkDetectionResult:
        return FrameworkDetectionResult.unmatched(
            project_path=project_path,
            warnings=["Framework detection not required for PO workflow BDD."],
        )

    def test_remote_connection(self, registration: object) -> RemoteConnectionTestResult:
        del registration
        return RemoteConnectionTestResult(
            success=True,
            connection_type="none",
            host="",
            port=0,
            message="Remote connection test is not required for this BDD flow.",
            error_code=None,
        )


class _SyncStub:
    def sync_remote_to_local(
        self,
        site: RegisteredSite,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncResult:
        del progress_callback
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

    def sync_local_to_remote(
        self,
        site: RegisteredSite,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncResult:
        del progress_callback
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
    def translate_text(self, *, text: str, target_locale: str) -> str:
        translations = {
            ("es_ES", "Save"): "Guardar",
            ("es_AR", "Save"): "Guardar",
            ("es_ES", "Title"): "Titulo",
            ("es_ES", "Price"): "Precio",
        }
        return translations[(target_locale, text)]


class _BehavePartiallyFailingTranslationProvider:
    def translate_text(self, *, text: str, target_locale: str) -> str:
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
    site = _build_site(workspace, compile_mo=False)
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
    site = _build_site(workspace, use_external_translator=False)
    typed.site_id = site.id
    typed.workflow_service = SiteRegistryPresentationWorkflowService(
        service=_InMemorySiteWorkflowService(site),
        project_sync_service=_SyncStub(),
        po_processing_service=POProcessingService(
            translation_provider=_BehaveTranslationProvider()
        ),
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
        locale,
        progress_callback=typed.po_progress_events.append,
    )
    typed.po_result_status = result.status
    typed.po_result_families = result.processed_families
    typed.po_result_summary = result.summary
    typed.compiled_mo_paths = tuple(sorted(Path(typed.temp_dir.name).rglob("*.mo")))


@then("the PO processing result reports completed status")
def step_then_completed(context: object) -> None:
    typed = _context(context)
    assert typed.po_result_status == "completed"


@then("the PO processing result reports completed with errors status")
def step_then_completed_with_errors(context: object) -> None:
    typed = _context(context)
    assert typed.po_result_status == "completed_with_errors"


@then("the PO processing result reports one processed family")
def step_then_one_family(context: object) -> None:
    typed = _context(context)
    assert typed.po_result_families == 1


@then("the PO processing result reports synchronized entries")
def step_then_synced_entries(context: object) -> None:
    typed = _context(context)
    assert "Synchronized entries: 1" in typed.po_result_summary


@then("the PO processing result reports translated entries")
def step_then_translated_entries(context: object) -> None:
    typed = _context(context)
    assert "Translated entries: 1" in typed.po_result_summary


@then("the PO processing result reports zero translated entries")
def step_then_zero_translated_entries(context: object) -> None:
    typed = _context(context)
    assert "Translated entries: 0" in typed.po_result_summary


@then("the PO processing result reports three translated entries")
def step_then_three_translated_entries(context: object) -> None:
    typed = _context(context)
    assert "Translated entries: 3" in typed.po_result_summary


@then("the PO processing result reports failed entries for the source file")
def step_then_failed_entries_for_source_file(context: object) -> None:
    typed = _context(context)
    assert "Failed entries: 1" in typed.po_result_summary
    assert "locale/messages-es_ES.po" in typed.po_result_summary
    assert "Broken" in typed.po_result_summary


@then("the PO processing result reports failed mo files for the source file")
def step_then_failed_mo_files_for_source_file(context: object) -> None:
    typed = _context(context)
    assert "Failed MO files:" in typed.po_result_summary
    assert "locale/messages-es_ES.po" in typed.po_result_summary
    assert "messages-es_ES.mo" in typed.po_result_summary


@then("the PO processing result reports compiled mo files")
def step_then_compiled_mo_files(context: object) -> None:
    typed = _context(context)
    assert "Compiled MO files: 2" in typed.po_result_summary


@then("the processed locale variants contain compiled mo files")
def step_then_compiled_mo_files_exist(context: object) -> None:
    typed = _context(context)
    assert typed.compiled_mo_paths == (
        Path(typed.temp_dir.name) / "locale" / "messages-es_AR.mo",
        Path(typed.temp_dir.name) / "locale" / "messages-es_ES.mo",
    )


@then("the PO processing result reports zero compiled mo files")
def step_then_zero_compiled_mo_files(context: object) -> None:
    typed = _context(context)
    assert "Compiled MO files: 0" in typed.po_result_summary


@then("the processed locale variants do not contain compiled mo files")
def step_then_no_compiled_mo_files_exist(context: object) -> None:
    typed = _context(context)
    assert typed.compiled_mo_paths == ()


@then("the processed PO file contains the translated text")
def step_then_processed_po_contains_translation(context: object) -> None:
    typed = _context(context)
    assert "Save=Guardar" in typed.processed_po_text


@then("the processed PO file keeps the untranslated text")
def step_then_processed_po_keeps_untranslated_text(context: object) -> None:
    typed = _context(context)
    assert "Save=" in typed.processed_po_text
    assert "Save=Guardar" not in typed.processed_po_text


@then("the processed PO file contains all translated texts")
def step_then_processed_po_contains_all_translations(context: object) -> None:
    typed = _context(context)
    assert "Save=Guardar" in typed.processed_po_text
    assert "Title=Titulo" in typed.processed_po_text
    assert "Price=Precio" in typed.processed_po_text


@then("the PO processing progress reports the current file and entry")
def step_then_progress_reports_current_file_and_entry(context: object) -> None:
    typed = _context(context)
    assert any(
        event.current_file == "locale/messages-es_ES.po" and event.current_entry == "Save"
        for event in typed.po_progress_events
    )
    assert any(
        event.current_file == "locale/messages-es_ES.po" and event.current_entry == "Title"
        for event in typed.po_progress_events
    )


@then("the PO processing result reports zero processed families")
def step_then_zero_family(context: object) -> None:
    typed = _context(context)
    assert typed.po_result_families == 0


def _build_site(
    workspace: Path,
    *,
    compile_mo: bool = True,
    use_external_translator: bool = True,
) -> RegisteredSite:
    return RegisteredSite(
        project=SiteProject(
            id="site-po",
            name="PO Site",
            framework_type="wordpress",
            local_path=str(workspace),
            default_locale="es_ES",
            is_active=True,
            compile_mo=compile_mo,
            use_external_translator=use_external_translator,
        ),
        remote_connection=None,
    )


def _write_po(path: Path, entries: list[tuple[str, str]]) -> None:
    po_file = polib.POFile()
    po_file.metadata = {"Language": path.stem.split("-")[-1]}
    for msgid, msgstr in entries:
        po_file.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    po_file.save(str(path))
