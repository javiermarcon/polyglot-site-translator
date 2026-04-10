"""Unit tests for the frontend presentation shell."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from threading import Event
from typing import Any

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.domain.sync.models import SyncProgressEvent, SyncProgressStage
from polyglot_site_translator.presentation.contracts import FrontendServices
from polyglot_site_translator.presentation.router import RouteName
from polyglot_site_translator.presentation.view_models import (
    AuditSummaryViewModel,
    POProcessingSummaryViewModel,
    RemoteConnectionTestResultViewModel,
    SyncProgressStateViewModel,
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

    def trust_remote_host_key(self, project_id: str) -> RemoteConnectionTestResultViewModel:
        return build_seeded_services().workflows.trust_remote_host_key(project_id)

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        return build_seeded_services().workflows.start_audit(project_id)

    def start_po_processing(self, project_id: str) -> POProcessingSummaryViewModel:
        return build_seeded_services().workflows.start_po_processing(project_id)


@dataclass
class _FailingBackgroundWorkflowService:
    def start_sync(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message="Connecting to the remote host.",
                    command_text="FTP CONNECT broken.example.test:21",
                )
            )
        msg = "Temporary failure in name resolution"
        raise AttributeError(msg)

    def trust_remote_host_key(self, project_id: str) -> RemoteConnectionTestResultViewModel:
        return build_seeded_services().workflows.trust_remote_host_key(project_id)

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


def test_background_sync_clears_stale_failed_sync_state_when_retry_starts() -> None:
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
    shell.sync_state = SyncStatusViewModel(
        status="failed",
        files_synced=0,
        summary="Server '127.0.0.1' not found in known_hosts",
        error_code="unknown_ssh_host_key",
    )

    shell.start_sync_async()

    assert workflow.started.wait(timeout=1) is True
    assert _sync_state_is_cleared(shell) is True
    workflow.release.set()
    assert shell._active_sync_thread is not None
    shell._active_sync_thread.join(timeout=1)


def test_background_sync_failures_are_exposed_in_shell_state_instead_of_crashing() -> None:
    seeded_services = build_seeded_services()
    shell = create_frontend_shell(
        FrontendServices(
            catalog=seeded_services.catalog,
            workflows=_FailingBackgroundWorkflowService(),
            settings=seeded_services.settings,
            registry=seeded_services.registry,
        )
    )

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_sync_async()

    if shell._active_sync_thread is not None:
        shell._active_sync_thread.join(timeout=1)

    assert shell.sync_state is not None
    assert shell.sync_state.status == "failed"
    assert shell.sync_state.summary == "Temporary failure in name resolution"
    assert shell.sync_state.error_code == "sync_runtime_failure"
    assert shell.latest_error == "Temporary failure in name resolution"
    assert shell.sync_progress_state is not None
    assert shell.sync_progress_state.status == "failed"
    assert shell.sync_progress_state.message == "Temporary failure in name resolution"


def test_background_sync_progress_keeps_only_the_last_configured_operations() -> None:
    seeded_services = build_seeded_services()
    shell = create_frontend_shell(seeded_services)

    shell.open_settings()
    assert shell.settings_state is not None
    shell.update_settings_draft(
        replace(shell.settings_state.app_settings, sync_progress_log_limit=2)
    )
    shell.save_settings()
    shell.sync_progress_state = SyncProgressStateViewModel(
        project_id="wp-site",
        project_name="WordPress Site",
        status="running",
        message="Starting remote sync.",
        progress_current=0,
        progress_total=0,
        progress_is_indeterminate=True,
        command_log_limit=2,
        command_log=[],
    )
    shell._record_sync_progress_event(
        SyncProgressEvent(
            stage=SyncProgressStage.LISTING_REMOTE,
            message="Listing remote files.",
            command_text="SFTP LIST /srv/app",
        )
    )
    shell._record_sync_progress_event(
        SyncProgressEvent(
            stage=SyncProgressStage.DOWNLOADING_FILE,
            message="Downloading a file.",
            command_text="SFTP GET /srv/app/locale/es.po",
        )
    )
    shell._record_sync_progress_event(
        SyncProgressEvent(
            stage=SyncProgressStage.DOWNLOADING_FILE,
            message="Writing the file locally.",
            command_text="LOCAL WRITE /workspace/wp-site/locale/es.po",
        )
    )

    assert shell.sync_progress_state is not None
    assert [entry.command_text for entry in shell.sync_progress_state.command_log] == [
        "SFTP GET /srv/app/locale/es.po",
        "LOCAL WRITE /workspace/wp-site/locale/es.po",
    ]


def _sync_state_is_cleared(shell: Any) -> bool:
    return shell.sync_state is None


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
