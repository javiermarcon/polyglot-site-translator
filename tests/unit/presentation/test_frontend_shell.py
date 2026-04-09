"""Unit tests for the frontend presentation shell."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Event

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.domain.sync.models import SyncProgressEvent, SyncProgressStage
from polyglot_site_translator.presentation.contracts import FrontendServices
from polyglot_site_translator.presentation.router import RouteName
from polyglot_site_translator.presentation.view_models import (
    AuditSummaryViewModel,
    POProcessingSummaryViewModel,
    SyncStatusViewModel,
)
from tests.support.frontend_doubles import (
    build_empty_services,
    build_failing_sync_services,
    build_seeded_services,
)


@dataclass
class _BlockingWorkflowService:
    started: Event
    release: Event

    def start_sync(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message="Listing remote files in the blocking workflow test.",
                    command_text="SFTP LIST /srv/app",
                )
            )
        self.started.set()
        self.release.wait(timeout=1)
        return SyncStatusViewModel(
            status="completed",
            files_synced=1,
            summary="Downloaded 1 files into /workspace/marketing-site.",
            error_code=None,
        )

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        return build_seeded_services().workflows.start_audit(project_id)

    def start_po_processing(self, project_id: str) -> POProcessingSummaryViewModel:
        return build_seeded_services().workflows.start_po_processing(project_id)


def test_dashboard_sections_are_available_on_startup() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_dashboard()

    assert shell.router.current.name is RouteName.DASHBOARD
    assert [section.key for section in shell.dashboard_state.sections] == [
        "projects",
        "sync",
        "audit",
        "po-processing",
        "settings",
    ]


def test_projects_screen_loads_summaries_and_empty_state() -> None:
    shell = create_frontend_shell(build_empty_services())

    shell.open_projects()

    assert shell.projects_state.projects == []
    assert shell.projects_state.empty_message == "No projects registered yet."


def test_selecting_project_loads_detail_and_actions() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_projects()
    shell.select_project("wp-site")

    assert shell.router.current.name is RouteName.PROJECT_DETAIL
    assert shell.project_detail_state is not None
    assert shell.project_detail_state.project.id == "wp-site"
    assert [action.key for action in shell.project_detail_state.actions] == [
        "sync",
        "audit",
        "po-processing",
    ]


def test_sync_action_uses_fake_service_and_updates_state() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_sync()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "completed"
    assert shell.sync_state.files_synced == 12
    assert shell.latest_error is None


def test_sync_failure_is_exposed_without_crashing() -> None:
    shell = create_frontend_shell(build_failing_sync_services())

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_sync()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "failed"
    assert shell.latest_error == "Sync preview is unavailable for this project."


def test_sync_can_run_in_background_without_leaving_the_project_detail_route() -> None:
    seeded_services = build_seeded_services()
    workflow = _BlockingWorkflowService(started=Event(), release=Event())
    shell = create_frontend_shell(
        FrontendServices(
            catalog=seeded_services.catalog,
            workflows=workflow,
            settings=seeded_services.settings,
            registry=seeded_services.registry,
        )
    )

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_sync_async()

    assert workflow.started.wait(timeout=1) is True
    assert shell.router.current.name is RouteName.PROJECT_DETAIL
    assert shell.sync_progress_state is not None
    assert shell.sync_progress_state.status == "running"

    workflow.release.set()
    assert shell._active_sync_thread is not None
    shell._active_sync_thread.join(timeout=1)

    assert shell.sync_state is not None
    assert shell.sync_state.status == "completed"
    assert shell.sync_progress_state is not None
    assert shell.sync_progress_state.status == "completed"


def test_audit_and_po_actions_update_independent_panels() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_audit()
    shell.start_po_processing()

    assert shell.audit_state is not None
    assert shell.audit_state.status == "completed"
    assert (
        shell.audit_state.findings_summary
        == "No supported framework was detected for this project."
    )
    assert shell.po_processing_state is not None
    assert shell.po_processing_state.status == "completed"
    assert shell.po_processing_state.processed_families == 4
