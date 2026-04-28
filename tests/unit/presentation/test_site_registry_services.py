"""Unit tests for presentation adapters around the real site registry service."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import polib
import pytest

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.domain.framework_detection.errors import (
    FrameworkDetectionAmbiguityError,
)
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingCompilationError,
    POProcessingTranslationError,
)
from polyglot_site_translator.domain.po_processing.models import (
    POFileData,
    POProcessingProgress,
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
from polyglot_site_translator.domain.sync.errors import SyncConfigurationError
from polyglot_site_translator.domain.sync.models import (
    RemoteSyncFile,
    SyncDirection,
    SyncProgressEvent,
    SyncResult,
    SyncSummary,
)
from polyglot_site_translator.domain.sync.scope import (
    SyncFilterType,
    SyncRuleBehavior,
    build_sync_rule_key,
)
from polyglot_site_translator.infrastructure.po_files import PolibPOCatalogRepository
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
    _build_sync_status,
)
from polyglot_site_translator.presentation.view_models import (
    SettingsStateViewModel,
    SiteEditorViewModel,
    SyncRuleEditorItemViewModel,
    build_default_app_settings,
    build_settings_state,
)
from polyglot_site_translator.services.framework_detection import FrameworkDetectionService
from polyglot_site_translator.services.framework_sync_scope import FrameworkSyncScopeService
from polyglot_site_translator.services.po_processing import POProcessingService
from polyglot_site_translator.services.remote_connections import RemoteConnectionService
from polyglot_site_translator.services.site_registry import SiteRegistryService


class _StubPOTranslationProvider:
    def translate_text(self, *, text: str, target_locale: str) -> str:
        translations = {("es_ES", "Save"): "Guardar", ("es_AR", "Save"): "Guardar"}
        return translations[(target_locale, text)]


class _PartiallyFailingPOTranslationProvider:
    def translate_text(self, *, text: str, target_locale: str) -> str:
        if text == "Broken":
            msg = f"translation failed for {target_locale}:{text}"
            raise POProcessingTranslationError(msg)
        translations = {("es_ES", "Save"): "Guardar"}
        return translations[(target_locale, text)]


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

    def ensure_remote_directory(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> int:
        msg = f"ensure_remote_directory not used in this test for {remote_path}"
        raise AssertionError(msg)

    def upload_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        contents: bytes,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> None:
        msg = f"upload not used in this test for {remote_path}"
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

    def sync_local_to_remote(
        self,
        site: RegisteredSite,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncResult:
        return SyncResult(
            direction=SyncDirection.LOCAL_TO_REMOTE,
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
                files_uploaded=0,
                bytes_uploaded=0,
            ),
            error=None,
        )


class FailingFrameworkSyncScopeService:
    def resolve_for_framework(
        self,
        *,
        framework_type: str,
        project_path: Path | str,
        project_rule_overrides: tuple[object, ...] = (),
    ) -> Any:
        del framework_type, project_path, project_rule_overrides
        msg = "broken sync scope"
        raise SyncConfigurationError(msg)


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


def test_management_service_preserves_filtered_sync_preference_in_payloads(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    repository = InMemorySiteRegistryRepository()
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(repository),
        settings_service=settings_service,
    )

    created_project = management.create_project(
        replace(_build_editor(), use_adapter_sync_filters=True)
    )

    persisted_site = repository.get_site(created_project.project.id)

    assert persisted_site.remote_connection is not None
    assert persisted_site.remote_connection.flags.use_adapter_sync_filters is True


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
        framework_sync_scope_service=_build_framework_sync_scope_service(),
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
    assert create_state.sync_scope_status == "framework_unresolved"
    assert edit_state.mode == "edit"
    assert edit_state.editor.site_id == created.id


def test_management_service_builds_create_state_from_translation_defaults(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.save_settings(
        replace(
            build_default_app_settings(database_directory=str(tmp_path)),
            default_project_locale="es_AR,es_ES",
        )
    )
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=settings_service,
    )

    create_state = management.build_create_project_editor()

    assert create_state.editor.default_locale == "es_AR,es_ES"


def test_management_service_builds_create_state_from_translation_compile_defaults(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.save_settings(
        replace(
            build_default_app_settings(database_directory=str(tmp_path)),
            default_compile_mo=False,
        )
    )
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=settings_service,
    )

    create_state = management.build_create_project_editor()

    assert create_state.editor.compile_mo is False


def test_management_service_builds_edit_state_for_projects_without_remote_connection(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    repository = InMemorySiteRegistryRepository()
    domain_service = _build_domain_service(repository)
    created = domain_service.create_site(
        SiteRegistrationInput(
            name="Local Only",
            framework_type="django",
            local_path="/workspace/local-only",
            default_locale="en_US",
            remote_connection=None,
            is_active=True,
        )
    )
    management = SiteRegistryPresentationManagementService(
        service=domain_service,
        settings_service=settings_service,
        framework_sync_scope_service=_build_framework_sync_scope_service(),
    )

    edit_state = management.build_edit_project_editor(created.id)

    assert edit_state.editor.connection_type == "none"
    assert edit_state.editor.remote_host == ""
    assert "locale" in [item.relative_path for item in edit_state.editor.sync_rule_items]


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
        framework_sync_scope_service=_build_framework_sync_scope_service(),
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


def test_management_service_wraps_remote_connection_test_payload_errors(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=settings_service,
    )

    with pytest.raises(ControlledServiceError, match=r"invalid literal for int"):
        management.test_remote_connection(replace(_build_editor(), remote_port="invalid-port"))


def test_management_service_preserves_remote_host_verification_choice(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    domain_service = _build_domain_service(InMemorySiteRegistryRepository())
    management = SiteRegistryPresentationManagementService(
        service=domain_service,
        settings_service=settings_service,
        framework_sync_scope_service=_build_framework_sync_scope_service(),
    )

    created_project = management.create_project(replace(_build_editor(), remote_verify_host=False))

    persisted_site = domain_service.get_site(created_project.project.id)
    assert persisted_site.remote_connection is not None
    assert persisted_site.remote_connection.flags.verify_host is False


def test_management_service_previews_resolved_scope_and_project_rules(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=settings_service,
        framework_sync_scope_service=_build_framework_sync_scope_service(),
    )

    preview = management.preview_project_editor(
        replace(
            _build_editor(),
            framework_type="django",
            use_adapter_sync_filters=True,
            sync_rule_items=(
                SyncRuleEditorItemViewModel(
                    rule_key="",
                    target_rule_key=None,
                    relative_path="locale_custom",
                    filter_type="directory",
                    behavior="include",
                    description="Project locale override",
                    source="project",
                    is_enabled=True,
                    is_removable=True,
                ),
            ),
        ),
        mode="create",
    )

    assert preview.sync_scope_status == "filtered"
    assert "locale" in [item.relative_path for item in preview.editor.sync_rule_items]
    assert ".venv" in [item.relative_path for item in preview.editor.sync_rule_items]
    assert "locale_custom" in [item.relative_path for item in preview.editor.sync_rule_items]


def test_management_service_keeps_editor_usable_when_sync_scope_resolution_fails(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=settings_service,
        framework_sync_scope_service=FailingFrameworkSyncScopeService(),  # type: ignore[arg-type]
    )

    preview = management.preview_project_editor(
        replace(_build_editor(), framework_type="django", use_adapter_sync_filters=True),
        mode="create",
    )

    assert preview.status == "editing"
    assert preview.sync_scope_status == "adapter_unavailable"
    assert preview.sync_scope_message == (
        "Framework sync scope resolution failed. Cause: broken sync scope"
    )


def test_management_service_persists_project_sync_rule_overrides(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    repository = InMemorySiteRegistryRepository()
    domain_service = _build_domain_service(repository)
    management = SiteRegistryPresentationManagementService(
        service=domain_service,
        settings_service=settings_service,
        framework_sync_scope_service=_build_framework_sync_scope_service(),
    )
    preview = management.preview_project_editor(
        replace(
            _build_editor(),
            framework_type="django",
            use_adapter_sync_filters=True,
        ),
        mode="create",
    )
    disabled_cache_rule_items = (
        *(
            item
            if item.relative_path != "__pycache__"
            else SyncRuleEditorItemViewModel(
                rule_key=item.rule_key,
                target_rule_key=item.target_rule_key,
                relative_path=item.relative_path,
                filter_type=item.filter_type,
                behavior=item.behavior,
                description=item.description,
                source=item.source,
                is_enabled=False,
                is_removable=item.is_removable,
            )
            for item in preview.editor.sync_rule_items
        ),
        SyncRuleEditorItemViewModel(
            rule_key="",
            target_rule_key=None,
            relative_path="locale_custom",
            filter_type="directory",
            behavior="include",
            description="Project locale override",
            source="project",
            is_enabled=True,
            is_removable=True,
        ),
    )

    created_project = management.create_project(
        replace(
            _build_editor(),
            framework_type="django",
            use_adapter_sync_filters=True,
            sync_rule_items=disabled_cache_rule_items,
        )
    )
    persisted_site = domain_service.get_site(created_project.project.id)

    assert persisted_site.remote_connection is not None
    assert persisted_site.remote_connection.flags.sync_rule_overrides != ()
    assert any(
        override.rule_key
        == build_sync_rule_key(
            relative_path="locale_custom",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.INCLUDE,
        )
        for override in persisted_site.remote_connection.flags.sync_rule_overrides
    )
    assert any(
        override.target_rule_key
        == build_sync_rule_key(
            relative_path="__pycache__",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.EXCLUDE,
        )
        and override.is_enabled is False
        for override in persisted_site.remote_connection.flags.sync_rule_overrides
    )

    reloaded_editor = management.build_edit_project_editor(created_project.project.id)
    matching_custom_rules = [
        item
        for item in reloaded_editor.editor.sync_rule_items
        if item.relative_path == "locale_custom"
    ]
    matching_cache_rules = [
        item
        for item in reloaded_editor.editor.sync_rule_items
        if item.relative_path == "__pycache__"
    ]
    assert matching_custom_rules and matching_custom_rules[0].source == "project"
    assert matching_cache_rules and matching_cache_rules[0].is_enabled is False


def test_management_service_wraps_invalid_sync_rule_preview_payloads(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=settings_service,
        framework_sync_scope_service=_build_framework_sync_scope_service(),
    )

    with pytest.raises(ControlledServiceError, match=r"Sync rule paths must not be blank\."):
        management.preview_project_editor(
            replace(
                _build_editor(),
                sync_rule_items=(
                    SyncRuleEditorItemViewModel(
                        rule_key="",
                        target_rule_key=None,
                        relative_path="",
                        filter_type="directory",
                        behavior="include",
                        description="invalid",
                        source="project",
                        is_enabled=True,
                        is_removable=True,
                    ),
                ),
            ),
            mode="create",
        )


def test_management_service_wraps_duplicate_sync_rule_payloads(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=settings_service,
        framework_sync_scope_service=_build_framework_sync_scope_service(),
    )
    duplicate_rule = SyncRuleEditorItemViewModel(
        rule_key="",
        target_rule_key=None,
        relative_path="locale_custom",
        filter_type="directory",
        behavior="include",
        description="duplicate",
        source="project",
        is_enabled=True,
        is_removable=True,
    )

    with pytest.raises(
        ControlledServiceError,
        match=r"Duplicate sync rule detected for 'locale_custom'\.",
    ):
        management.preview_project_editor(
            replace(
                _build_editor(),
                sync_rule_items=(duplicate_rule, duplicate_rule),
            ),
            mode="create",
        )


def test_management_service_preview_without_scope_service_keeps_existing_rule_catalog(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    management = SiteRegistryPresentationManagementService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        settings_service=settings_service,
    )
    adapter_rule = SyncRuleEditorItemViewModel(
        rule_key="exclude:directory:__pycache__",
        target_rule_key=None,
        relative_path="__pycache__",
        filter_type="directory",
        behavior="exclude",
        description="Adapter cache rule",
        source="adapter",
        is_enabled=True,
        is_removable=False,
    )

    preview = management.preview_project_editor(
        replace(_build_editor(), sync_rule_items=(adapter_rule,)),
        mode="create",
    )

    assert preview.sync_scope_status == "adapter_unavailable"
    assert preview.editor.sync_rule_items[0].rule_key == "exclude:directory:__pycache__"
    assert preview.editor.sync_rule_items[0].target_rule_key == "exclude:directory:__pycache__"


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


def test_workflow_service_builds_po_processing_preview() -> None:
    repository = InMemorySiteRegistryRepository()
    site_service = _build_domain_service(repository)
    site = site_service.create_site(_build_registration(local_path="/workspace/marketing-site"))
    workflow = SiteRegistryPresentationWorkflowService(
        service=site_service,
        project_sync_service=SyncStub(),
        po_processing_service=POProcessingService(repository=PolibPOCatalogRepository()),
    )

    preview = workflow.start_po_processing(site.id)

    assert preview.status == "completed"
    assert preview.processed_families == 0
    assert preview.progress_current == 0
    assert preview.progress_total == 0
    assert "Families processed: 0" in preview.summary
    assert "Compiled MO files: 0" in preview.summary


def test_workflow_service_processes_po_variants_from_site_workspace(tmp_path: Path) -> None:
    locale_dir = tmp_path / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po_file(locale_dir / "messages-es_ES.po", [("Hello", "Hola")])
    _write_po_file(locale_dir / "messages-es_AR.po", [("Hello", "")])

    repository = InMemorySiteRegistryRepository()
    site_service = _build_domain_service(repository)
    site = site_service.create_site(
        SiteRegistrationInput(
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(tmp_path),
            default_locale="es_ES",
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
    )
    workflow = SiteRegistryPresentationWorkflowService(
        service=site_service,
        project_sync_service=SyncStub(),
        po_processing_service=POProcessingService(repository=PolibPOCatalogRepository()),
    )

    preview = workflow.start_po_processing(site.id)

    assert preview.status == "completed"
    assert preview.processed_families == 1
    assert preview.progress_current == 1
    assert preview.progress_total == 1
    assert "Synchronized entries: 1" in preview.summary
    assert "Translated entries: 0" in preview.summary
    assert "Compiled MO files: 2" in preview.summary


def test_workflow_service_processes_po_variants_from_selected_locales(tmp_path: Path) -> None:
    locale_dir = tmp_path / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po_file(locale_dir / "messages-pt_BR.po", [("Hello", "Ola")])
    _write_po_file(locale_dir / "messages-pt_PT.po", [("Hello", "")])

    repository = InMemorySiteRegistryRepository()
    site_service = _build_domain_service(repository)
    site = site_service.create_site(
        SiteRegistrationInput(
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(tmp_path),
            default_locale="es_ES",
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
    )
    workflow = SiteRegistryPresentationWorkflowService(
        service=site_service,
        project_sync_service=SyncStub(),
        po_processing_service=POProcessingService(repository=PolibPOCatalogRepository()),
    )

    preview = workflow.start_po_processing(site.id, "pt_BR")

    assert preview.status == "completed"
    assert preview.processed_families == 1
    assert preview.progress_current == 1
    assert preview.progress_total == 1
    assert "Synchronized entries: 1" in preview.summary
    assert "Translated entries: 0" in preview.summary
    assert "Compiled MO files: 2" in preview.summary


def test_workflow_service_reports_translated_entries_when_provider_is_used(tmp_path: Path) -> None:
    locale_dir = tmp_path / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po_file(locale_dir / "messages-es_ES.po", [("Save", "")])
    _write_po_file(locale_dir / "messages-es_AR.po", [("Save", "")])

    repository = InMemorySiteRegistryRepository()
    site_service = _build_domain_service(repository)
    site = site_service.create_site(
        SiteRegistrationInput(
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(tmp_path),
            default_locale="es_ES,es_AR",
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
    )
    workflow = SiteRegistryPresentationWorkflowService(
        service=site_service,
        project_sync_service=SyncStub(),
        po_processing_service=POProcessingService(
            repository=PolibPOCatalogRepository(),
            translation_provider=_StubPOTranslationProvider(),
        ),
    )

    preview = workflow.start_po_processing(site.id)

    assert preview.status == "completed"
    assert "Synchronized entries: 1" in preview.summary
    assert "Translated entries: 1" in preview.summary
    assert "Compiled MO files: 2" in preview.summary


def test_workflow_service_reports_partial_po_translation_failures(tmp_path: Path) -> None:
    locale_dir = tmp_path / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po_file(locale_dir / "messages-es_ES.po", [("Broken", ""), ("Save", "")])

    repository = InMemorySiteRegistryRepository()
    site_service = _build_domain_service(repository)
    site = site_service.create_site(
        SiteRegistrationInput(
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(tmp_path),
            default_locale="es_ES",
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
    )
    workflow = SiteRegistryPresentationWorkflowService(
        service=site_service,
        project_sync_service=SyncStub(),
        po_processing_service=POProcessingService(
            repository=PolibPOCatalogRepository(),
            translation_provider=_PartiallyFailingPOTranslationProvider(),
        ),
    )

    preview = workflow.start_po_processing(site.id)

    assert preview.status == "completed_with_errors"
    assert "Translated entries: 1" in preview.summary
    assert "Failed entries: 1" in preview.summary
    assert "Compiled MO files: 1" in preview.summary
    assert "locale/messages-es_ES.po" in preview.summary
    assert "Broken" in preview.summary


def test_workflow_service_reports_mo_compilation_failures_as_completed_with_errors(
    tmp_path: Path,
) -> None:
    locale_dir = tmp_path / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po_file(locale_dir / "messages-es_ES.po", [("Hello", "Hola")])
    _write_po_file(locale_dir / "messages-es_AR.po", [("Hello", "")])

    class _FailingCompileRepository(PolibPOCatalogRepository):
        def compile_mo_file(self, file_data: POFileData) -> None:
            if file_data.locale == "es_AR":
                msg = "MO file compilation failed for es_AR."
                raise POProcessingCompilationError(msg)
            super().compile_mo_file(file_data)

    repository = InMemorySiteRegistryRepository()
    site_service = _build_domain_service(repository)
    site = site_service.create_site(
        SiteRegistrationInput(
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(tmp_path),
            default_locale="es_ES",
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
    )
    workflow = SiteRegistryPresentationWorkflowService(
        service=site_service,
        project_sync_service=SyncStub(),
        po_processing_service=POProcessingService(repository=_FailingCompileRepository()),
    )

    preview = workflow.start_po_processing(site.id)

    assert preview.status == "completed_with_errors"
    assert "Compiled MO files: 1" in preview.summary
    assert "Failed MO files:" in preview.summary


def test_workflow_service_wraps_po_processing_lookup_errors() -> None:
    workflow = SiteRegistryPresentationWorkflowService(
        service=_build_domain_service(InMemorySiteRegistryRepository()),
        project_sync_service=SyncStub(),
        po_processing_service=POProcessingService(repository=PolibPOCatalogRepository()),
    )

    with pytest.raises(ControlledServiceError, match="Unknown site id: missing-site"):
        workflow.start_po_processing("missing-site")


def test_workflow_service_wraps_po_processing_service_errors() -> None:
    class _ExplodingPOService:
        def process_site(
            self,
            site: RegisteredSite,
            progress_callback: Callable[[POProcessingProgress], None] | None = None,
        ) -> object:
            del site, progress_callback
            msg = "PO workflow exploded."
            raise POProcessingTranslationError(msg)

    repository = InMemorySiteRegistryRepository()
    site_service = _build_domain_service(repository)
    site = site_service.create_site(_build_registration(local_path="/workspace/marketing-site"))
    workflow = SiteRegistryPresentationWorkflowService(
        service=site_service,
        project_sync_service=SyncStub(),
        po_processing_service=cast(POProcessingService, _ExplodingPOService()),
    )

    with pytest.raises(ControlledServiceError, match=r"PO workflow exploded\."):
        workflow.start_po_processing(site.id)


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


def test_workflow_service_wraps_local_to_remote_lookup_errors() -> None:
    workflow = SiteRegistryPresentationWorkflowService(
        service=SiteRegistryService(repository=InMemorySiteRegistryRepository()),
        project_sync_service=SyncStub(),
    )

    with pytest.raises(ControlledServiceError, match=r"Unknown site id: missing-site"):
        workflow.start_sync_to_remote("missing-site")


def test_build_sync_status_covers_empty_upload_and_download_summaries() -> None:
    upload_status = _build_sync_status(
        SyncResult(
            direction=SyncDirection.LOCAL_TO_REMOTE,
            success=True,
            project_id="site-1",
            connection_type="sftp",
            local_path="/workspace/site-1",
            summary=SyncSummary(
                files_discovered=0,
                files_downloaded=0,
                directories_created=0,
                bytes_downloaded=0,
                files_uploaded=0,
                bytes_uploaded=0,
            ),
            error=None,
        )
    )
    download_status = _build_sync_status(
        SyncResult(
            direction=SyncDirection.REMOTE_TO_LOCAL,
            success=True,
            project_id="site-1",
            connection_type="sftp",
            local_path="/workspace/site-1",
            summary=SyncSummary(
                files_discovered=1,
                files_downloaded=1,
                directories_created=0,
                bytes_downloaded=10,
            ),
            error=None,
        )
    )

    assert upload_status.summary == "Local workspace is empty. No files were uploaded."
    assert download_status.summary == "Downloaded 1 files into /workspace/site-1."


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


def test_build_project_detail_without_remote_connection_is_explicit() -> None:
    detail = _build_project_detail(
        RegisteredSite(
            project=SiteProject(
                id="site-1",
                name="Local Only",
                framework_type="django",
                local_path="/workspace/local-only",
                default_locale="en_US",
                is_active=True,
            ),
            remote_connection=None,
        )
    )

    assert detail.default_locale == "en_US"
    assert detail.configuration_summary == (
        "Locale: en_US | Compile MO: enabled | Remote connection: None"
    )
    assert detail.metadata_summary == "Framework: Django | Remote connection: none configured"


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


def _build_framework_sync_scope_service() -> FrameworkSyncScopeService:
    return FrameworkSyncScopeService(registry=FrameworkAdapterRegistry.discover_installed())


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
        use_adapter_sync_filters=False,
    )


def _write_po_file(path: Path, entries: list[tuple[str, str]]) -> None:
    po_file = polib.POFile()
    po_file.metadata = {"Language": path.stem.split("-")[-1]}
    for msgid, msgstr in entries:
        po_file.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    po_file.save(str(path))
