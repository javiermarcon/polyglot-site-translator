"""Unit tests for the SQLite-backed site registry repository."""

from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from polyglot_site_translator.domain.remote_connections.models import RemoteConnectionConfig
from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryConfigurationError,
    SiteRegistryNotFoundError,
    SiteRegistryPersistenceError,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.infrastructure.database_location import SQLiteDatabaseLocation
from polyglot_site_translator.infrastructure.settings import TomlSettingsService
from polyglot_site_translator.infrastructure.site_registry_sqlite import (
    ConfiguredSqliteSiteRegistryRepository,
    SqliteSiteRegistryRepository,
)
from polyglot_site_translator.infrastructure.site_secrets import LocalKeySiteSecretCipher
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.view_models import SettingsStateViewModel


def test_sqlite_repository_creates_schema_and_roundtrips_a_site(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    site = _build_site()

    repository.create_site(site)
    loaded_site = repository.get_site(site.id)

    assert loaded_site == site
    assert repository.list_sites() == [site]


def test_sqlite_repository_updates_a_site(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    site = _build_site()
    repository.create_site(site)
    updated_site = RegisteredSite(
        project=SiteProject(
            **{
                **site.project.__dict__,
                "local_path": "/workspace/marketing-site-v2",
            }
        ),
        remote_connection=RemoteConnectionConfig(
            **{
                **site.remote_connection.__dict__,
                "host": "sftp.example.com",
                "connection_type": "sftp",
                "port": 22,
                "remote_path": "/srv/app",
            }
        ),
    )

    repository.update_site(updated_site)

    assert repository.get_site(site.id) == updated_site


def test_sqlite_repository_returns_an_empty_list_when_no_sites_exist(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)

    assert repository.list_sites() == []


def test_sqlite_repository_rejects_duplicate_site_names(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    repository.create_site(_build_site())

    with pytest.raises(
        ValueError,
        match=r"A site with the name 'Marketing Site' already exists\.",
    ):
        repository.create_site(
            RegisteredSite(
                project=SiteProject(
                    id="site-2",
                    name="Marketing Site",
                    framework_type="wordpress",
                    local_path="/workspace/another",
                    default_locale="en_US",
                    is_active=True,
                ),
                remote_connection=None,
            )
        )


def test_sqlite_repository_encrypts_the_stored_remote_password(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    site = _build_site()

    repository.create_site(site)
    stored_password = repository.fetch_encrypted_password(site.id)

    assert site.remote_connection is not None
    assert stored_password != site.remote_connection.password
    assert site.remote_connection.password not in stored_password


def test_sqlite_repository_supports_projects_without_remote_connections(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    site = RegisteredSite(
        project=SiteProject(
            id="site-no-remote",
            name="Local Only",
            framework_type="flask",
            local_path="/workspace/local-only",
            default_locale="en_US",
            is_active=True,
        ),
        remote_connection=None,
    )

    repository.create_site(site)

    assert repository.get_site(site.id).remote_connection is None


def test_sqlite_repository_migrates_legacy_ftp_columns_without_losing_ciphertext(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    cipher = LocalKeySiteSecretCipher(tmp_path / "site_registry.key")
    encrypted_password = cipher.encrypt("super-secret")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE site_registry (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                framework_type TEXT NOT NULL,
                local_path TEXT NOT NULL UNIQUE,
                default_locale TEXT NOT NULL,
                ftp_host TEXT NOT NULL,
                ftp_port INTEGER NOT NULL,
                ftp_username TEXT NOT NULL,
                ftp_password_encrypted TEXT NOT NULL,
                ftp_remote_path TEXT NOT NULL,
                is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
            )
            """
        )
        connection.execute(
            """
            INSERT INTO site_registry (
                id,
                name,
                framework_type,
                local_path,
                default_locale,
                ftp_host,
                ftp_port,
                ftp_username,
                ftp_password_encrypted,
                ftp_remote_path,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "site-legacy",
                "Legacy Site",
                "wordpress",
                "/workspace/legacy-site",
                "en_US",
                "ftp.example.com",
                21,
                "deploy",
                encrypted_password,
                "/public_html",
                1,
            ),
        )
    repository = SqliteSiteRegistryRepository(
        location=SQLiteDatabaseLocation(
            directory=tmp_path,
            filename="legacy.sqlite3",
            database_path=database_path,
        ),
        secret_cipher=cipher,
    )

    loaded_site = repository.get_site("site-legacy")
    stored_ciphertext = repository.fetch_encrypted_password("site-legacy")

    assert loaded_site.remote_connection is not None
    assert loaded_site.remote_connection.connection_type == "ftp"
    assert loaded_site.remote_connection.password == "super-secret"
    assert stored_ciphertext == encrypted_password


def test_sqlite_repository_raises_for_missing_rows_and_delete_roundtrip(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    site = _build_site()
    repository.create_site(site)
    repository.delete_site(site.id)

    assert repository.list_sites() == []

    with pytest.raises(SiteRegistryNotFoundError, match=r"Unknown site id: site-1"):
        repository.get_site(site.id)

    with pytest.raises(SiteRegistryNotFoundError, match=r"Unknown site id: site-1"):
        repository.fetch_encrypted_password(site.id)

    with pytest.raises(SiteRegistryNotFoundError, match=r"Unknown site id: missing-site"):
        repository.delete_site("missing-site")

    with pytest.raises(SiteRegistryNotFoundError, match=r"Unknown site id: site-1"):
        repository.update_site(site)


def test_sqlite_repository_wraps_sqlite_errors_for_read_write_and_delete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = _build_repository(tmp_path)

    def fail_connect() -> sqlite3.Connection:
        msg = "boom"
        raise sqlite3.OperationalError(msg)

    monkeypatch.setattr(repository, "_connect", fail_connect)

    with pytest.raises(SiteRegistryPersistenceError, match=r"SQLite site registry write failed"):
        repository.create_site(_build_site())

    with pytest.raises(SiteRegistryPersistenceError, match=r"SQLite site registry read failed"):
        repository.list_sites()

    with pytest.raises(SiteRegistryPersistenceError, match=r"SQLite site registry read failed"):
        repository.get_site("site-1")

    with pytest.raises(SiteRegistryPersistenceError, match=r"SQLite site registry write failed"):
        repository.update_site(_build_site())

    with pytest.raises(SiteRegistryPersistenceError, match=r"SQLite site registry delete failed"):
        repository.delete_site("site-1")


def test_sqlite_repository_wraps_schema_preparation_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    location = SQLiteDatabaseLocation(
        directory=tmp_path / "nested",
        filename="registry.sqlite3",
        database_path=tmp_path / "nested" / "registry.sqlite3",
    )

    def fail_mkdir(*_args: object, **_kwargs: object) -> None:
        msg = "boom"
        raise OSError(msg)

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)

    with pytest.raises(
        SiteRegistryPersistenceError,
        match=r"SQLite directory could not be prepared at",
    ):
        SqliteSiteRegistryRepository(
            location=location,
            secret_cipher=LocalKeySiteSecretCipher(tmp_path / "site_registry.key"),
        )


def test_configured_sqlite_repository_resolves_settings_and_wraps_load_failures(
    tmp_path: Path,
) -> None:
    isolated_config_dir = tmp_path / "isolated-config"
    settings_service = TomlSettingsService(isolated_config_dir / "settings.toml")
    settings_service.reset_settings()
    repository = ConfiguredSqliteSiteRegistryRepository(settings_service)
    site = RegisteredSite(
        project=SiteProject(
            id="site-configured",
            name="Configured Site",
            framework_type="wordpress",
            local_path="/workspace/configured-site",
            default_locale="en_US",
            is_active=True,
        ),
        remote_connection=RemoteConnectionConfig(
            id="remote-site-configured",
            site_project_id="site-configured",
            connection_type="ftp",
            host="ftp.example.com",
            port=21,
            username="deploy",
            password="super-secret",
            remote_path="/public_html",
        ),
    )

    repository.create_site(site)
    assert repository.get_site(site.id) == site
    updated_site = RegisteredSite(
        project=SiteProject(**{**site.project.__dict__, "local_path": "/workspace/v2"}),
        remote_connection=site.remote_connection,
    )
    repository.update_site(updated_site)
    assert repository.list_sites()[0].local_path == "/workspace/v2"
    repository.delete_site(site.id)
    assert repository.list_sites() == []

    class FailingSettingsService(TomlSettingsService):
        def load_settings(self) -> SettingsStateViewModel:
            msg = "Settings unavailable."
            raise ControlledServiceError(msg)

    with pytest.raises(SiteRegistryConfigurationError, match=r"Settings unavailable\."):
        ConfiguredSqliteSiteRegistryRepository(
            FailingSettingsService(isolated_config_dir / "failing.toml")
        ).list_sites()


def _build_repository(tmp_path: Path) -> SqliteSiteRegistryRepository:
    location = SQLiteDatabaseLocation(
        directory=tmp_path,
        filename="registry.sqlite3",
        database_path=tmp_path / "registry.sqlite3",
    )
    return SqliteSiteRegistryRepository(
        location=location,
        secret_cipher=LocalKeySiteSecretCipher(tmp_path / "site_registry.key"),
    )


def _build_site() -> RegisteredSite:
    return RegisteredSite(
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
            password="super-secret",
            remote_path="/public_html",
        ),
    )
