"""Test configuration shared across the suite."""

# ruff: noqa: E402

from __future__ import annotations

from pathlib import Path
import sys

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from polyglot_site_translator.domain.remote_connections.models import RemoteConnectionConfig
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.infrastructure.site_registry_sqlite import (
    ConfiguredSqliteSiteRegistryRepository,
)


@pytest.fixture(autouse=True)
def isolate_user_config_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Force tests to use an isolated user config directory."""
    monkeypatch.setenv("POLYGLOT_SITE_TRANSLATOR_CONFIG_DIR", str(tmp_path))
    settings_service = build_default_settings_service(config_dir=tmp_path)
    settings_service.reset_settings()
    repository = ConfiguredSqliteSiteRegistryRepository(settings_service)
    if not repository.list_sites():
        repository.create_site(
            RegisteredSite(
                project=SiteProject(
                    id="wp-site",
                    name="Marketing Site",
                    framework_type="wordpress",
                    local_path="/workspace/marketing-site",
                    default_locale="en_US",
                    is_active=True,
                ),
                remote_connection=RemoteConnectionConfig(
                    id="remote-wp-site",
                    site_project_id="wp-site",
                    connection_type="ftp",
                    host="ftp.example.com",
                    port=21,
                    username="deploy",
                    password="super-secret",
                    remote_path="/public_html",
                ),
            )
        )
        repository.create_site(
            RegisteredSite(
                project=SiteProject(
                    id="dj-admin",
                    name="Backoffice",
                    framework_type="django",
                    local_path="/workspace/backoffice",
                    default_locale="en_US",
                    is_active=False,
                ),
                remote_connection=RemoteConnectionConfig(
                    id="remote-dj-admin",
                    site_project_id="dj-admin",
                    connection_type="ftp",
                    host="ftp-backoffice.example.com",
                    port=21,
                    username="deploy",
                    password="super-secret",
                    remote_path="/srv/backoffice",
                ),
            )
        )
