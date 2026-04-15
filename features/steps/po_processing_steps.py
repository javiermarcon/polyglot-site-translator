"""BDD steps for PO processing workflows."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tempfile
from typing import Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]
import polib

from polyglot_site_translator.domain.framework_detection.models import FrameworkDetectionResult
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


@when("the operator runs the PO processing workflow for that site")
def step_when_run_po(context: object) -> None:
    typed = _context(context)
    result = typed.workflow_service.start_po_processing(typed.site_id)
    typed.po_result_status = result.status
    typed.po_result_families = result.processed_families
    typed.po_result_summary = result.summary


@then("the PO processing result reports completed status")
def step_then_completed(context: object) -> None:
    typed = _context(context)
    assert typed.po_result_status == "completed"


@then("the PO processing result reports one processed family")
def step_then_one_family(context: object) -> None:
    typed = _context(context)
    assert typed.po_result_families == 1


@then("the PO processing result reports synchronized entries")
def step_then_synced_entries(context: object) -> None:
    typed = _context(context)
    assert "Synchronized entries: 1" in typed.po_result_summary


@then("the PO processing result reports zero processed families")
def step_then_zero_family(context: object) -> None:
    typed = _context(context)
    assert typed.po_result_families == 0


def _build_site(workspace: Path) -> RegisteredSite:
    return RegisteredSite(
        project=SiteProject(
            id="site-po",
            name="PO Site",
            framework_type="wordpress",
            local_path=str(workspace),
            default_locale="es_ES",
            is_active=True,
        ),
        remote_connection=None,
    )


def _write_po(path: Path, entries: list[tuple[str, str]]) -> None:
    po_file = polib.POFile()
    po_file.metadata = {"Language": path.stem.split("-")[-1]}
    for msgid, msgstr in entries:
        po_file.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    po_file.save(str(path))
