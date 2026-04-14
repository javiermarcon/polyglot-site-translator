"""Runtime service wiring for the frontend shell."""

from __future__ import annotations

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.settings import TomlSettingsService
from polyglot_site_translator.infrastructure.site_registry_sqlite import (
    ConfiguredSqliteSiteRegistryRepository,
)
from polyglot_site_translator.infrastructure.sync_scope_sqlite import (
    ConfiguredSqliteSyncScopeRepository,
)
from polyglot_site_translator.presentation.contracts import FrontendServices
from polyglot_site_translator.presentation.site_registry_services import (
    SiteRegistryPresentationCatalogService,
    SiteRegistryPresentationManagementService,
    SiteRegistryPresentationWorkflowService,
)
from polyglot_site_translator.services.framework_detection import (
    FrameworkDetectionService,
)
from polyglot_site_translator.services.framework_sync_scope import (
    FrameworkSyncScopeService,
)
from polyglot_site_translator.services.project_sync import ProjectSyncService
from polyglot_site_translator.services.remote_connections import RemoteConnectionService
from polyglot_site_translator.services.site_registry import SiteRegistryService


def build_default_frontend_services(
    *,
    settings_service: TomlSettingsService,
    remote_connection_service: RemoteConnectionService | None = None,
    project_sync_service: ProjectSyncService | None = None,
) -> FrontendServices:
    """Return the default runtime services with real SQLite site registry persistence."""
    repository = ConfiguredSqliteSiteRegistryRepository(settings_service)
    framework_registry = FrameworkAdapterRegistry.discover_installed()
    framework_detection_service = FrameworkDetectionService(registry=framework_registry)
    resolved_remote_connection_service = remote_connection_service or RemoteConnectionService(
        registry=RemoteConnectionRegistry.discover_installed()
    )
    sync_scope_repository = ConfiguredSqliteSyncScopeRepository(settings_service)
    site_registry_service = SiteRegistryService(
        repository=repository,
        framework_detection_service=framework_detection_service,
        remote_connection_service=resolved_remote_connection_service,
    )
    resolved_project_sync_service = project_sync_service or ProjectSyncService(
        registry=RemoteConnectionRegistry.discover_installed(),
        framework_sync_scope_service=FrameworkSyncScopeService(
            registry=framework_registry,
            sync_scope_settings_provider=sync_scope_repository.load_sync_scope_settings,
        ),
    )
    framework_sync_scope_service = FrameworkSyncScopeService(
        registry=framework_registry,
        sync_scope_settings_provider=sync_scope_repository.load_sync_scope_settings,
    )
    return FrontendServices(
        catalog=SiteRegistryPresentationCatalogService(site_registry_service),
        workflows=SiteRegistryPresentationWorkflowService(
            service=site_registry_service,
            project_sync_service=resolved_project_sync_service,
        ),
        settings=settings_service,
        registry=SiteRegistryPresentationManagementService(
            service=site_registry_service,
            settings_service=settings_service,
            framework_sync_scope_service=framework_sync_scope_service,
        ),
    )
