"""Test configuration shared across the suite."""

# ruff: noqa: E402

from __future__ import annotations

from pathlib import Path
import sys

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from polyglot_site_translator.domain.site_registry.models import RegisteredSite
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
                id="wp-site",
                name="Marketing Site",
                framework_type="wordpress",
                local_path="/workspace/marketing-site",
                default_locale="en_US",
                ftp_host="ftp.example.com",
                ftp_port=21,
                ftp_username="deploy",
                ftp_password="super-secret",
                ftp_remote_path="/public_html",
                is_active=True,
            )
        )
        repository.create_site(
            RegisteredSite(
                id="dj-admin",
                name="Backoffice",
                framework_type="django",
                local_path="/workspace/backoffice",
                default_locale="en_US",
                ftp_host="ftp-backoffice.example.com",
                ftp_port=21,
                ftp_username="deploy",
                ftp_password="super-secret",
                ftp_remote_path="/srv/backoffice",
                is_active=False,
            )
        )
