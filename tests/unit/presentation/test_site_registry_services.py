"""Unit tests for presentation adapters around the real site registry service."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.domain.framework_detection.errors import (
    FrameworkDetectionAmbiguityError,
)
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryConflictError,
    SiteRegistryNotFoundError,
    SiteRegistryPersistenceError,
)
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteProject,
    SiteRegistrationInput,
)
from polyglot_site_translator.domain.sync.models import (
    RemoteSyncFile,
    SyncDirection,
    SyncProgressEvent,
    SyncResult,
    SyncSummary,
)
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.settings import TomlSettingsService
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.site_registry_services import (
    SiteRegistryPresentationCatalogService,
    SiteRegistryPresentationManagementService,
    SiteRegistryPresentationWorkflowService,
    _build_project_detail,
)
from polyglot_site_translator.presentation.view_models import (
    SettingsStateViewModel,
    SiteEditorViewModel,
    build_default_app_settings,
    build_settings_state,
)
from polyglot_site_translator.services.framework_detection import FrameworkDetectionService
from polyglot_site_translator.services.remote_connections import RemoteConnectionService
from polyglot_site_translator.services.site_registry import SiteRegistryService


class InMemorySiteRegistryRepository:
    """Small test repository for presentation adapter coverage."""

    def __init__(self) -> None:
        self.sites: dict[str, RegisteredSite] = {}

    def create_site(self, site: RegisteredSite) -> RegisteredSite:
        self.sites[site.id] = site
        return site

    def list_sites(self) -> list[RegisteredSite]:
        return list(self.sites.values())

    def get_site(self, site_id: str) -> RegisteredSite:
        if site_id not in self.sites:
            msg = f"Unknown site id: {site_id}"
            raise SiteRegistryNotFoundError(msg)
        return self.sites[site_id]

    def update_site(self, site: RegisteredSite) -> RegisteredSite:
        if site.id not in self.sites:
            msg = f"Unknown site id: {site.id}"
            raise SiteRegistryNotFoundError(msg)
        self.sites[site.id] = site
        return site

    def delete_site(self, site_id: str) -> None:
        self.sites.pop(site_id, None)


class PersistenceFailingRepository(InMemorySiteRegistryRepository):
    """Repository fake that fails every access with a persistence error."""

    def list_sites(self) -> list[RegisteredSite]:
        msg = "SQLite site registry read failed."
        raise SiteRegistryPersistenceError(msg)

    def get_site(self, site_id: str) -> RegisteredSite:
        msg = "SQLite site registry read failed."
        raise SiteRegistryPersistenceError(msg)


class SuccessfulSFTPProvider:
    """Remote connection provider stub for presentation tests."""

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type="sftp",
        display_name="SFTP",
        default_port=22,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        return RemoteConnectionTestResult(
            success=True,
            connection_type=config.connection_type,
            host=config.host,
            port=config.port,
            message="Connected successfully.",
            error_code=None,
        )

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
        *,
        max_files: int = 1000,
    ) -> list[RemoteSyncFile]:
        return []

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        return iter(())

    def open_session(self, config: RemoteConnectionConfig) -> Any:
        msg = f"open_session not used in this test for {config.connection_type}"
        raise AssertionError(msg)

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> bytes:
        msg = f"download not used in this test for {remote_path}"
        raise AssertionError(msg)


class SyncStub:
    """Project sync stub for workflow-constructor compatibility in audit tests."""

    def sync_remote_to_local(
        self,
        site: RegisteredSite,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncResult:
        return SyncResult(
            direction=SyncDirection.REMOTE_TO_LOCAL,
            success=True,
            project_id=site.id,
            connection_type=(
                site.remote_connection.connection_type if site.remote_connection else None
            ),
            local_path=site.local_path,
            summary=SyncSummary(
                files_discovered=0,
                files_downloaded=0,
                directories_created=0,
                bytes_downloaded=0,
            ),
            error=None,
        )


def test_catalog_service_maps_project_summaries_and_detail() -> None:
    repository = InMemorySiteRegistryRepository()
    service = _build_domain_service(repository)
    created = service.create_site(_build_registration(framework_type="custom_cms"))
    catalog = SiteRegistryPresentationCatalogService(service)

    projects = catalog.list_projects()
    detail = catalog.get_project_detail(created.id)

    assert projects[0].status == "Active"
    assert projects[0].framework == "Custom_Cms"
    assert "Remote user: deploy" in detail.metadata_summary
    assert "No framework detected" in detail.metadata_summary


def test_catalog_service_wraps_controlled_errors() -> None:
    catalog = SiteRegistryPresentationCatalogService(
        SiteRegistryService(repository=PersistenceFailingRepository())
    )

    with pytest.raises(ControlledServiceError, match=r"SQLite site registry read failed\."):
        catalog.list_projects()

    with pytest.raises(ControlledServiceError, match=r"SQLite site registry read failed\."):
        catalog.get_project_detail("missing-site")


def test_management_service_builds_create_and_edit_editor_states(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    repository = InMemorySiteRegistryRepository()
    domain_service = _build_domain_service(repository)
    created = domain_service.create_site(_build_registration())
    management = SiteRegistryPresentationManagementService(
        service=domain_service,
        settings_service=settings_service,
    )

    create_state = management.build_create_project_editor()
    edit_state = management.build_edit_project_editor(created.id)

    assert create_state.mode == "create"
    assert create_state.editor.local_path.endswith("/site")
    assert [option.value for option in create_state.framework_options] == [
        "unknown",
        "django",
        "flask",
        "wordpress",
    ]
    assert [option.value for option in create_state.connection_type_options] == [
        "none",
        "sftp",
    ]
    assert edit_state.mode == "edit"
    assert edit_state.editor.site_id == created.id


def test_management_service_wraps_build_edit_errors(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=settings_service,
    )

    with pytest.raises(ControlledServiceError, match=r"Unknown site id: missing-site"):
        management.build_edit_project_editor("missing-site")


def test_management_service_wraps_build_create_configuration_errors(tmp_path: Path) -> None:
    class InvalidSettingsService(TomlSettingsService):
        def load_settings(self) -> SettingsStateViewModel:
            return build_settings_state(
                app_settings=replace(
                    build_default_app_settings(database_directory=str(tmp_path)),
                    database_filename="",
                ),
                status="loaded",
                status_message="Settings loaded.",
            )

    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=InvalidSettingsService(tmp_path / "settings.toml"),
    )

    with pytest.raises(ControlledServiceError, match=r"Database filename must not be empty\."):
        management.build_create_project_editor()


def test_management_service_wraps_invalid_editor_payloads_and_missing_sites(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    repository = InMemorySiteRegistryRepository()
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(repository),
        settings_service=settings_service,
    )

    invalid_editor = replace(_build_editor(), remote_port="not-a-number")

    with pytest.raises(ControlledServiceError, match=r"invalid literal for int"):
        management.create_project(invalid_editor)

    with pytest.raises(ControlledServiceError, match=r"Unknown site id: missing-site"):
        management.update_project("missing-site", _build_editor())


def test_management_service_wraps_domain_conflicts(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    repository = InMemorySiteRegistryRepository()
    _build_domain_service(repository).create_site(_build_registration())

    class ConflictRepository(InMemorySiteRegistryRepository):
        def create_site(self, site: RegisteredSite) -> RegisteredSite:
            msg = "A site with the name 'Marketing Site' already exists."
            raise SiteRegistryConflictError(msg)

    conflict_management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(ConflictRepository()),
        settings_service=settings_service,
    )

    with pytest.raises(
        ControlledServiceError,
        match=r"A site with the name 'Marketing Site' already exists\.",
    ):
        conflict_management.create_project(_build_editor())


def test_management_service_updates_projects_successfully(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    repository = InMemorySiteRegistryRepository()
    domain_service = _build_domain_service(repository)
    created = domain_service.create_site(_build_registration())
    management = SiteRegistryPresentationManagementService(
        service=domain_service,
        settings_service=settings_service,
    )

    detail = management.update_project(
        created.id,
        replace(_build_editor(), local_path="/workspace/marketing-site-v2"),
    )

    assert detail.project.local_path == "/workspace/marketing-site-v2"


def test_management_service_tests_remote_connections_successfully(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=settings_service,
    )

    result = management.test_remote_connection(_build_editor())

    assert result.success is True
    assert result.message == "Connected successfully."


def test_management_service_preserves_remote_host_verification_choice(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    domain_service = _build_domain_service(InMemorySiteRegistryRepository())
    management = SiteRegistryPresentationManagementService(
        service=domain_service,
        settings_service=settings_service,
    )

    created_project = management.create_project(replace(_build_editor(), remote_verify_host=False))

    persisted_site = domain_service.get_site(created_project.project.id)
    assert persisted_site.remote_connection is not None
    assert persisted_site.remote_connection.flags.verify_host is False


def test_framework_aware_workflow_service_builds_audit_preview_from_detection() -> None:
    repository = InMemorySiteRegistryRepository()
    service = _build_domain_service(repository)
    created = service.create_site(_build_registration())
    workflow = SiteRegistryPresentationWorkflowService(
        service=service,
        project_sync_service=SyncStub(),
    )

    audit = workflow.start_audit(created.id)

    assert audit.status == "completed"
    assert audit.findings_count == 0
    assert "No supported framework was detected" in audit.findings_summary


def test_workflow_service_trusts_remote_host_key_with_explicit_confirmation() -> None:
    repository = InMemorySiteRegistryRepository()
    service = _build_domain_service(repository)
    created = service.create_site(_build_registration())
    workflow = SiteRegistryPresentationWorkflowService(
        service=service,
        project_sync_service=SyncStub(),
    )

    result = workflow.trust_remote_host_key(created.id)

    assert result.success is True
    assert result.message == "Connected successfully."


def test_workflow_service_wraps_host_key_trust_without_remote_connection() -> None:
    repository = InMemorySiteRegistryRepository()
    service = _build_domain_service(repository)
    created = service.create_site(
        SiteRegistrationInput(
            name="Local Only",
            framework_type="wordpress",
            local_path="/workspace/local-only",
            default_locale="en_US",
            remote_connection=None,
            is_active=True,
        )
    )
    workflow = SiteRegistryPresentationWorkflowService(
        service=service,
        project_sync_service=SyncStub(),
    )

    with pytest.raises(
        ControlledServiceError,
        match=r"Remote host-key trust requires a configured remote connection\.",
    ):
        workflow.trust_remote_host_key(created.id)


def test_framework_aware_workflow_service_builds_matched_audit_preview(tmp_path: Path) -> None:
    project_path = tmp_path / "wordpress-site"
    project_path.mkdir()
    (project_path / "wp-config.php").write_text("<?php\n", encoding="utf-8")
    (project_path / "wp-content").mkdir()
    (project_path / "wp-includes").mkdir()
    repository = InMemorySiteRegistryRepository()
    service = SiteRegistryService(
        repository=repository,
        framework_detection_service=FrameworkDetectionService(
            registry=FrameworkAdapterRegistry.discover_installed()
        ),
        remote_connection_service=_build_remote_connection_service(),
    )
    created = service.create_site(
        _build_registration(framework_type="unknown", local_path=str(project_path))
    )
    workflow = SiteRegistryPresentationWorkflowService(
        service=service,
        project_sync_service=SyncStub(),
    )

    audit = workflow.start_audit(created.id)

    assert audit.status == "completed"
    assert audit.findings_count > 0
    assert "wp-config.php" in audit.findings_summary


def test_framework_aware_workflow_service_wraps_lookup_errors() -> None:
    workflow = SiteRegistryPresentationWorkflowService(
        service=SiteRegistryService(repository=InMemorySiteRegistryRepository()),
        project_sync_service=SyncStub(),
    )

    with pytest.raises(ControlledServiceError, match=r"Unknown site id: missing-site"):
        workflow.start_audit("missing-site")


def test_build_project_detail_without_detection_keeps_base_metadata_only() -> None:
    detail = _build_project_detail(
        RegisteredSite(
            project=SiteProject(
                id="site-1",
                name="Marketing Site",
                framework_type="wordpress",
                local_path="/workspace/marketing-site",
                default_locale="en_US",
                is_active=True,
            ),
            remote_connection=RemoteConnectionConfig(
                id="remote-site-1",
                site_project_id="site-1",
                connection_type="ftp",
                host="ftp.example.com",
                port=21,
                username="deploy",
                password="secret",
                remote_path="/public_html",
            ),
        )
    )

    assert (
        detail.metadata_summary
        == "Framework: WordPress | Remote user: deploy | Connection type: ftp"
    )


def test_catalog_service_wraps_framework_detection_ambiguity() -> None:
    repository = InMemorySiteRegistryRepository()

    class AmbiguousDetectionService(SiteRegistryService):
        def detect_framework(self, project_path: str) -> FrameworkDetectionResult:
            msg = "Multiple framework adapters matched the project path with the same confidence."
            raise FrameworkDetectionAmbiguityError(msg)

    service = AmbiguousDetectionService(repository=repository)
    created = service.create_site(_build_registration())
    catalog = SiteRegistryPresentationCatalogService(service)

    with pytest.raises(
        ControlledServiceError,
        match=r"Multiple framework adapters matched the project path with the same confidence\.",
    ):
        catalog.get_project_detail(created.id)


def _build_domain_service(repository: InMemorySiteRegistryRepository) -> SiteRegistryService:
    return SiteRegistryService(
        repository=repository,
        framework_detection_service=FrameworkDetectionService(
            registry=FrameworkAdapterRegistry.discover_installed()
        ),
        remote_connection_service=_build_remote_connection_service(),
    )


def _build_remote_connection_service() -> RemoteConnectionService:
    return RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(providers=[SuccessfulSFTPProvider()])
    )


def _build_registration(
    *,
    framework_type: str = "wordpress",
    local_path: str = "/workspace/marketing-site",
) -> SiteRegistrationInput:
    return SiteRegistrationInput(
        name="Marketing Site",
        framework_type=framework_type,
        local_path=local_path,
        default_locale="en_US",
        remote_connection=RemoteConnectionConfigInput(
            connection_type="sftp",
            host="example.com",
            port=22,
            username="deploy",
            password="super-secret",
            remote_path="/srv/app",
        ),
        is_active=True,
    )


def _build_editor() -> SiteEditorViewModel:
    return SiteEditorViewModel(
        site_id=None,
        name="Marketing Site",
        framework_type="wordpress",
        local_path="/workspace/marketing-site",
        default_locale="en_US",
        connection_type="sftp",
        remote_host="example.com",
        remote_port="22",
        remote_username="deploy",
        remote_password="super-secret",
        remote_path="/srv/app",
        is_active=True,
    )
