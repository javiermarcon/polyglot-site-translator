"""Unit tests for the frontend presentation shell."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from threading import Event
from typing import Any, cast

from pytest import MonkeyPatch

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.domain.po_processing.models import POProcessingProgress
from polyglot_site_translator.domain.sync.models import (
    SyncProgressEvent,
    SyncProgressStage,
)
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
    TranslationWorkflowRequestViewModel,
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
    """Test helper for BlockingWorkflowService.

    Attributes:
        started:
            Documented attribute exposed by this type.
        release:
            Documented attribute exposed by this type.
    """

    started: Event
    release: Event

    def start_sync(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Handle start sync.

        Args:
            self:
                Value supplied to this callable.
            project_id:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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

    @staticmethod
    def trust_remote_host_key(project_id: str) -> RemoteConnectionTestResultViewModel:
        """Handle trust remote host key.

        Args:
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.trust_remote_host_key(project_id)

    def start_sync_to_remote(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Handle start sync to remote.

        Args:
            self:
                Value supplied to this callable.
            project_id:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
        """Handle start audit.

        Args:
            self:
                Value supplied to this callable.
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_audit(project_id)

    def start_po_processing(
        self,
        project_id: str,
        request: TranslationWorkflowRequestViewModel | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        """Handle start po processing.

        Args:
            self:
                Value supplied to this callable.
            project_id:
                Value supplied to this callable.
            request:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_po_processing(
            project_id,
            request,
            progress_callback,
        )


@dataclass
class _FailingBackgroundWorkflowService:
    """Test helper for FailingBackgroundWorkflowService.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    @staticmethod
    def start_sync(
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Handle start sync.

        Args:
            project_id:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            AttributeError:
                Raised when this callable hits the corresponding error path.
        """
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

    @staticmethod
    def trust_remote_host_key(project_id: str) -> RemoteConnectionTestResultViewModel:
        """Handle trust remote host key.

        Args:
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.trust_remote_host_key(project_id)

    @staticmethod
    def start_sync_to_remote(
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Handle start sync to remote.

        Args:
            project_id:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            AttributeError:
                Raised when this callable hits the corresponding error path.
        """
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

    @staticmethod
    def start_audit(project_id: str) -> AuditSummaryViewModel:
        """Handle start audit.

        Args:
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_audit(project_id)

    @staticmethod
    def start_po_processing(
        project_id: str,
        request: TranslationWorkflowRequestViewModel | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        """Handle start po processing.

        Args:
            project_id:
                Value supplied to this callable.
            request:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_po_processing(
            project_id,
            request,
            progress_callback,
        )


@dataclass
class _BlockingPOProcessingWorkflowService:
    """Test helper for BlockingPOProcessingWorkflowService.

    Attributes:
        started:
            Documented attribute exposed by this type.
        release:
            Documented attribute exposed by this type.
        requested_locales:
            Documented attribute exposed by this type.
        requested_compile_mo:
            Documented attribute exposed by this type.
        requested_use_external_translator:
            Documented attribute exposed by this type.
        requested_dry_run:
            Documented attribute exposed by this type.
        requested_stats_only:
            Documented attribute exposed by this type.
        requested_report_inconsistencies:
            Documented attribute exposed by this type.
    """

    started: Event
    release: Event
    requested_locales: list[str]
    requested_compile_mo: list[bool | None]
    requested_use_external_translator: list[bool | None]
    requested_dry_run: list[bool | None]
    requested_stats_only: list[bool | None]
    requested_report_inconsistencies: list[bool | None]

    @staticmethod
    def start_sync(
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Handle start sync.

        Args:
            project_id:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_sync(
            project_id, progress_callback
        )

    @staticmethod
    def trust_remote_host_key(project_id: str) -> RemoteConnectionTestResultViewModel:
        """Handle trust remote host key.

        Args:
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.trust_remote_host_key(project_id)

    @staticmethod
    def start_sync_to_remote(
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Handle start sync to remote.

        Args:
            project_id:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_sync_to_remote(
            project_id, progress_callback
        )

    @staticmethod
    def start_audit(project_id: str) -> AuditSummaryViewModel:
        """Handle start audit.

        Args:
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_audit(project_id)

    def start_po_processing(
        self,
        project_id: str,
        request: TranslationWorkflowRequestViewModel | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        """Handle start po processing.

        Args:
            self:
                Value supplied to this callable.
            project_id:
                Value supplied to this callable.
            request:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.requested_locales.append("" if request is None else request.locales)
        self.requested_compile_mo.append(
            None if request is None else request.options.compile_mo
        )
        self.requested_use_external_translator.append(
            None if request is None else request.options.use_external_translator
        )
        self.requested_dry_run.append(
            None if request is None else request.options.dry_run
        )
        self.requested_stats_only.append(
            None if request is None else request.options.stats_only
        )
        self.requested_report_inconsistencies.append(
            None if request is None else request.options.report_inconsistencies
        )
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
    """Test helper for FailingPOProcessingWorkflowService.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    @staticmethod
    def start_sync(
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Handle start sync.

        Args:
            project_id:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_sync(
            project_id, progress_callback
        )

    @staticmethod
    def trust_remote_host_key(project_id: str) -> RemoteConnectionTestResultViewModel:
        """Handle trust remote host key.

        Args:
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.trust_remote_host_key(project_id)

    @staticmethod
    def start_sync_to_remote(
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Handle start sync to remote.

        Args:
            project_id:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_sync_to_remote(
            project_id, progress_callback
        )

    @staticmethod
    def start_audit(project_id: str) -> AuditSummaryViewModel:
        """Handle start audit.

        Args:
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_audit(project_id)

    @staticmethod
    def start_po_processing(
        project_id: str,
        request: TranslationWorkflowRequestViewModel | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        """Handle start po processing.

        Args:
            project_id:
                Value supplied to this callable.
            request:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ControlledServiceError:
                Raised when this callable hits the corresponding error path.
        """
        options = None if request is None else request.options
        msg = (
            "PO processing failed for locales: "
            f"{None if request is None else request.locales} and compile_mo: "
            f"{None if options is None else options.compile_mo} and "
            f"use_external_translator: "
            f"{None if options is None else options.use_external_translator} and "
            f"dry_run: {None if options is None else options.dry_run} and "
            f"stats_only: {None if options is None else options.stats_only} and "
            "report_inconsistencies: "
            f"{None if options is None else options.report_inconsistencies}"
        )
        raise ControlledServiceError(msg)


@dataclass
class _TrustHostKeyWorkflowService:
    """Test helper for TrustHostKeyWorkflowService.

    Attributes:
        succeed:
            Documented attribute exposed by this type.
        raise_error:
            Documented attribute exposed by this type.
    """

    succeed: bool = True
    raise_error: bool = False

    @staticmethod
    def start_sync(
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Handle start sync.

        Args:
            project_id:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_sync(
            project_id, progress_callback
        )

    def trust_remote_host_key(
        self, project_id: str
    ) -> RemoteConnectionTestResultViewModel:
        """Handle trust remote host key.

        Args:
            self:
                Value supplied to this callable.
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ControlledServiceError:
                Raised when this callable hits the corresponding error path.
        """
        if self.raise_error:
            msg = f"Unable to trust host key for {project_id}."
            raise ControlledServiceError(msg)
        return RemoteConnectionTestResultViewModel(
            success=self.succeed,
            message="Trusted." if self.succeed else "Rejected.",
            error_code=None if self.succeed else "trust_failed",
        )

    @staticmethod
    def start_sync_to_remote(
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Handle start sync to remote.

        Args:
            project_id:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_sync_to_remote(
            project_id, progress_callback
        )

    @staticmethod
    def start_audit(project_id: str) -> AuditSummaryViewModel:
        """Handle start audit.

        Args:
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_audit(project_id)

    @staticmethod
    def start_po_processing(
        project_id: str,
        request: TranslationWorkflowRequestViewModel | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        """Handle start po processing.

        Args:
            project_id:
                Value supplied to this callable.
            request:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_seeded_services().workflows.start_po_processing(
            project_id,
            request,
            progress_callback,
        )


class _FailingConnectionTestRegistry(InMemoryProjectRegistryManagementService):
    """Test helper for FailingConnectionTestRegistry.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def test_remote_connection(
        self,
        editor: SiteEditorViewModel,
    ) -> RemoteConnectionTestResultViewModel:
        """Verify remote connection.

        Args:
            self:
                Value supplied to this callable.
            editor:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ControlledServiceError:
                Raised when this callable hits the corresponding error path.
        """
        msg = "Remote connection draft is invalid."
        raise ControlledServiceError(msg)


def test_dashboard_sections_are_available_on_startup() -> None:
    """Verify dashboard sections are available on startup.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Verify projects screen loads summaries and empty state.

    Returns:
        value:
            Structured value returned by this callable.
    """
    shell = create_frontend_shell(build_empty_services())

    shell.open_projects()

    assert shell.projects_state.projects == []
    assert shell.projects_state.empty_message == "No projects registered yet."


def test_selecting_project_loads_detail_and_actions() -> None:
    """Verify selecting project loads detail and actions.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Verify sync action uses fake service and updates state.

    Returns:
        value:
            Structured value returned by this callable.
    """
    shell = create_frontend_shell(build_seeded_services())

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_sync()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "completed"
    assert shell.sync_state.files_synced == 12
    assert shell.latest_error is None


def test_local_to_remote_sync_action_uses_fake_service_and_updates_state() -> None:
    """Verify local to remote sync action uses fake service and updates state.

    Returns:
        value:
            Structured value returned by this callable.
    """
    shell = create_frontend_shell(build_seeded_services())

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_sync_to_remote()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "completed"
    assert shell.sync_state.files_synced == 7
    assert shell.latest_error is None


def test_sync_failure_is_exposed_without_crashing() -> None:
    """Verify sync failure is exposed without crashing.

    Returns:
        value:
            Structured value returned by this callable.
    """
    shell = create_frontend_shell(build_failing_sync_services())

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_sync()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "failed"
    assert shell.latest_error == "Sync preview is unavailable for this project."


def test_sync_can_run_in_background_without_leaving_the_project_detail_route() -> None:
    """Verify sync can run in background without leaving the project detail route.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Verify background sync does not start a second worker while running.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Verify background sync clears stale failed sync state when retry starts.

    Returns:
        value:
            Structured value returned by this callable.
    """
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


def test_background_sync_failures_are_exposed_in_shell_state_instead_of_crashing() -> (
    None
):
    """Verify background sync failures are exposed in shell state instead of crashing.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Verify background sync uses default command limit when settings load fails.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Verify background sync progress keeps only the last configured operations.

    Returns:
        value:
            Structured value returned by this callable.
    """
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


def test_trust_selected_project_remote_host_key_covers_a18f() -> None:
    """Verify trust selected project remote host key covers success failure and service.

    error.

    Returns:
        value:
            Structured value returned by this callable.
    """
    seeded_services = build_seeded_services()
    shell = create_frontend_shell(
        FrontendServices(
            catalog=seeded_services.catalog,
            workflows=_TrustHostKeyWorkflowService(succeed=False),
            settings=seeded_services.settings,
            registry=seeded_services.registry,
        )
    )
    shell.open_projects()
    shell.select_project("wp-site")
    shell.sync_progress_state = SyncProgressStateViewModel(
        project_id="wp-site",
        project_name="Marketing Site",
        status="running",
        message="Running",
        progress_current=0,
        progress_total=0,
        progress_is_indeterminate=True,
        command_log_limit=2,
        command_log=[],
    )

    shell.trust_selected_project_remote_host_key()

    assert shell.latest_error == "Rejected."

    shell.services = FrontendServices(
        catalog=seeded_services.catalog,
        workflows=_TrustHostKeyWorkflowService(raise_error=True),
        settings=seeded_services.settings,
        registry=seeded_services.registry,
    )
    shell.trust_selected_project_remote_host_key()
    assert shell.latest_error == "Unable to trust host key for wp-site."

    shell.services = FrontendServices(
        catalog=seeded_services.catalog,
        workflows=_TrustHostKeyWorkflowService(succeed=True),
        settings=seeded_services.settings,
        registry=seeded_services.registry,
    )
    shell.trust_selected_project_remote_host_key()
    assert shell.latest_error is None


def test_sync_progress_event_is_ignored_when_no_progress_state_exists() -> None:
    """Verify sync progress event is ignored when no progress state exists.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Verify project connection test failure is exposed in editor state.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    assert (
        shell.project_editor_state.status_message
        == "Remote connection draft is invalid."
    )
    assert shell.project_editor_state.connection_test_enabled is False
    assert shell.latest_error == "Remote connection draft is invalid."


def _sync_state_is_cleared(shell: Any) -> bool:
    """Handle sync state is cleared.

    Args:
        shell:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return shell.sync_state is None


def test_trust_project_editor_remote_host_key_reruns_test_without_host_verification(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify trust project editor remote host key reruns test without host.

    verification.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    captured: list[SiteEditorViewModel] = []

    def fake_test(_self: object, editor: SiteEditorViewModel) -> None:
        """Handle fake test.

        Args:
            _self:
                Value supplied to this callable.
            editor:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
    """Verify audit and po actions update independent panels.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Verify po processing can run in background with selected locales.

    Returns:
        value:
            Structured value returned by this callable.
    """
    seeded_services = build_seeded_services()
    workflow = _BlockingPOProcessingWorkflowService(
        started=Event(),
        release=Event(),
        requested_locales=[],
        requested_compile_mo=[],
        requested_use_external_translator=[],
        requested_dry_run=[],
        requested_stats_only=[],
        requested_report_inconsistencies=[],
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
    """Verify background po processing failure is exposed without crashing.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
        "use_external_translator: True and dry_run: False and "
        "stats_only: False and report_inconsistencies: False"
    )
    assert shell.po_processing_state.current_file is None
    assert shell.po_processing_state.current_entry is None
    assert shell.latest_error == (
        "PO processing failed for locales: es_ES and compile_mo: True and "
        "use_external_translator: True and dry_run: False and "
        "stats_only: False and report_inconsistencies: False"
    )
