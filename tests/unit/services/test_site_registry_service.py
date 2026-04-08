"""Unit tests for site registry application services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.adapters.wordpress import WordPressFrameworkAdapter
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteRegistrationInput,
)
from polyglot_site_translator.services.framework_detection import (
    FrameworkDetectionService,
)
from polyglot_site_translator.services.site_registry import SiteRegistryService


@dataclass
class InMemorySiteRegistryRepository:
    """Minimal in-memory repository for site registry service tests."""

    sites: dict[str, RegisteredSite]

    def create_site(self, site: RegisteredSite) -> RegisteredSite:
        if site.name in {saved.name for saved in self.sites.values()}:
            msg = f"A site with the name '{site.name}' already exists."
            raise ValueError(msg)
        self.sites[site.id] = site
        return site

    def list_sites(self) -> list[RegisteredSite]:
        return list(self.sites.values())

    def get_site(self, site_id: str) -> RegisteredSite:
        return self.sites[site_id]

    def update_site(self, site: RegisteredSite) -> RegisteredSite:
        self.sites[site.id] = site
        return site

    def delete_site(self, site_id: str) -> None:
        del self.sites[site_id]


def test_site_registry_service_creates_and_lists_sites() -> None:
    service = SiteRegistryService(repository=InMemorySiteRegistryRepository(sites={}))

    created_site = service.create_site(
        SiteRegistrationInput(
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

    assert created_site.name == "Marketing Site"
    assert service.list_sites() == [created_site]


def test_site_registry_service_updates_a_site() -> None:
    service = SiteRegistryService(repository=InMemorySiteRegistryRepository(sites={}))
    created_site = service.create_site(
        SiteRegistrationInput(
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

    updated_site = service.update_site(
        site_id=created_site.id,
        registration=SiteRegistrationInput(
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site-v2",
            default_locale="en_US",
            ftp_host="ftp-v2.example.com",
            ftp_port=21,
            ftp_username="deploy",
            ftp_password="super-secret",
            ftp_remote_path="/public_html",
            is_active=False,
        ),
    )

    assert updated_site.local_path == "/workspace/marketing-site-v2"
    assert updated_site.is_active is False


def test_site_registry_service_detects_and_persists_supported_frameworks(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "wordpress-site"
    project_path.mkdir()
    (project_path / "wp-config.php").write_text("<?php\n", encoding="utf-8")
    (project_path / "wp-content").mkdir()
    (project_path / "wp-includes").mkdir()
    service = SiteRegistryService(
        repository=InMemorySiteRegistryRepository(sites={}),
        framework_detection_service=FrameworkDetectionService(
            registry=FrameworkAdapterRegistry.default_registry(
                adapters=[WordPressFrameworkAdapter()]
            )
        ),
    )

    created_site = service.create_site(
        SiteRegistrationInput(
            name="Marketing Site",
            framework_type="customapp",
            local_path=str(project_path),
            default_locale="en_US",
            ftp_host="ftp.example.com",
            ftp_port=21,
            ftp_username="deploy",
            ftp_password="super-secret",
            ftp_remote_path="/public_html",
            is_active=True,
        )
    )

    assert created_site.framework_type == "wordpress"


def test_site_registry_service_delete_and_detection_fallback_behave_as_expected() -> None:
    repository = InMemorySiteRegistryRepository(sites={})
    service = SiteRegistryService(repository=repository)
    created_site = service.create_site(
        SiteRegistrationInput(
            name="Marketing Site",
            framework_type="customapp",
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

    detection = service.detect_framework("/workspace/marketing-site")
    service.delete_site(created_site.id)

    assert detection.matched is False
    assert repository.sites == {}


def test_site_registry_service_lists_unknown_framework_when_detection_is_missing() -> None:
    service = SiteRegistryService(repository=InMemorySiteRegistryRepository(sites={}))

    frameworks = service.list_supported_frameworks()

    assert [framework.framework_type for framework in frameworks] == ["unknown"]


@pytest.mark.parametrize(
    ("name", "local_path", "default_locale", "ftp_port", "expected_message"),
    [
        ("", "/workspace/marketing-site", "en_US", 21, r"Site name must not be empty\."),
        ("Marketing Site", "", "en_US", 21, r"Local path must not be empty\."),
        (
            "Marketing Site",
            "/workspace/marketing-site",
            "",
            21,
            r"Default locale must not be empty\.",
        ),
        (
            "Marketing Site",
            "/workspace/marketing-site",
            "en_US",
            0,
            r"FTP port must be a positive integer\.",
        ),
    ],
)
def test_site_registry_service_rejects_invalid_input(
    name: str,
    local_path: str,
    default_locale: str,
    ftp_port: int,
    expected_message: str,
) -> None:
    service = SiteRegistryService(repository=InMemorySiteRegistryRepository(sites={}))

    with pytest.raises(ValueError, match=expected_message):
        service.create_site(
            SiteRegistrationInput(
                name=name,
                framework_type="wordpress",
                local_path=local_path,
                default_locale=default_locale,
                ftp_host="ftp.example.com",
                ftp_port=ftp_port,
                ftp_username="deploy",
                ftp_password="super-secret",
                ftp_remote_path="/public_html",
                is_active=True,
            )
        )
