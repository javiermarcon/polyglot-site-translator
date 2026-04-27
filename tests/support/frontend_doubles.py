"""Frontend test doubles for implemented presentation workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.domain.po_processing.models import POProcessingProgress
from polyglot_site_translator.domain.remote_connections.models import (
    NO_REMOTE_CONNECTION_VALUE,
)
from polyglot_site_translator.domain.site_registry.locales import normalize_default_locale
from polyglot_site_translator.domain.sync.models import SyncProgressEvent
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.presentation.contracts import (
    FrontendServices,
    SettingsService,
)
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    AuditSummaryViewModel,
    POProcessingSummaryViewModel,
    ProjectActionViewModel,
    ProjectDetailViewModel,
    ProjectEditorStateViewModel,
    ProjectSummaryViewModel,
    RemoteConnectionTestResultViewModel,
    SettingsOptionViewModel,
    SettingsStateViewModel,
    SiteEditorViewModel,
    SyncStatusViewModel,
    build_connection_type_options,
    build_default_app_settings,
    build_default_site_editor,
    build_framework_type_options_from_descriptors,
    build_project_editor_state,
    build_settings_state,
    build_sync_rule_behavior_options,
    build_sync_rule_filter_type_options,
)
from polyglot_site_translator.services.remote_connections import RemoteConnectionService


def _default_actions() -> list[ProjectActionViewModel]:
    return [
        ProjectActionViewModel(
            key="sync",
            label="Sync Remote",
            description="Preview a synchronization workflow through a test double.",
        ),
        ProjectActionViewModel(
            key="audit",
            label="Run Audit",
            description="Return a deterministic audit summary from a test double.",
        ),
        ProjectActionViewModel(
            key="po-processing",
            label="Process PO",
            description="Return a deterministic PO-processing summary from a test double.",
        ),
    ]


def _default_connection_type_options() -> list[SettingsOptionViewModel]:
    remote_connection_service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.discover_installed()
    )
    return build_connection_type_options(
        descriptors=remote_connection_service.list_supported_connection_types()
    )


@dataclass
class InMemoryProjectCatalogService:
    """In-memory catalog double for frontend tests."""

    projects: list[ProjectSummaryViewModel]

    def list_projects(self) -> list[ProjectSummaryViewModel]:
        return list(self.projects)

    def get_project_detail(self, project_id: str) -> ProjectDetailViewModel:
        for project in self.projects:
            if project.id == project_id:
                return ProjectDetailViewModel(
                    project=project,
                    default_locale="en_US",
                    configuration_summary="Framework adapter and storage wiring are pending.",
                    metadata_summary=(
                        "This screen is prepared for site registry, sync, audit and PO workflows."
                    ),
                    actions=_default_actions(),
                )
        msg = f"Unknown project id: {project_id}"
        raise LookupError(msg)


class FailingSiteRegistryCatalogService:
    """Catalog double that always surfaces a controlled site registry failure."""

    def list_projects(self) -> list[ProjectSummaryViewModel]:
        msg = "SQLite site registry is temporarily unavailable."
        raise ControlledServiceError(msg)

    def get_project_detail(self, project_id: str) -> ProjectDetailViewModel:
        msg = f"SQLite site registry is temporarily unavailable for {project_id}."
        raise ControlledServiceError(msg)


@dataclass(frozen=True)
class StubProjectWorkflowService:
    """Deterministic workflow double for implemented presentation flows."""

    fail_sync: bool = False

    def start_sync(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        if self.fail_sync and project_id == "wp-site":
            msg = "Sync preview is unavailable for this project."
            raise ControlledServiceError(msg)
        return SyncStatusViewModel(
            status="completed",
            files_synced=12,
            summary="Synchronized 12 files into the local workspace preview.",
            error_code=None,
        )

    def start_sync_to_remote(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        return SyncStatusViewModel(
            status="completed",
            files_synced=7,
            summary="Uploaded 7 files from the local workspace preview.",
            error_code=None,
        )

    def trust_remote_host_key(self, project_id: str) -> RemoteConnectionTestResultViewModel:
        return RemoteConnectionTestResultViewModel(
            success=True,
            message=f"Trusted SSH host key for {project_id}.",
            error_code=None,
        )

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        return AuditSummaryViewModel(
            status="completed",
            findings_count=0,
            findings_summary="No supported framework was detected for this project.",
        )

    def start_po_processing(
        self,
        project_id: str,
        locales: str | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        del progress_callback
        return POProcessingSummaryViewModel(
            status="completed",
            processed_families=4,
            progress_current=0,
            progress_total=0,
            progress_is_indeterminate=False,
            summary=(
                "Families processed: 4 | PO files discovered: 4 | "
                "Synchronized entries: 0 | Translated entries: 0 | Failed entries: 0"
            ),
            current_file=None,
            current_entry=None,
        )


@dataclass
class InMemorySettingsService:
    """In-memory settings double for frontend tests."""

    _saved_settings: AppSettingsViewModel
    fail_load: bool = False
    fail_save: bool = False

    def load_settings(self) -> SettingsStateViewModel:
        if self.fail_load:
            msg = "App settings are temporarily unavailable."
            raise ControlledServiceError(msg)
        return build_settings_state(
            app_settings=self._saved_settings,
            status="loaded",
            status_message="Settings loaded.",
        )

    def save_settings(self, app_settings: AppSettingsViewModel) -> SettingsStateViewModel:
        if self.fail_save:
            msg = "App settings could not be saved."
            raise ControlledServiceError(msg)
        self._saved_settings = replace(
            app_settings,
            default_project_locale=normalize_default_locale(
                app_settings.default_project_locale,
                label="Default project locale",
            ),
        )
        return build_settings_state(
            app_settings=self._saved_settings,
            status="saved",
            status_message="Settings saved.",
        )

    def reset_settings(self) -> SettingsStateViewModel:
        self._saved_settings = build_default_app_settings()
        return build_settings_state(
            app_settings=self._saved_settings,
            status="defaults-restored",
            status_message="Settings restored to defaults.",
        )


@dataclass
class InMemoryProjectRegistryManagementService:
    """In-memory registry-management double for frontend tests."""

    catalog: InMemoryProjectCatalogService

    def build_create_project_editor(self) -> ProjectEditorStateViewModel:
        return build_project_editor_state(
            mode="create",
            editor=build_default_site_editor(),
            framework_options=build_framework_type_options_from_descriptors(
                FrameworkAdapterRegistry.discover_installed().list_framework_descriptors()
            ),
            connection_type_options=_default_connection_type_options(),
            sync_rule_filter_type_options=build_sync_rule_filter_type_options(),
            sync_rule_behavior_options=build_sync_rule_behavior_options(),
            connection_test_enabled=False,
            connection_test_result=None,
            sync_scope_status="framework_unresolved",
            sync_scope_message="No framework scope has been resolved in the frontend test double.",
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
                connection_type=NO_REMOTE_CONNECTION_VALUE,
                remote_host="",
                remote_port="",
                remote_username="",
                remote_password="",
                remote_path="",
                is_active=True,
            ),
            framework_options=build_framework_type_options_from_descriptors(
                FrameworkAdapterRegistry.discover_installed().list_framework_descriptors()
            ),
            connection_type_options=_default_connection_type_options(),
            sync_rule_filter_type_options=build_sync_rule_filter_type_options(),
            sync_rule_behavior_options=build_sync_rule_behavior_options(),
            connection_test_enabled=False,
            connection_test_result=None,
            sync_scope_status="framework_unresolved",
            sync_scope_message="No framework scope has been resolved in the frontend test double.",
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

    def test_remote_connection(
        self,
        editor: SiteEditorViewModel,
    ) -> RemoteConnectionTestResultViewModel:
        success = editor.connection_type != NO_REMOTE_CONNECTION_VALUE and editor.remote_host != ""
        message = "Connected successfully using the frontend test double."
        if not success:
            message = "Remote connection test requires a configured remote connection."
        return RemoteConnectionTestResultViewModel(
            success=success,
            message=message,
            error_code=None if success else "invalid_remote_config",
        )

    def preview_project_editor(
        self,
        editor: SiteEditorViewModel,
        *,
        mode: str,
    ) -> ProjectEditorStateViewModel:
        return build_project_editor_state(
            mode=mode,
            editor=editor,
            framework_options=build_framework_type_options_from_descriptors(
                FrameworkAdapterRegistry.discover_installed().list_framework_descriptors()
            ),
            connection_type_options=_default_connection_type_options(),
            sync_rule_filter_type_options=build_sync_rule_filter_type_options(),
            sync_rule_behavior_options=build_sync_rule_behavior_options(),
            connection_test_enabled=False,
            connection_test_result=None,
            sync_scope_status="filtered" if editor.use_adapter_sync_filters else "no_filters",
            sync_scope_message="Project editor preview rebuilt by the frontend test double.",
            status="editing",
            status_message="Project editor draft updated.",
        )


def build_seeded_services() -> FrontendServices:
    return build_seeded_services_with_settings(
        InMemorySettingsService(_saved_settings=build_default_app_settings())
    )


def build_seeded_services_with_settings(settings_service: SettingsService) -> FrontendServices:
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
        workflows=StubProjectWorkflowService(),
        settings=settings_service,
        registry=InMemoryProjectRegistryManagementService(catalog=catalog),
    )


def build_empty_services() -> FrontendServices:
    catalog = InMemoryProjectCatalogService(projects=[])
    return FrontendServices(
        catalog=catalog,
        workflows=StubProjectWorkflowService(),
        settings=InMemorySettingsService(_saved_settings=build_default_app_settings()),
        registry=InMemoryProjectRegistryManagementService(catalog=catalog),
    )


def build_failing_sync_services() -> FrontendServices:
    services = build_seeded_services()
    return FrontendServices(
        catalog=services.catalog,
        workflows=StubProjectWorkflowService(fail_sync=True),
        settings=services.settings,
        registry=services.registry,
    )


def build_failing_settings_load_services() -> FrontendServices:
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
