"""In-memory fake services for the frontend shell."""

from __future__ import annotations

from dataclasses import dataclass

from polyglot_site_translator.infrastructure.settings import TomlSettingsService
from polyglot_site_translator.infrastructure.site_registry_sqlite import (
    ConfiguredSqliteSiteRegistryRepository,
)
from polyglot_site_translator.presentation.contracts import (
    FrontendServices,
    ProjectCatalogService,
    SettingsService,
)
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.site_registry_services import (
    SiteRegistryPresentationCatalogService,
    SiteRegistryPresentationManagementService,
)
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    AuditSummaryViewModel,
    POProcessingSummaryViewModel,
    ProjectActionViewModel,
    ProjectDetailViewModel,
    ProjectEditorStateViewModel,
    ProjectSummaryViewModel,
    SettingsStateViewModel,
    SiteEditorViewModel,
    SyncStatusViewModel,
    build_default_app_settings,
    build_default_site_editor,
    build_project_editor_state,
    build_settings_state,
)
from polyglot_site_translator.services.site_registry import SiteRegistryService


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


@dataclass
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


@dataclass
class InMemoryProjectRegistryManagementService:
    """Fake create/update service for project registry tests."""

    catalog: InMemoryProjectCatalogService

    def build_create_project_editor(self) -> ProjectEditorStateViewModel:
        return build_project_editor_state(
            mode="create",
            editor=build_default_site_editor(),
            status="editing",
            status_message="Provide the project metadata to register a new site.",
        )

    def build_edit_project_editor(self, project_id: str) -> ProjectEditorStateViewModel:
        detail = self.catalog.get_project_detail(project_id)
        return build_project_editor_state(
            mode="edit",
            editor=SiteEditorViewModel(
                site_id=detail.project.id,
                name=detail.project.name,
                framework_type=detail.project.framework.lower(),
                local_path=detail.project.local_path,
                default_locale="en_US",
                ftp_host="ftp.example.com",
                ftp_port="21",
                ftp_username="deploy",
                ftp_password="super-secret",
                ftp_remote_path="/public_html",
                is_active=True,
            ),
            status="editing",
            status_message="Update the persisted site registry record.",
        )

    def create_project(self, editor: SiteEditorViewModel) -> ProjectDetailViewModel:
        project = ProjectSummaryViewModel(
            id="created-site",
            name=editor.name,
            framework=editor.framework_type.title(),
            local_path=editor.local_path,
            status="Active" if editor.is_active else "Inactive",
        )
        self.catalog.projects = [*self.catalog.projects, project]
        return self.catalog.get_project_detail(project.id)

    def update_project(
        self,
        project_id: str,
        editor: SiteEditorViewModel,
    ) -> ProjectDetailViewModel:
        updated_projects: list[ProjectSummaryViewModel] = []
        for project in self.catalog.projects:
            if project.id == project_id:
                updated_projects.append(
                    ProjectSummaryViewModel(
                        id=project.id,
                        name=editor.name,
                        framework=editor.framework_type.title(),
                        local_path=editor.local_path,
                        status="Active" if editor.is_active else "Inactive",
                    )
                )
            else:
                updated_projects.append(project)
        self.catalog.projects = updated_projects
        return self.catalog.get_project_detail(project_id)


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
    catalog = InMemoryProjectCatalogService(projects=projects)
    return FrontendServices(
        catalog=catalog,
        workflows=FakeProjectWorkflowService(),
        settings=settings_service,
        registry=InMemoryProjectRegistryManagementService(catalog=catalog),
    )


def build_empty_services() -> FrontendServices:
    """Return a fake service bundle with no registered projects."""
    catalog = InMemoryProjectCatalogService(projects=[])
    return FrontendServices(
        catalog=catalog,
        workflows=FakeProjectWorkflowService(),
        settings=InMemorySettingsService(_saved_settings=build_default_app_settings()),
        registry=InMemoryProjectRegistryManagementService(catalog=catalog),
    )


def build_failing_sync_services() -> FrontendServices:
    """Return a fake service bundle that fails sync deterministically."""
    services = build_seeded_services()
    return FrontendServices(
        catalog=services.catalog,
        workflows=FakeProjectWorkflowService(fail_sync=True),
        settings=services.settings,
        registry=services.registry,
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
        registry=services.registry,
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
        registry=services.registry,
    )


def build_default_frontend_services(
    *,
    settings_service: TomlSettingsService,
    fail_site_registry: bool = False,
) -> FrontendServices:
    """Return the default runtime services with real SQLite site registry persistence."""
    repository = ConfiguredSqliteSiteRegistryRepository(settings_service)
    site_registry_service = SiteRegistryService(repository=repository)
    catalog: ProjectCatalogService = SiteRegistryPresentationCatalogService(site_registry_service)
    if fail_site_registry:
        catalog = FailingSiteRegistryCatalogService()
    return FrontendServices(
        catalog=catalog,
        workflows=FakeProjectWorkflowService(),
        settings=settings_service,
        registry=SiteRegistryPresentationManagementService(
            service=site_registry_service,
            settings_service=settings_service,
        ),
    )


class FailingSiteRegistryCatalogService:
    """Catalog fake that always surfaces a controlled site registry failure."""

    def list_projects(self) -> list[ProjectSummaryViewModel]:
        msg = "SQLite site registry is temporarily unavailable."
        raise ControlledServiceError(msg)

    def get_project_detail(self, project_id: str) -> ProjectDetailViewModel:
        msg = f"SQLite site registry is temporarily unavailable for {project_id}."
        raise ControlledServiceError(msg)
