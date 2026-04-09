"""Presentation orchestration independent from Kivy widgets."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from threading import Lock, Thread

from polyglot_site_translator.domain.sync.models import SyncProgressEvent, SyncProgressStage
from polyglot_site_translator.presentation.contracts import FrontendServices
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.router import FrontendRouter, RouteName
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    AuditSummaryViewModel,
    DashboardSectionViewModel,
    DashboardStateViewModel,
    NavigationMenuStateViewModel,
    POProcessingSummaryViewModel,
    ProjectActionViewModel,
    ProjectDetailStateViewModel,
    ProjectEditorStateViewModel,
    ProjectsStateViewModel,
    SettingsStateViewModel,
    SiteEditorViewModel,
    SyncCommandLogEntryViewModel,
    SyncProgressStateViewModel,
    SyncStatusViewModel,
    build_default_app_settings,
    build_navigation_menu_state,
    build_settings_state,
)


def _build_dashboard_state() -> DashboardStateViewModel:
    return DashboardStateViewModel(
        sections=[
            DashboardSectionViewModel(
                key="projects",
                title="Projects",
                description="Open the registry of managed sites and applications.",
            ),
            DashboardSectionViewModel(
                key="sync",
                title="Sync",
                description="Run a remote synchronization workflow through service contracts.",
            ),
            DashboardSectionViewModel(
                key="audit",
                title="Audit",
                description="Review upcoming localization scans and findings summaries.",
            ),
            DashboardSectionViewModel(
                key="po-processing",
                title="PO Processing",
                description="Prepare PO and MO workflows behind injectable service interfaces.",
            ),
            DashboardSectionViewModel(
                key="settings",
                title="Settings",
                description="Configure frontend behavior through extensible settings sections.",
            ),
        ]
    )


@dataclass
class FrontendShell:
    """Stateful UI orchestrator consumed by screens and tests."""

    router: FrontendRouter
    services: FrontendServices
    dashboard_state: DashboardStateViewModel
    projects_state: ProjectsStateViewModel
    project_detail_state: ProjectDetailStateViewModel | None
    sync_state: SyncStatusViewModel | None
    audit_state: AuditSummaryViewModel | None
    po_processing_state: POProcessingSummaryViewModel | None
    settings_state: SettingsStateViewModel | None
    project_editor_state: ProjectEditorStateViewModel | None
    sync_progress_state: SyncProgressStateViewModel | None
    navigation_menu: NavigationMenuStateViewModel
    latest_error: str | None

    def __init__(self, router: FrontendRouter, services: FrontendServices) -> None:
        self.router = router
        self.services = services
        self.dashboard_state = _build_dashboard_state()
        self.projects_state = ProjectsStateViewModel(projects=[], empty_message=None)
        self.project_detail_state = None
        self.sync_state = None
        self.audit_state = None
        self.po_processing_state = None
        self.settings_state = None
        self.project_editor_state = None
        self.sync_progress_state = None
        self.navigation_menu = build_navigation_menu_state(
            active_route_key=RouteName.DASHBOARD.value,
            operations_enabled=False,
            is_open=False,
        )
        self.latest_error = None
        self._sync_state_lock = Lock()
        self._active_sync_thread: Thread | None = None

    def open_dashboard(self) -> None:
        """Open the dashboard route."""
        self.latest_error = None
        self._set_route(RouteName.DASHBOARD)

    def open_projects(self) -> None:
        """Load project summaries and open the projects route."""
        try:
            projects = self.services.catalog.list_projects()
            self.latest_error = None
            empty_message = None
            if not projects:
                empty_message = "No projects registered yet."
            self.projects_state = ProjectsStateViewModel(
                projects=projects,
                empty_message=empty_message,
            )
        except ControlledServiceError as error:
            self.projects_state = ProjectsStateViewModel(
                projects=[],
                empty_message="No projects registered yet.",
            )
            self.latest_error = str(error)
        self._set_route(RouteName.PROJECTS)

    def select_project(self, project_id: str) -> None:
        """Load a project detail and open its route."""
        try:
            detail = self.services.catalog.get_project_detail(project_id)
            self.project_detail_state = ProjectDetailStateViewModel(
                project=detail.project,
                configuration_summary=detail.configuration_summary,
                metadata_summary=detail.metadata_summary,
                actions=_build_project_actions(detail.actions),
            )
            self.latest_error = None
        except ControlledServiceError as error:
            self.project_detail_state = None
            self.latest_error = str(error)
        self._set_route(RouteName.PROJECT_DETAIL, project_id=project_id)

    def start_sync(self) -> None:
        """Trigger sync through the workflow contract."""
        project_id = self._require_project_id()
        self._run_sync(
            project_id=project_id,
            route_to_sync=True,
            progress_callback=None,
        )

    def start_sync_async(self) -> None:
        """Trigger sync in a background thread for popup-based progress rendering."""
        project_id = self._require_project_id()
        project_name = project_id
        if self.project_detail_state is not None:
            project_name = self.project_detail_state.project.name
        with self._sync_state_lock:
            if self._active_sync_thread is not None and self._active_sync_thread.is_alive():
                return
            self.sync_progress_state = SyncProgressStateViewModel(
                project_id=project_id,
                project_name=project_name,
                status="running",
                message="Starting remote sync.",
                progress_current=0,
                progress_total=0,
                progress_is_indeterminate=True,
                command_log=[],
            )
        worker = Thread(
            target=self._run_sync_in_background,
            args=(project_id,),
            daemon=True,
            name=f"sync-{project_id}",
        )
        self._active_sync_thread = worker
        worker.start()

    def start_audit(self) -> None:
        """Trigger audit through the workflow contract."""
        project_id = self._require_project_id()
        self.latest_error = None
        self.audit_state = self.services.workflows.start_audit(project_id)
        self._set_route(RouteName.AUDIT, project_id=project_id)

    def start_po_processing(self) -> None:
        """Trigger PO processing through the workflow contract."""
        project_id = self._require_project_id()
        self.latest_error = None
        self.po_processing_state = self.services.workflows.start_po_processing(project_id)
        self._set_route(RouteName.PO_PROCESSING, project_id=project_id)

    def open_settings(self) -> None:
        """Load settings and open the settings route."""
        try:
            self.settings_state = self.services.settings.load_settings()
            self.latest_error = None
        except ControlledServiceError as error:
            self.settings_state = build_settings_state(
                app_settings=build_default_app_settings(),
                status="failed",
                status_message=str(error),
            )
            self.latest_error = str(error)
        self._set_route(RouteName.SETTINGS)

    def open_application_menu(self) -> None:
        """Mark the application menu as open for the current route context."""
        self._refresh_navigation_menu(is_open=True)

    def open_route_from_menu(self, route_key: str) -> None:
        """Open a route selected from the grouped application menu."""
        action_map: dict[str, Callable[[], None]] = {
            RouteName.DASHBOARD.value: self.open_dashboard,
            RouteName.PROJECTS.value: self.open_projects,
            RouteName.SETTINGS.value: self.open_settings,
            RouteName.PROJECT_EDITOR.value: self.open_project_editor_create,
            RouteName.SYNC.value: self.start_sync,
            RouteName.AUDIT.value: self.start_audit,
            RouteName.PO_PROCESSING.value: self.start_po_processing,
        }
        action = action_map.get(route_key)
        if action is not None:
            action()
            return
        msg = f"Unsupported route key: {route_key}"
        raise ValueError(msg)

    def set_settings_theme_mode(self, theme_mode: str) -> None:
        """Update the draft theme mode."""
        state = self._require_settings_state()
        allowed_theme_modes = {"system", "light", "dark"}
        if theme_mode not in allowed_theme_modes:
            msg = f"Unsupported theme mode: {theme_mode}"
            raise ValueError(msg)
        self.settings_state = replace(
            state,
            app_settings=replace(state.app_settings, theme_mode=theme_mode),
            status="editing",
            status_message="Settings draft updated.",
        )

    def toggle_remember_last_screen(self) -> None:
        """Toggle remember-last-screen behavior in the draft settings."""
        state = self._require_settings_state()
        self.settings_state = replace(
            state,
            app_settings=replace(
                state.app_settings,
                remember_last_screen=not state.app_settings.remember_last_screen,
            ),
            status="editing",
            status_message="Settings draft updated.",
        )

    def toggle_developer_mode(self) -> None:
        """Toggle developer-mode behavior in the draft settings."""
        state = self._require_settings_state()
        self.settings_state = replace(
            state,
            app_settings=replace(
                state.app_settings,
                developer_mode=not state.app_settings.developer_mode,
            ),
            status="editing",
            status_message="Settings draft updated.",
        )

    def set_settings_window_size(self, *, width: int, height: int) -> None:
        """Update the draft default window size."""
        if width <= 0 or height <= 0:
            msg = "Window dimensions must be positive integers."
            raise ValueError(msg)
        state = self._require_settings_state()
        self.settings_state = replace(
            state,
            app_settings=replace(
                state.app_settings,
                window_width=width,
                window_height=height,
            ),
            status="editing",
            status_message="Settings draft updated.",
        )

    def set_settings_ui_language(self, ui_language: str) -> None:
        """Update the draft UI language."""
        state = self._require_settings_state()
        allowed_languages = {"en", "es"}
        if ui_language not in allowed_languages:
            msg = f"Unsupported UI language: {ui_language}"
            raise ValueError(msg)
        self.settings_state = replace(
            state,
            app_settings=replace(state.app_settings, ui_language=ui_language),
            status="editing",
            status_message="Settings draft updated.",
        )

    def set_settings_database_directory(self, database_directory: str) -> None:
        """Update the draft SQLite database directory."""
        state = self._require_settings_state()
        self.settings_state = replace(
            state,
            app_settings=replace(state.app_settings, database_directory=database_directory),
            status="editing",
            status_message="Settings draft updated.",
        )

    def set_settings_database_filename(self, database_filename: str) -> None:
        """Update the draft SQLite database filename."""
        state = self._require_settings_state()
        self.settings_state = replace(
            state,
            app_settings=replace(state.app_settings, database_filename=database_filename),
            status="editing",
            status_message="Settings draft updated.",
        )

    def update_settings_draft(self, app_settings: AppSettingsViewModel) -> None:
        """Replace the current settings draft with a full form snapshot."""
        state = self._require_settings_state()
        self.settings_state = build_settings_state(
            app_settings=app_settings,
            status="editing",
            status_message="Settings draft updated.",
            selected_section_key=state.selected_section_key,
        )

    def select_settings_section(self, section_key: str) -> None:
        """Change the selected settings section without bypassing the shell."""
        state = self._require_settings_state()
        next_state = build_settings_state(
            app_settings=state.app_settings,
            status=state.status,
            status_message=state.status_message,
            selected_section_key=section_key,
        )
        if next_state.selected_section_is_available:
            status_message = "App / UI / Kivy settings are ready to edit."
        else:
            status_message = f"{next_state.selected_section_title} will be available later."
        self.settings_state = replace(next_state, status_message=status_message)

    def save_settings(self) -> None:
        """Persist the current draft settings through the settings contract."""
        state = self._require_settings_state()
        try:
            self.settings_state = self.services.settings.save_settings(state.app_settings)
            self.latest_error = None
        except ControlledServiceError as error:
            self.settings_state = replace(
                state,
                status="failed",
                status_message=str(error),
            )
            self.latest_error = str(error)
        self._set_route(RouteName.SETTINGS)

    def restore_default_settings(self) -> None:
        """Restore settings defaults through the settings contract."""
        try:
            self.settings_state = self.services.settings.reset_settings()
            self.latest_error = None
        except ControlledServiceError as error:
            state = self._require_settings_state()
            self.settings_state = replace(
                state,
                status="failed",
                status_message=str(error),
            )
            self.latest_error = str(error)
        self._set_route(RouteName.SETTINGS)

    def open_project_editor_create(self) -> None:
        """Open the create-project editor workflow."""
        try:
            self.project_editor_state = self.services.registry.build_create_project_editor()
            self.latest_error = None
        except ControlledServiceError as error:
            self.project_editor_state = None
            self.latest_error = str(error)
        self._set_route(RouteName.PROJECT_EDITOR)

    def open_project_editor_edit(self, project_id: str) -> None:
        """Open the edit-project editor workflow."""
        try:
            self.project_editor_state = self.services.registry.build_edit_project_editor(project_id)
            self.latest_error = None
        except ControlledServiceError as error:
            self.project_editor_state = None
            self.latest_error = str(error)
        self._set_route(RouteName.PROJECT_EDITOR, project_id=project_id)

    def save_new_project(self, editor: SiteEditorViewModel) -> None:
        """Create a project registry record from the editor draft."""
        try:
            detail = self.services.registry.create_project(editor)
            self.project_detail_state = ProjectDetailStateViewModel(
                project=detail.project,
                configuration_summary=detail.configuration_summary,
                metadata_summary=detail.metadata_summary,
                actions=_build_project_actions(detail.actions),
            )
            self.latest_error = None
        except ControlledServiceError as error:
            state = self._require_project_editor_state()
            self.project_editor_state = replace(
                state,
                status="failed",
                status_message=str(error),
                editor=editor,
            )
            self.latest_error = str(error)
            self._set_route(RouteName.PROJECT_EDITOR)
            return
        self._set_route(RouteName.PROJECT_DETAIL, project_id=detail.project.id)

    def save_project_edits(self, project_id: str, editor: SiteEditorViewModel) -> None:
        """Update a project registry record from the editor draft."""
        try:
            detail = self.services.registry.update_project(project_id, editor)
            self.project_detail_state = ProjectDetailStateViewModel(
                project=detail.project,
                configuration_summary=detail.configuration_summary,
                metadata_summary=detail.metadata_summary,
                actions=_build_project_actions(detail.actions),
            )
            self.latest_error = None
        except ControlledServiceError as error:
            state = self._require_project_editor_state()
            self.project_editor_state = replace(
                state,
                status="failed",
                status_message=str(error),
                editor=editor,
            )
            self.latest_error = str(error)
            self._set_route(RouteName.PROJECT_EDITOR, project_id=project_id)
            return
        self._set_route(RouteName.PROJECT_DETAIL, project_id=detail.project.id)

    def test_project_connection(self, editor: SiteEditorViewModel) -> None:
        """Run a remote connection test for the current editor draft."""
        state = self._require_project_editor_state()
        try:
            connection_test_result = self.services.registry.test_remote_connection(editor)
            self.project_editor_state = replace(
                state,
                editor=editor,
                connection_test_enabled=True,
                connection_test_result=connection_test_result,
                status="connection-tested",
                status_message=connection_test_result.message,
            )
            self.latest_error = None
        except ControlledServiceError as error:
            self.project_editor_state = replace(
                state,
                editor=editor,
                connection_test_result=None,
                connection_test_enabled=False,
                status="failed",
                status_message=str(error),
            )
            self.latest_error = str(error)
        self._set_route(RouteName.PROJECT_EDITOR, project_id=editor.site_id)

    def _require_project_id(self) -> str:
        route = self.router.current
        project_id = route.project_id
        if project_id is None and self.project_detail_state is not None:
            project_id = self.project_detail_state.project.id
        if project_id is None:
            msg = "A project must be selected before running workflows."
            raise ValueError(msg)
        return project_id

    def _run_sync(
        self,
        *,
        project_id: str,
        route_to_sync: bool,
        progress_callback: Callable[[SyncProgressEvent], None] | None,
    ) -> None:
        try:
            self.sync_state = self.services.workflows.start_sync(
                project_id,
                progress_callback=progress_callback,
            )
            self.latest_error = None
        except ControlledServiceError as error:
            self.sync_state = SyncStatusViewModel(
                status="failed",
                files_synced=0,
                summary=str(error),
                error_code=None,
            )
            self.latest_error = str(error)
        if route_to_sync:
            self._set_route(RouteName.SYNC, project_id=project_id)

    def _run_sync_in_background(self, project_id: str) -> None:
        self._run_sync(
            project_id=project_id,
            route_to_sync=False,
            progress_callback=self._record_sync_progress_event,
        )
        with self._sync_state_lock:
            current_state = self.sync_progress_state
            if current_state is None or self.sync_state is None:
                self._active_sync_thread = None
                return
            self.sync_progress_state = replace(
                current_state,
                status=self.sync_state.status,
                message=self.sync_state.summary,
                progress_current=self.sync_state.files_synced,
                progress_total=max(current_state.progress_total, self.sync_state.files_synced),
                progress_is_indeterminate=False,
            )
            self._active_sync_thread = None

    def _record_sync_progress_event(self, event: SyncProgressEvent) -> None:
        with self._sync_state_lock:
            current_state = self.sync_progress_state
            if current_state is None:
                return
            command_log = list(current_state.command_log)
            if event.command_text is not None:
                command_log.append(
                    SyncCommandLogEntryViewModel(
                        command_text=event.command_text,
                        message=event.message,
                    )
                )
            progress_total = current_state.progress_total
            if event.total_files is not None:
                progress_total = event.total_files
            progress_current = current_state.progress_current
            if event.files_downloaded is not None:
                progress_current = event.files_downloaded
            status = current_state.status
            if event.stage is SyncProgressStage.COMPLETED:
                status = "completed"
            if event.stage is SyncProgressStage.FAILED:
                status = "failed"
            self.sync_progress_state = replace(
                current_state,
                status=status,
                message=event.message,
                progress_current=progress_current,
                progress_total=progress_total,
                progress_is_indeterminate=progress_total == 0 and status == "running",
                command_log=command_log,
            )

    def _require_settings_state(self) -> SettingsStateViewModel:
        state = self.settings_state
        if state is None:
            msg = "Settings must be loaded before editing them."
            raise ValueError(msg)
        return state

    def _require_project_editor_state(self) -> ProjectEditorStateViewModel:
        state = self.project_editor_state
        if state is None:
            msg = "Project editor state must be loaded before editing."
            raise ValueError(msg)
        return state

    def _set_route(self, route_name: RouteName, project_id: str | None = None) -> None:
        self.router.go_to(route_name, project_id=project_id)
        self._refresh_navigation_menu(is_open=False)
        self._persist_last_opened_screen(route_name)

    def _refresh_navigation_menu(self, *, is_open: bool) -> None:
        self.navigation_menu = build_navigation_menu_state(
            active_route_key=self.router.current.name.value,
            operations_enabled=self._has_project_context(),
            is_open=is_open,
        )

    def _has_project_context(self) -> bool:
        if self.project_detail_state is not None:
            return True
        return self.router.current.project_id is not None

    def _persist_last_opened_screen(self, route_name: RouteName) -> None:
        """Persist the last opened screen when the preference is enabled."""
        settings_state = self.settings_state
        if settings_state is None or settings_state.status == "failed":
            return
        if not settings_state.app_settings.remember_last_screen:
            return
        updated_settings = replace(
            settings_state.app_settings,
            last_opened_screen=route_name.value,
        )
        try:
            self.services.settings.save_settings(updated_settings)
            self.settings_state = replace(settings_state, app_settings=updated_settings)
        except ControlledServiceError as error:
            self.latest_error = str(error)


def _build_project_actions(
    actions: list[ProjectActionViewModel],
) -> list[ProjectActionViewModel]:
    """Return stable action descriptors for the detail screen."""
    return [
        ProjectActionViewModel(
            key=action.key,
            label=action.label,
            description=action.description,
        )
        for action in actions
    ]
