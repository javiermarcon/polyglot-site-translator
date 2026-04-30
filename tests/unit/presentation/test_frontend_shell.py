"""Unit tests for the frontend presentation shell."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from threading import Event
from typing import Any, cast

from pytest import MonkeyPatch

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.domain.po_processing.models import POProcessingProgress
from polyglot_site_translator.domain.sync.models import SyncProgressEvent, SyncProgressStage
from polyglot_site_translator.presentation.contracts import FrontendServices
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.router import RouteName
from polyglot_site_translator.presentation.view_models import (
    AuditSummaryViewModel,
    POProcessingSummaryViewModel,
    RemoteConnectionTestResultViewModel,
    SiteEditorViewModel,
    SyncProgressStateViewModel,
    SyncStatusViewModel,
    build_default_app_settings,
)
from tests.support.frontend_doubles import (
    InMemoryProjectCatalogService,
    InMemoryProjectRegistryManagementService,
    build_empty_services,
    build_failing_settings_load_services,
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

    def start_sync_to_remote(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_LOCAL,
                    message="Listing local files in the blocking workflow test.",
                    command_text="LOCAL LIST /workspace/marketing-site",
                )
            )
        self.started.set()
        self.release.wait(timeout=1)
        return SyncStatusViewModel(
            status="completed",
            files_synced=1,
            summary="Uploaded 1 files into /srv/app.",
            error_code=None,
        )

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        return build_seeded_services().workflows.start_audit(project_id)

    def start_po_processing(
        self,
        project_id: str,
        locales: str | None = None,
        compile_mo: bool | None = None,
        use_external_translator: bool | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        return build_seeded_services().workflows.start_po_processing(
            project_id,
            locales,
            compile_mo,
            use_external_translator,
            progress_callback,
        )


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

    def start_sync_to_remote(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_LOCAL,
                    message="Listing local files before upload.",
                    command_text="LOCAL LIST /workspace/broken-site",
                )
            )
        msg = "Temporary failure in name resolution"
        raise AttributeError(msg)

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        return build_seeded_services().workflows.start_audit(project_id)

    def start_po_processing(
        self,
        project_id: str,
        locales: str | None = None,
        compile_mo: bool | None = None,
        use_external_translator: bool | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        return build_seeded_services().workflows.start_po_processing(
            project_id,
            locales,
            compile_mo,
            use_external_translator,
            progress_callback,
        )


@dataclass
class _BlockingPOProcessingWorkflowService:
    started: Event
    release: Event
    requested_locales: list[str]
    requested_compile_mo: list[bool | None]
    requested_use_external_translator: list[bool | None]

    def start_sync(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        return build_seeded_services().workflows.start_sync(project_id, progress_callback)

    def trust_remote_host_key(self, project_id: str) -> RemoteConnectionTestResultViewModel:
        return build_seeded_services().workflows.trust_remote_host_key(project_id)

    def start_sync_to_remote(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        return build_seeded_services().workflows.start_sync_to_remote(project_id, progress_callback)

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        return build_seeded_services().workflows.start_audit(project_id)

    def start_po_processing(
        self,
        project_id: str,
        locales: str | None = None,
        compile_mo: bool | None = None,
        use_external_translator: bool | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        self.requested_locales.append("" if locales is None else locales)
        self.requested_compile_mo.append(compile_mo)
        self.requested_use_external_translator.append(use_external_translator)
        if progress_callback is not None:
            progress_callback(
                POProcessingProgress(
                    processed_families=0,
                    completed_entries=0,
                    total_entries=5,
                    files_discovered=3,
                    entries_synchronized=0,
                    entries_translated=0,
                    entries_failed=0,
                    message="Preparing 2 PO families for synchronization.",
                    current_file="locale/messages-es_ES.po",
                    current_entry="Save",
                )
            )
        self.started.set()
        self.release.wait(timeout=1)
        return POProcessingSummaryViewModel(
            status="completed",
            processed_families=2,
            progress_current=5,
            progress_total=5,
            progress_is_indeterminate=False,
            summary=(
                "Families processed: 2 | PO files discovered: 3 | "
                "Synchronized entries: 4 | Translated entries: 1 | Failed entries: 0 | "
                "Compiled MO files: 3"
            ),
            current_file=None,
            current_entry=None,
        )


@dataclass
class _FailingPOProcessingWorkflowService:
    def start_sync(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        return build_seeded_services().workflows.start_sync(project_id, progress_callback)

    def trust_remote_host_key(self, project_id: str) -> RemoteConnectionTestResultViewModel:
        return build_seeded_services().workflows.trust_remote_host_key(project_id)

    def start_sync_to_remote(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        return build_seeded_services().workflows.start_sync_to_remote(project_id, progress_callback)

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        return build_seeded_services().workflows.start_audit(project_id)

    def start_po_processing(
        self,
        project_id: str,
        locales: str | None = None,
        compile_mo: bool | None = None,
        use_external_translator: bool | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        msg = (
            "PO processing failed for locales: "
            f"{locales} and compile_mo: {compile_mo} and "
            f"use_external_translator: {use_external_translator}"
        )
        raise ControlledServiceError(msg)


class _FailingConnectionTestRegistry(InMemoryProjectRegistryManagementService):
    def test_remote_connection(
        self,
        editor: SiteEditorViewModel,
    ) -> RemoteConnectionTestResultViewModel:
        msg = "Remote connection draft is invalid."
        raise ControlledServiceError(msg)


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


def test_local_to_remote_sync_action_uses_fake_service_and_updates_state() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_sync_to_remote()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "completed"
    assert shell.sync_state.files_synced == 7
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


def test_background_sync_does_not_start_a_second_worker_while_running() -> None:
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
    active_thread = shell._active_sync_thread
    shell.start_sync_async()

    assert shell._active_sync_thread is active_thread
    workflow.release.set()
    assert shell._active_sync_thread is not None
    shell._active_sync_thread.join(timeout=1)


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
    assert shell.sync_state.summary == (
        "Unexpected background sync failure while synchronizing project 'wp-site'. "
        "Cause: Temporary failure in name resolution"
    )
    assert shell.sync_state.error_code == "sync_runtime_failure"
    assert shell.latest_error == (
        "Unexpected background sync failure while synchronizing project 'wp-site'. "
        "Cause: Temporary failure in name resolution"
    )
    assert shell.sync_progress_state is not None
    assert shell.sync_progress_state.status == "failed"
    assert shell.sync_progress_state.message == (
        "Unexpected background sync failure while synchronizing project 'wp-site'. "
        "Cause: Temporary failure in name resolution"
    )


def test_background_sync_uses_default_command_limit_when_settings_load_fails() -> None:
    shell = create_frontend_shell(build_failing_settings_load_services())
    shell.open_projects()
    shell.select_project("wp-site")

    shell.start_sync_async()

    assert shell.sync_progress_state is not None
    assert (
        shell.sync_progress_state.command_log_limit
        == build_default_app_settings().sync_progress_log_limit
    )
    if shell._active_sync_thread is not None:
        shell._active_sync_thread.join(timeout=1)


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


def test_sync_progress_event_is_ignored_when_no_progress_state_exists() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell._record_sync_progress_event(
        SyncProgressEvent(
            stage=SyncProgressStage.LISTING_REMOTE,
            message="Listing remote files.",
            command_text="SFTP LIST /srv/app",
        )
    )

    assert shell.sync_progress_state is None


def test_project_connection_test_failure_is_exposed_in_editor_state() -> None:
    services = build_seeded_services()
    shell = create_frontend_shell(
        FrontendServices(
            catalog=services.catalog,
            workflows=services.workflows,
            settings=services.settings,
            registry=_FailingConnectionTestRegistry(
                catalog=cast(InMemoryProjectCatalogService, services.catalog)
            ),
        )
    )
    shell.open_project_editor_create()
    assert shell.project_editor_state is not None
    editor = shell.project_editor_state.editor

    shell.test_project_connection(editor)

    assert shell.project_editor_state is not None
    assert shell.project_editor_state.status == "failed"
    assert shell.project_editor_state.status_message == "Remote connection draft is invalid."
    assert shell.project_editor_state.connection_test_enabled is False
    assert shell.latest_error == "Remote connection draft is invalid."


def _sync_state_is_cleared(shell: Any) -> bool:
    return shell.sync_state is None


def test_trust_project_editor_remote_host_key_reruns_test_without_host_verification(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: list[SiteEditorViewModel] = []

    def fake_test(_self: object, editor: SiteEditorViewModel) -> None:
        captured.append(editor)

    monkeypatch.setattr(FrontendShell, "test_project_connection", fake_test)

    shell = create_frontend_shell(build_seeded_services())
    editor = SiteEditorViewModel(
        site_id=None,
        name="Site",
        framework_type="wordpress",
        local_path="/tmp/x",
        default_locale="en_US",
        connection_type="sftp",
        remote_host="localhost",
        remote_port="22",
        remote_username="u",
        remote_password="p",
        remote_path="/tmp",
        is_active=True,
        remote_verify_host=True,
    )

    shell.trust_project_editor_remote_host_key(editor)

    assert len(captured) == 1
    assert captured[0].remote_verify_host is False


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
    assert shell.po_processing_state.progress_current == 0
    assert shell.po_processing_state.progress_total == 0


def test_po_processing_can_run_in_background_with_selected_locales() -> None:
    seeded_services = build_seeded_services()
    workflow = _BlockingPOProcessingWorkflowService(
        started=Event(),
        release=Event(),
        requested_locales=[],
        requested_compile_mo=[],
        requested_use_external_translator=[],
    )
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
    shell.start_po_processing_async("es_ES, es_AR")

    assert workflow.started.wait(timeout=1) is True
    assert shell.router.current.name is RouteName.PROJECT_DETAIL
    assert shell.po_processing_state is not None
    assert shell.po_processing_state.status == "running"
    assert "Preparing 2 PO families" in shell.po_processing_state.summary
    assert shell.po_processing_state.progress_current == 0
    assert shell.po_processing_state.progress_total == 5
    assert shell.po_processing_state.current_file == "locale/messages-es_ES.po"
    assert shell.po_processing_state.current_entry == "Save"
    assert workflow.requested_locales == ["es_ES,es_AR"]
    assert workflow.requested_compile_mo == [True]
    assert workflow.requested_use_external_translator == [True]

    workflow.release.set()
    assert shell._active_po_processing_thread is not None
    shell._active_po_processing_thread.join(timeout=1)

    assert shell.po_processing_state is not None
    assert shell.po_processing_state.status == "completed"
    assert shell.po_processing_state.processed_families == 2
    assert shell.po_processing_state.progress_current == 5
    assert shell.po_processing_state.progress_total == 5


def test_background_po_processing_failure_is_exposed_without_crashing() -> None:
    seeded_services = build_seeded_services()
    shell = create_frontend_shell(
        FrontendServices(
            catalog=seeded_services.catalog,
            workflows=_FailingPOProcessingWorkflowService(),
            settings=seeded_services.settings,
            registry=seeded_services.registry,
        )
    )

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_po_processing_async("es_ES")

    if shell._active_po_processing_thread is not None:
        shell._active_po_processing_thread.join(timeout=1)

    assert shell.po_processing_state is not None
    assert shell.po_processing_state.status == "failed"
    assert shell.po_processing_state.summary == (
        "PO processing failed for locales: es_ES and compile_mo: True and "
        "use_external_translator: True"
    )
    assert shell.po_processing_state.current_file is None
    assert shell.po_processing_state.current_entry is None
    assert shell.latest_error == (
        "PO processing failed for locales: es_ES and compile_mo: True and "
        "use_external_translator: True"
    )
