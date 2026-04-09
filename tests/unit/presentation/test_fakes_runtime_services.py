"""Additional tests for runtime wiring and frontend test doubles."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel
from polyglot_site_translator.services.remote_connections import RemoteConnectionService
from tests.support.frontend_doubles import (
    FailingSiteRegistryCatalogService,
    build_seeded_services,
)


def _build_editor(*, connection_type: str, remote_host: str) -> SiteEditorViewModel:
    return SiteEditorViewModel(
        site_id=None,
        name="Site",
        framework_type="wordpress",
        local_path="/workspace/site",
        default_locale="en_US",
        connection_type=connection_type,
        remote_host=remote_host,
        remote_port="21",
        remote_username="deploy",
        remote_password="secret",
        remote_path="/remote/path",
        is_active=True,
    )


def test_seeded_registry_fake_reports_success_for_configured_remote_connection() -> None:
    services = build_seeded_services()

    result = services.registry.test_remote_connection(
        _build_editor(connection_type="ftp", remote_host="ftp.example.com")
    )

    assert result.success is True
    assert result.error_code is None


def test_seeded_registry_fake_reports_invalid_configuration_without_remote_connection() -> None:
    services = build_seeded_services()

    result = services.registry.test_remote_connection(
        _build_editor(connection_type="none", remote_host="")
    )

    assert result.success is False
    assert result.error_code == "invalid_remote_config"
    assert result.message == "Remote connection test requires a configured remote connection."


def test_runtime_services_allow_catalog_replacement_with_failure_double(tmp_path: Path) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")

    services = replace(
        build_default_frontend_services(settings_service=settings_service),
        catalog=FailingSiteRegistryCatalogService(),
    )

    with pytest.raises(ControlledServiceError, match="temporarily unavailable"):
        services.catalog.list_projects()


def test_build_default_frontend_services_accepts_injected_remote_connection_service(
    tmp_path: Path,
) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    injected_remote_service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.discover_installed()
    )

    services = build_default_frontend_services(
        settings_service=settings_service,
        remote_connection_service=injected_remote_service,
    )

    assert services.catalog.list_projects() == []


def test_failing_site_registry_catalog_service_raises_controlled_errors() -> None:
    service = FailingSiteRegistryCatalogService()

    with pytest.raises(ControlledServiceError, match="temporarily unavailable\\."):
        service.list_projects()

    with pytest.raises(ControlledServiceError, match="temporarily unavailable for missing-site\\."):
        service.get_project_detail("missing-site")
