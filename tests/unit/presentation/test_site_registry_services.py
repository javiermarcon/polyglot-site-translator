"""Unit tests for presentation adapters around the real site registry service."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryConflictError,
    SiteRegistryNotFoundError,
    SiteRegistryPersistenceError,
)
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteRegistrationInput,
)
from polyglot_site_translator.infrastructure.settings import TomlSettingsService
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.site_registry_services import (
    SiteRegistryPresentationCatalogService,
    SiteRegistryPresentationManagementService,
)
from polyglot_site_translator.presentation.view_models import (
    SettingsStateViewModel,
    SiteEditorViewModel,
    build_default_app_settings,
    build_settings_state,
)
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


def test_catalog_service_maps_project_summaries_and_detail() -> None:
    repository = InMemorySiteRegistryRepository()
    service = SiteRegistryService(repository=repository)
    created = service.create_site(_build_registration(framework_type="custom_cms"))
    catalog = SiteRegistryPresentationCatalogService(service)

    projects = catalog.list_projects()
    detail = catalog.get_project_detail(created.id)

    assert projects[0].status == "Active"
    assert projects[0].framework == "Custom_Cms"
    assert "FTP user: deploy" in detail.metadata_summary


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
    domain_service = SiteRegistryService(repository=repository)
    created = domain_service.create_site(_build_registration())
    management = SiteRegistryPresentationManagementService(
        service=domain_service,
        settings_service=settings_service,
    )

    create_state = management.build_create_project_editor()
    edit_state = management.build_edit_project_editor(created.id)

    assert create_state.mode == "create"
    assert create_state.editor.local_path.endswith("/site")
    assert edit_state.mode == "edit"
    assert edit_state.editor.site_id == created.id


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
        service=SiteRegistryService(repository=InMemorySiteRegistryRepository()),
        settings_service=InvalidSettingsService(tmp_path / "settings.toml"),
    )

    with pytest.raises(ControlledServiceError, match=r"Database filename must not be empty\."):
        management.build_create_project_editor()


def test_management_service_wraps_invalid_editor_payloads_and_missing_sites(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    repository = InMemorySiteRegistryRepository()
    management = SiteRegistryPresentationManagementService(
        service=SiteRegistryService(repository=repository),
        settings_service=settings_service,
    )

    invalid_editor = replace(_build_editor(), ftp_port="not-a-number")

    with pytest.raises(ControlledServiceError, match=r"invalid literal for int"):
        management.create_project(invalid_editor)

    with pytest.raises(ControlledServiceError, match=r"Unknown site id: missing-site"):
        management.update_project("missing-site", _build_editor())


def test_management_service_wraps_domain_conflicts(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.reset_settings()
    repository = InMemorySiteRegistryRepository()
    SiteRegistryService(repository=repository).create_site(_build_registration())

    class ConflictRepository(InMemorySiteRegistryRepository):
        def create_site(self, site: RegisteredSite) -> RegisteredSite:
            msg = "A site with the name 'Marketing Site' already exists."
            raise SiteRegistryConflictError(msg)

    conflict_management = SiteRegistryPresentationManagementService(
        service=SiteRegistryService(repository=ConflictRepository()),
        settings_service=settings_service,
    )

    with pytest.raises(
        ControlledServiceError,
        match=r"A site with the name 'Marketing Site' already exists\.",
    ):
        conflict_management.create_project(_build_editor())


def _build_registration(*, framework_type: str = "wordpress") -> SiteRegistrationInput:
    return SiteRegistrationInput(
        name="Marketing Site",
        framework_type=framework_type,
        local_path="/workspace/marketing-site",
        default_locale="en_US",
        ftp_host="ftp.example.com",
        ftp_port=21,
        ftp_username="deploy",
        ftp_password="super-secret",
        ftp_remote_path="/public_html",
        is_active=True,
    )


def _build_editor() -> SiteEditorViewModel:
    return SiteEditorViewModel(
        site_id=None,
        name="Marketing Site",
        framework_type="wordpress",
        local_path="/workspace/marketing-site",
        default_locale="en_US",
        ftp_host="ftp.example.com",
        ftp_port="21",
        ftp_username="deploy",
        ftp_password="super-secret",
        ftp_remote_path="/public_html",
        is_active=True,
    )
