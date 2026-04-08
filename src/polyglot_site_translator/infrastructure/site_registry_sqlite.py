"""SQLite-backed site registry repository."""

from __future__ import annotations

import sqlite3

from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryConfigurationError,
    SiteRegistryConflictError,
    SiteRegistryNotFoundError,
    SiteRegistryPersistenceError,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.infrastructure.database_location import (
    SQLiteDatabaseLocation,
    resolve_sqlite_database_location,
)
from polyglot_site_translator.infrastructure.settings import TomlSettingsService
from polyglot_site_translator.infrastructure.site_secrets import LocalKeySiteSecretCipher
from polyglot_site_translator.presentation.errors import ControlledServiceError


class SqliteSiteRegistryRepository:
    """Persist site registry records in SQLite."""

    def __init__(
        self,
        *,
        location: SQLiteDatabaseLocation,
        secret_cipher: LocalKeySiteSecretCipher,
    ) -> None:
        self._location = location
        self._secret_cipher = secret_cipher
        self._ensure_schema()

    def create_site(self, site: RegisteredSite) -> RegisteredSite:
        """Insert a new site registry record."""
        encrypted_password = self._secret_cipher.encrypt(site.ftp_password)
        statement = """
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
        """
        try:
            with self._connect() as connection:
                connection.execute(
                    statement,
                    (
                        site.id,
                        site.name,
                        site.framework_type,
                        site.local_path,
                        site.default_locale,
                        site.ftp_host,
                        site.ftp_port,
                        site.ftp_username,
                        encrypted_password,
                        site.ftp_remote_path,
                        int(site.is_active),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise _map_integrity_error(site.name, site.local_path) from error
        except sqlite3.Error as error:
            msg = f"SQLite site registry write failed at {self._location.database_path}."
            raise SiteRegistryPersistenceError(msg) from error
        return site

    def list_sites(self) -> list[RegisteredSite]:
        """Return persisted site registry records ordered by name."""
        statement = "SELECT * FROM site_registry ORDER BY name COLLATE NOCASE"
        try:
            with self._connect() as connection:
                rows = connection.execute(statement).fetchall()
        except sqlite3.Error as error:
            msg = f"SQLite site registry read failed at {self._location.database_path}."
            raise SiteRegistryPersistenceError(msg) from error
        return [_map_row_to_site(row, self._secret_cipher) for row in rows]

    def get_site(self, site_id: str) -> RegisteredSite:
        """Return a single site registry record."""
        statement = "SELECT * FROM site_registry WHERE id = ?"
        try:
            with self._connect() as connection:
                row = connection.execute(statement, (site_id,)).fetchone()
        except sqlite3.Error as error:
            msg = f"SQLite site registry read failed at {self._location.database_path}."
            raise SiteRegistryPersistenceError(msg) from error
        if row is None:
            msg = f"Unknown site id: {site_id}"
            raise SiteRegistryNotFoundError(msg)
        return _map_row_to_site(row, self._secret_cipher)

    def update_site(self, site: RegisteredSite) -> RegisteredSite:
        """Persist changes for an existing site registry record."""
        encrypted_password = self._secret_cipher.encrypt(site.ftp_password)
        statement = """
            UPDATE site_registry
            SET
                name = ?,
                framework_type = ?,
                local_path = ?,
                default_locale = ?,
                ftp_host = ?,
                ftp_port = ?,
                ftp_username = ?,
                ftp_password_encrypted = ?,
                ftp_remote_path = ?,
                is_active = ?
            WHERE id = ?
        """
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    statement,
                    (
                        site.name,
                        site.framework_type,
                        site.local_path,
                        site.default_locale,
                        site.ftp_host,
                        site.ftp_port,
                        site.ftp_username,
                        encrypted_password,
                        site.ftp_remote_path,
                        int(site.is_active),
                        site.id,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise _map_integrity_error(site.name, site.local_path) from error
        except sqlite3.Error as error:
            msg = f"SQLite site registry write failed at {self._location.database_path}."
            raise SiteRegistryPersistenceError(msg) from error
        if cursor.rowcount == 0:
            msg = f"Unknown site id: {site.id}"
            raise SiteRegistryNotFoundError(msg)
        return site

    def delete_site(self, site_id: str) -> None:
        """Delete a site registry record."""
        statement = "DELETE FROM site_registry WHERE id = ?"
        try:
            with self._connect() as connection:
                cursor = connection.execute(statement, (site_id,))
        except sqlite3.Error as error:
            msg = f"SQLite site registry delete failed at {self._location.database_path}."
            raise SiteRegistryPersistenceError(msg) from error
        if cursor.rowcount == 0:
            msg = f"Unknown site id: {site_id}"
            raise SiteRegistryNotFoundError(msg)

    def fetch_encrypted_password(self, site_id: str) -> str:
        """Return the stored encrypted password for integration tests."""
        statement = "SELECT ftp_password_encrypted FROM site_registry WHERE id = ?"
        with self._connect() as connection:
            row = connection.execute(statement, (site_id,)).fetchone()
        if row is None:
            msg = f"Unknown site id: {site_id}"
            raise SiteRegistryNotFoundError(msg)
        return str(row["ftp_password_encrypted"])

    def _ensure_schema(self) -> None:
        try:
            self._location.directory.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS site_registry (
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
        except sqlite3.Error as error:
            msg = f"SQLite schema initialization failed at {self._location.database_path}."
            raise SiteRegistryPersistenceError(msg) from error
        except OSError as error:
            msg = f"SQLite directory could not be prepared at {self._location.directory}."
            raise SiteRegistryPersistenceError(msg) from error

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._location.database_path)
        connection.row_factory = sqlite3.Row
        return connection


def _map_row_to_site(
    row: sqlite3.Row,
    secret_cipher: LocalKeySiteSecretCipher,
) -> RegisteredSite:
    return RegisteredSite(
        id=str(row["id"]),
        name=str(row["name"]),
        framework_type=str(row["framework_type"]),
        local_path=str(row["local_path"]),
        default_locale=str(row["default_locale"]),
        ftp_host=str(row["ftp_host"]),
        ftp_port=int(row["ftp_port"]),
        ftp_username=str(row["ftp_username"]),
        ftp_password=secret_cipher.decrypt(str(row["ftp_password_encrypted"])),
        ftp_remote_path=str(row["ftp_remote_path"]),
        is_active=bool(row["is_active"]),
    )


def _map_integrity_error(site_name: str, local_path: str) -> SiteRegistryConflictError:
    msg = f"A site with the name '{site_name}' already exists."
    if local_path:
        return SiteRegistryConflictError(msg)
    return SiteRegistryConflictError(msg)


class ConfiguredSqliteSiteRegistryRepository:
    """Resolve the SQLite location from app settings before each repository operation."""

    def __init__(self, settings_service: TomlSettingsService) -> None:
        self._settings_service = settings_service

    def create_site(self, site: RegisteredSite) -> RegisteredSite:
        return self._build_repository().create_site(site)

    def list_sites(self) -> list[RegisteredSite]:
        return self._build_repository().list_sites()

    def get_site(self, site_id: str) -> RegisteredSite:
        return self._build_repository().get_site(site_id)

    def update_site(self, site: RegisteredSite) -> RegisteredSite:
        return self._build_repository().update_site(site)

    def delete_site(self, site_id: str) -> None:
        self._build_repository().delete_site(site_id)

    def _build_repository(self) -> SqliteSiteRegistryRepository:
        try:
            settings_state = self._settings_service.load_settings()
            location = resolve_sqlite_database_location(settings_state.app_settings)
        except ControlledServiceError as error:
            raise SiteRegistryConfigurationError(str(error)) from error
        return SqliteSiteRegistryRepository(
            location=location,
            secret_cipher=LocalKeySiteSecretCipher(
                self._settings_service.settings_path.parent / "site_registry.key"
            ),
        )
