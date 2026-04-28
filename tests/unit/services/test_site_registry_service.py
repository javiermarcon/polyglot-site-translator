"""Unit tests for site registry application services."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pytest

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.adapters.wordpress import WordPressFrameworkAdapter
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteRegistrationInput,
)
from polyglot_site_translator.domain.sync.models import RemoteSyncFile, SyncProgressEvent
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.services.framework_detection import (
    FrameworkDetectionService,
)
from polyglot_site_translator.services.remote_connections import RemoteConnectionService
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


_DEFAULT_REMOTE = object()


@dataclass(frozen=True)
class StubSFTPProvider:
    """Remote provider stub for site registry service tests."""

    descriptor: RemoteConnectionTypeDescriptor = field(
        default_factory=lambda: RemoteConnectionTypeDescriptor(
            connection_type="sftp",
            display_name="SFTP",
            default_port=22,
        )
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


def test_site_registry_service_creates_and_lists_sites() -> None:
    service = _build_service()

    created_site = service.create_site(_build_registration())

    assert created_site.name == "Marketing Site"
    assert created_site.remote_connection is not None
    assert service.list_sites() == [created_site]


def test_site_registry_service_allows_projects_without_remote_connections() -> None:
    service = _build_service()

    created_site = service.create_site(_build_registration(remote_connection=None))

    assert created_site.remote_connection is None


def test_site_registry_service_normalizes_comma_separated_default_locales() -> None:
    service = _build_service()

    created_site = service.create_site(_build_registration(default_locale="es_ES, es_AR"))

    assert created_site.default_locale == "es_ES,es_AR"


def test_site_registry_service_preserves_compile_mo_preference() -> None:
    service = _build_service()

    created_site = service.create_site(_build_registration(compile_mo=False))

    assert created_site.project.compile_mo is False


def test_site_registry_service_lists_and_gets_sites_from_the_repository() -> None:
    service = _build_service()
    created_site = service.create_site(_build_registration())

    assert service.list_sites() == [created_site]
    assert service.get_site(created_site.id) == created_site


def test_site_registry_service_updates_a_site() -> None:
    service = _build_service()
    created_site = service.create_site(_build_registration())

    updated_site = service.update_site(
        site_id=created_site.id,
        registration=_build_registration(
            local_path="/workspace/marketing-site-v2",
            remote_connection=RemoteConnectionConfigInput(
                connection_type="sftp",
                host="sftp.example.com",
                port=22,
                username="deploy",
                password="super-secret",
                remote_path="/srv/app",
            ),
            is_active=False,
        ),
    )

    assert updated_site.local_path == "/workspace/marketing-site-v2"
    assert updated_site.is_active is False
    assert updated_site.remote_connection is not None
    assert updated_site.remote_connection.connection_type == "sftp"


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
        remote_connection_service=_build_remote_connection_service(),
    )

    created_site = service.create_site(
        _build_registration(
            framework_type="customapp",
            local_path=str(project_path),
        )
    )

    assert created_site.framework_type == "wordpress"


def test_site_registry_service_delete_and_detection_fallback_behave_as_expected() -> None:
    repository = InMemorySiteRegistryRepository(sites={})
    service = SiteRegistryService(repository=repository)
    created_site = service.create_site(_build_registration(remote_connection=None))

    detection = service.detect_framework("/workspace/marketing-site")
    service.delete_site(created_site.id)

    assert detection.matched is False
    assert repository.sites == {}


def test_site_registry_service_lists_unknown_framework_when_detection_is_missing() -> None:
    service = SiteRegistryService(repository=InMemorySiteRegistryRepository(sites={}))

    frameworks = service.list_supported_frameworks()

    assert [framework.framework_type for framework in frameworks] == ["unknown"]


def test_site_registry_service_handles_missing_remote_connection_service_branches() -> None:
    service = SiteRegistryService(repository=InMemorySiteRegistryRepository(sites={}))
    created_site = service.create_site(_build_registration())

    assert created_site.remote_connection is None
    assert service.list_supported_connection_types() == []
    assert service.can_test_remote_connection(_build_registration(remote_connection=None)) is False
    with pytest.raises(
        ValueError,
        match=r"Remote connection testing is not configured\.",
    ):
        service.test_remote_connection(_build_registration())


def test_site_registry_service_lists_supported_connection_types() -> None:
    service = _build_service()

    connection_types = service.list_supported_connection_types()

    assert [descriptor.connection_type for descriptor in connection_types] == [
        "none",
        "sftp",
    ]


def test_site_registry_service_lists_supported_frameworks_when_detection_is_configured() -> None:
    service = SiteRegistryService(
        repository=InMemorySiteRegistryRepository(sites={}),
        framework_detection_service=FrameworkDetectionService(
            registry=FrameworkAdapterRegistry.discover_installed()
        ),
        remote_connection_service=_build_remote_connection_service(),
    )

    assert [framework.framework_type for framework in service.list_supported_frameworks()] == [
        "unknown",
        "django",
        "flask",
        "wordpress",
    ]


def test_site_registry_service_can_test_and_runs_a_remote_connection() -> None:
    service = _build_service()
    registration = _build_registration()

    assert service.can_test_remote_connection(registration) is True
    result = service.test_remote_connection(registration)

    assert result.success is True
    assert result.message == "Connected successfully."


def test_site_registry_service_keeps_the_operator_framework_when_detection_does_not_match(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "generic-site"
    project_path.mkdir()
    (project_path / "README.txt").write_text("generic project\n", encoding="utf-8")
    service = SiteRegistryService(
        repository=InMemorySiteRegistryRepository(sites={}),
        framework_detection_service=FrameworkDetectionService(
            registry=FrameworkAdapterRegistry.default_registry(
                adapters=[WordPressFrameworkAdapter()]
            )
        ),
        remote_connection_service=_build_remote_connection_service(),
    )

    created_site = service.create_site(
        _build_registration(framework_type="customapp", local_path=str(project_path))
    )

    assert created_site.framework_type == "customapp"


@pytest.mark.parametrize(
    ("name", "local_path", "default_locale", "remote_connection", "expected_message"),
    [
        ("", "/workspace/marketing-site", "en_US", None, r"Site name must not be empty\."),
        ("Marketing Site", "", "en_US", None, r"Local path must not be empty\."),
        (
            "Marketing Site",
            "/workspace/marketing-site",
            "",
            None,
            r"Default locale must not be empty\.",
        ),
        (
            "Marketing Site",
            "/workspace/marketing-site",
            "asad@",
            None,
            (
                r"Default locale must be a valid locale or a comma-separated list of "
                r"valid locales\. Invalid values: asad@\."
            ),
        ),
        (
            "Marketing Site",
            "/workspace/marketing-site",
            "es_ES,,es_AR",
            None,
            r"Default locale must be a valid locale or a comma-separated list of valid locales\.",
        ),
        (
            "Marketing Site",
            "/workspace/marketing-site",
            "en_US",
            RemoteConnectionConfigInput(
                connection_type="sftp",
                host="example.com",
                port=0,
                username="deploy",
                password="super-secret",
                remote_path="/srv/app",
            ),
            r"Remote port must be a positive integer\.",
        ),
    ],
)
def test_site_registry_service_rejects_invalid_input(
    name: str,
    local_path: str,
    default_locale: str,
    remote_connection: RemoteConnectionConfigInput | None,
    expected_message: str,
) -> None:
    service = _build_service()

    with pytest.raises(ValueError, match=expected_message):
        service.create_site(
            _build_registration(
                name=name,
                local_path=local_path,
                default_locale=default_locale,
                remote_connection=remote_connection,
            )
        )


def _build_service() -> SiteRegistryService:
    return SiteRegistryService(
        repository=InMemorySiteRegistryRepository(sites={}),
        remote_connection_service=_build_remote_connection_service(),
    )


def _build_remote_connection_service() -> RemoteConnectionService:
    return RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(providers=[StubSFTPProvider()])
    )


def _build_registration(  # noqa: PLR0913
    *,
    name: str = "Marketing Site",
    framework_type: str = "wordpress",
    local_path: str = "/workspace/marketing-site",
    default_locale: str = "en_US",
    remote_connection: RemoteConnectionConfigInput | object | None = _DEFAULT_REMOTE,
    is_active: bool = True,
    compile_mo: bool = True,
) -> SiteRegistrationInput:
    resolved_remote_connection = remote_connection
    if resolved_remote_connection is _DEFAULT_REMOTE:
        resolved_remote_connection = RemoteConnectionConfigInput(
            connection_type="sftp",
            host="example.com",
            port=22,
            username="deploy",
            password="super-secret",
            remote_path="/srv/app",
        )
    return SiteRegistrationInput(
        name=name,
        framework_type=framework_type,
        local_path=local_path,
        default_locale=default_locale,
        remote_connection=cast(RemoteConnectionConfigInput | None, resolved_remote_connection),
        is_active=is_active,
        compile_mo=compile_mo,
    )
