"""In-memory fake services for the frontend shell."""

from __future__ import annotations

from dataclasses import dataclass

from polyglot_site_translator.presentation.contracts import FrontendServices, SettingsService
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    AuditSummaryViewModel,
    POProcessingSummaryViewModel,
    ProjectActionViewModel,
    ProjectDetailViewModel,
    ProjectSummaryViewModel,
    SettingsStateViewModel,
    SyncStatusViewModel,
    build_default_app_settings,
    build_settings_state,
)


def _default_actions() -> list[ProjectActionViewModel]:
    return [
        ProjectActionViewModel(
            key="sync",
            label="Sync FTP",
            description="Preview a future synchronization workflow through a fake service.",
        ),
        ProjectActionViewModel(
            key="audit",
            label="Run Audit",
            description="Launch a fake audit summary to validate the UI contract.",
        ),
        ProjectActionViewModel(
            key="po-processing",
            label="Process PO",
            description="Launch a fake PO processing summary without touching gettext files.",
        ),
    ]


@dataclass(frozen=True)
class InMemoryProjectCatalogService:
    """Fake project catalog backed by in-memory view models."""

    projects: list[ProjectSummaryViewModel]

    def list_projects(self) -> list[ProjectSummaryViewModel]:
        """Return registered project summaries."""
        return list(self.projects)

    def get_project_detail(self, project_id: str) -> ProjectDetailViewModel:
        """Return detail information for a selected project."""
        for project in self.projects:
            if project.id == project_id:
                return ProjectDetailViewModel(
                    project=project,
                    configuration_summary="Framework adapter and storage wiring are pending.",
                    metadata_summary=(
                        "This screen is prepared for site registry, sync, audit and PO workflows."
                    ),
                    actions=_default_actions(),
                )
        msg = f"Unknown project id: {project_id}"
        raise LookupError(msg)


@dataclass(frozen=True)
class FakeProjectWorkflowService:
    """Fake workflow service returning deterministic summaries."""

    fail_sync: bool = False

    def start_sync(self, project_id: str) -> SyncStatusViewModel:
        """Return a deterministic sync summary or a controlled error."""
        if self.fail_sync and project_id == "wp-site":
            msg = "Sync preview is unavailable for this project."
            raise ControlledServiceError(msg)
        return SyncStatusViewModel(
            status="completed",
            files_synced=12,
            summary="Synchronized 12 files into the local workspace preview.",
        )

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        """Return a deterministic audit summary."""
        return AuditSummaryViewModel(
            status="completed",
            findings_count=3,
            findings_summary="3 findings across code and templates",
        )

    def start_po_processing(self, project_id: str) -> POProcessingSummaryViewModel:
        """Return a deterministic PO processing summary."""
        return POProcessingSummaryViewModel(
            status="completed",
            processed_families=4,
            summary="Prepared 4 locale families for future PO synchronization.",
        )


@dataclass
class InMemorySettingsService:
    """Fake settings persistence kept in memory for the frontend shell."""

    _saved_settings: AppSettingsViewModel
    fail_load: bool = False
    fail_save: bool = False

    def load_settings(self) -> SettingsStateViewModel:
        """Return the currently saved settings state."""
        if self.fail_load:
            msg = "App settings are temporarily unavailable."
            raise ControlledServiceError(msg)
        return build_settings_state(
            app_settings=self._saved_settings,
            status="loaded",
            status_message="Settings loaded.",
        )

    def save_settings(self, app_settings: AppSettingsViewModel) -> SettingsStateViewModel:
        """Persist settings in memory and return the saved state."""
        if self.fail_save:
            msg = "App settings could not be saved."
            raise ControlledServiceError(msg)
        self._saved_settings = app_settings
        return build_settings_state(
            app_settings=self._saved_settings,
            status="saved",
            status_message="Settings saved.",
        )

    def reset_settings(self) -> SettingsStateViewModel:
        """Restore in-memory settings to the frontend defaults."""
        self._saved_settings = build_default_app_settings()
        return build_settings_state(
            app_settings=self._saved_settings,
            status="defaults-restored",
            status_message="Settings restored to defaults.",
        )


def build_seeded_services() -> FrontendServices:
    """Return a fake service bundle with sample projects."""
    return build_seeded_services_with_settings(
        InMemorySettingsService(_saved_settings=build_default_app_settings())
    )


def build_seeded_services_with_settings(settings_service: SettingsService) -> FrontendServices:
    """Return seeded fake catalog/workflow services with an injected settings service."""
    projects = [
        ProjectSummaryViewModel(
            id="wp-site",
            name="Marketing Site",
            framework="WordPress",
            local_path="/workspace/marketing-site",
            status="Ready",
        ),
        ProjectSummaryViewModel(
            id="dj-admin",
            name="Backoffice",
            framework="Django",
            local_path="/workspace/backoffice",
            status="Needs sync",
        ),
    ]
    return FrontendServices(
        catalog=InMemoryProjectCatalogService(projects=projects),
        workflows=FakeProjectWorkflowService(),
        settings=settings_service,
    )


def build_empty_services() -> FrontendServices:
    """Return a fake service bundle with no registered projects."""
    return FrontendServices(
        catalog=InMemoryProjectCatalogService(projects=[]),
        workflows=FakeProjectWorkflowService(),
        settings=InMemorySettingsService(_saved_settings=build_default_app_settings()),
    )


def build_failing_sync_services() -> FrontendServices:
    """Return a fake service bundle that fails sync deterministically."""
    services = build_seeded_services()
    return FrontendServices(
        catalog=services.catalog,
        workflows=FakeProjectWorkflowService(fail_sync=True),
        settings=services.settings,
    )


def build_failing_settings_load_services() -> FrontendServices:
    """Return a fake service bundle that fails when loading settings."""
    services = build_seeded_services()
    return FrontendServices(
        catalog=services.catalog,
        workflows=services.workflows,
        settings=InMemorySettingsService(
            _saved_settings=build_default_app_settings(),
            fail_load=True,
        ),
    )


def build_failing_settings_save_services() -> FrontendServices:
    """Return a fake service bundle that fails when saving settings."""
    services = build_seeded_services()
    return FrontendServices(
        catalog=services.catalog,
        workflows=services.workflows,
        settings=InMemorySettingsService(
            _saved_settings=build_default_app_settings(),
            fail_save=True,
        ),
    )
