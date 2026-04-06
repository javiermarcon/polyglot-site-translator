"""Presentation orchestration independent from Kivy widgets."""

from __future__ import annotations

from dataclasses import dataclass, replace

from polyglot_site_translator.presentation.contracts import FrontendServices
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.router import FrontendRouter, RouteName
from polyglot_site_translator.presentation.view_models import (
    AuditSummaryViewModel,
    DashboardSectionViewModel,
    DashboardStateViewModel,
    POProcessingSummaryViewModel,
    ProjectActionViewModel,
    ProjectDetailStateViewModel,
    ProjectsStateViewModel,
    SettingsStateViewModel,
    SyncStatusViewModel,
    build_default_app_settings,
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
                description="Run a future FTP synchronization workflow through service contracts.",
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
        self.latest_error = None

    def open_dashboard(self) -> None:
        """Open the dashboard route."""
        self.latest_error = None
        self.router.go_to(RouteName.DASHBOARD)

    def open_projects(self) -> None:
        """Load project summaries and open the projects route."""
        self.latest_error = None
        projects = self.services.catalog.list_projects()
        empty_message = None
        if not projects:
            empty_message = "No projects registered yet."
        self.projects_state = ProjectsStateViewModel(projects=projects, empty_message=empty_message)
        self.router.go_to(RouteName.PROJECTS)

    def select_project(self, project_id: str) -> None:
        """Load a project detail and open its route."""
        self.latest_error = None
        detail = self.services.catalog.get_project_detail(project_id)
        self.project_detail_state = ProjectDetailStateViewModel(
            project=detail.project,
            configuration_summary=detail.configuration_summary,
            metadata_summary=detail.metadata_summary,
            actions=_build_project_actions(detail.actions),
        )
        self.router.go_to(RouteName.PROJECT_DETAIL, project_id=project_id)

    def start_sync(self) -> None:
        """Trigger sync through the workflow contract."""
        project_id = self._require_project_id()
        try:
            self.sync_state = self.services.workflows.start_sync(project_id)
            self.latest_error = None
        except ControlledServiceError as error:
            self.sync_state = SyncStatusViewModel(
                status="failed",
                files_synced=0,
                summary=str(error),
            )
            self.latest_error = str(error)
        self.router.go_to(RouteName.SYNC, project_id=project_id)

    def start_audit(self) -> None:
        """Trigger audit through the workflow contract."""
        project_id = self._require_project_id()
        self.latest_error = None
        self.audit_state = self.services.workflows.start_audit(project_id)
        self.router.go_to(RouteName.AUDIT, project_id=project_id)

    def start_po_processing(self) -> None:
        """Trigger PO processing through the workflow contract."""
        project_id = self._require_project_id()
        self.latest_error = None
        self.po_processing_state = self.services.workflows.start_po_processing(project_id)
        self.router.go_to(RouteName.PO_PROCESSING, project_id=project_id)

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
        self.router.go_to(RouteName.SETTINGS)

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
        self.router.go_to(RouteName.SETTINGS)

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
        self.router.go_to(RouteName.SETTINGS)

    def _require_project_id(self) -> str:
        route = self.router.current
        project_id = route.project_id
        if project_id is None and self.project_detail_state is not None:
            project_id = self.project_detail_state.project.id
        if project_id is None:
            msg = "A project must be selected before running workflows."
            raise ValueError(msg)
        return project_id

    def _require_settings_state(self) -> SettingsStateViewModel:
        state = self.settings_state
        if state is None:
            msg = "Settings must be loaded before editing them."
            raise ValueError(msg)
        return state


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
