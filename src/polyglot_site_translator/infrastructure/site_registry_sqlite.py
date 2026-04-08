"""SQLite-backed site registry repository."""

from __future__ import annotations

import sqlite3

from polyglot_site_translator.domain.remote_connections.models import (
    BuiltinRemoteConnectionType,
    RemoteConnectionConfig,
    RemoteConnectionFlags,
)
from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryConfigurationError,
    SiteRegistryConflictError,
    SiteRegistryNotFoundError,
    SiteRegistryPersistenceError,
)
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteProject,
)
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
        project_statement = """
            INSERT INTO site_registry (
                id,
                name,
                framework_type,
                local_path,
                default_locale,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        connection_statement = """
            INSERT INTO site_remote_connections (
                id,
                site_project_id,
                connection_type,
                host,
                port,
                username,
                password_encrypted,
                remote_path,
                passive_mode,
                verify_host
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._connect() as connection:
                connection.execute(project_statement, _project_params(site.project))
                if site.remote_connection is not None:
                    connection.execute(
                        connection_statement,
                        _connection_params(site.remote_connection, self._secret_cipher),
                    )
        except sqlite3.IntegrityError as error:
            raise _map_integrity_error(site.name) from error
        except sqlite3.Error as error:
            msg = f"SQLite site registry write failed at {self._location.database_path}."
            raise SiteRegistryPersistenceError(msg) from error
        return site

    def list_sites(self) -> list[RegisteredSite]:
        """Return persisted site registry records ordered by name."""
        statement = """
            SELECT
                project.id,
                project.name,
                project.framework_type,
                project.local_path,
                project.default_locale,
                project.is_active,
                remote.id AS remote_id,
                remote.connection_type,
                remote.host,
                remote.port,
                remote.username,
                remote.password_encrypted,
                remote.remote_path,
                remote.passive_mode,
                remote.verify_host
            FROM site_registry AS project
            LEFT JOIN site_remote_connections AS remote
                ON remote.site_project_id = project.id
            ORDER BY project.name COLLATE NOCASE
        """
        try:
            with self._connect() as connection:
                rows = connection.execute(statement).fetchall()
        except sqlite3.Error as error:
            msg = f"SQLite site registry read failed at {self._location.database_path}."
            raise SiteRegistryPersistenceError(msg) from error
        return [_map_row_to_site(row, self._secret_cipher) for row in rows]

    def get_site(self, site_id: str) -> RegisteredSite:
        """Return a single site registry record."""
        statement = """
            SELECT
                project.id,
                project.name,
                project.framework_type,
                project.local_path,
                project.default_locale,
                project.is_active,
                remote.id AS remote_id,
                remote.connection_type,
                remote.host,
                remote.port,
                remote.username,
                remote.password_encrypted,
                remote.remote_path,
                remote.passive_mode,
                remote.verify_host
            FROM site_registry AS project
            LEFT JOIN site_remote_connections AS remote
                ON remote.site_project_id = project.id
            WHERE project.id = ?
        """
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
        project_statement = """
            UPDATE site_registry
            SET
                name = ?,
                framework_type = ?,
                local_path = ?,
                default_locale = ?,
                is_active = ?
            WHERE id = ?
        """
        delete_connection_statement = (
            "DELETE FROM site_remote_connections WHERE site_project_id = ?"
        )
        insert_connection_statement = """
            INSERT INTO site_remote_connections (
                id,
                site_project_id,
                connection_type,
                host,
                port,
                username,
                password_encrypted,
                remote_path,
                passive_mode,
                verify_host
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._connect() as connection:
                cursor = connection.execute(project_statement, _project_update_params(site.project))
                if cursor.rowcount == 0:
                    msg = f"Unknown site id: {site.id}"
                    raise SiteRegistryNotFoundError(msg)
                connection.execute(delete_connection_statement, (site.id,))
                if site.remote_connection is not None:
                    connection.execute(
                        insert_connection_statement,
                        _connection_params(site.remote_connection, self._secret_cipher),
                    )
        except sqlite3.IntegrityError as error:
            raise _map_integrity_error(site.name) from error
        except sqlite3.Error as error:
            msg = f"SQLite site registry write failed at {self._location.database_path}."
            raise SiteRegistryPersistenceError(msg) from error
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
        statement = """
            SELECT password_encrypted
            FROM site_remote_connections
            WHERE site_project_id = ?
        """
        with self._connect() as connection:
            row = connection.execute(statement, (site_id,)).fetchone()
        if row is None:
            msg = f"Unknown site id: {site_id}"
            raise SiteRegistryNotFoundError(msg)
        return str(row["password_encrypted"])

    def _ensure_schema(self) -> None:
        try:
            self._location.directory.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                _ensure_project_table(connection)
                _ensure_remote_table(connection)
                _migrate_legacy_ftp_schema(connection)
        except sqlite3.Error as error:
            msg = f"SQLite schema initialization failed at {self._location.database_path}."
            raise SiteRegistryPersistenceError(msg) from error
        except OSError as error:
            msg = f"SQLite directory could not be prepared at {self._location.directory}."
            raise SiteRegistryPersistenceError(msg) from error

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._location.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _ensure_project_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS site_registry (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            framework_type TEXT NOT NULL,
            local_path TEXT NOT NULL UNIQUE,
            default_locale TEXT NOT NULL,
            is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
        )
        """
    )


def _ensure_remote_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS site_remote_connections (
            id TEXT PRIMARY KEY,
            site_project_id TEXT NOT NULL UNIQUE,
            connection_type TEXT NOT NULL,
            host TEXT NOT NULL,
            port INTEGER NOT NULL,
            username TEXT NOT NULL,
            password_encrypted TEXT NOT NULL,
            remote_path TEXT NOT NULL,
            passive_mode INTEGER NOT NULL CHECK (passive_mode IN (0, 1)),
            verify_host INTEGER NOT NULL CHECK (verify_host IN (0, 1)),
            FOREIGN KEY (site_project_id) REFERENCES site_registry(id) ON DELETE CASCADE
        )
        """
    )


def _migrate_legacy_ftp_schema(connection: sqlite3.Connection) -> None:
    columns = _get_table_columns(connection, "site_registry")
    legacy_columns = {
        "ftp_host",
        "ftp_port",
        "ftp_username",
        "ftp_password_encrypted",
        "ftp_remote_path",
    }
    if not legacy_columns.issubset(set(columns)):
        return
    connection.execute(
        """
        CREATE TEMP TABLE site_remote_connections_legacy_migration AS
        SELECT
            'remote-' || id AS id,
            id AS site_project_id,
            ? AS connection_type,
            ftp_host AS host,
            ftp_port AS port,
            ftp_username AS username,
            ftp_password_encrypted AS password_encrypted,
            ftp_remote_path AS remote_path,
            1 AS passive_mode,
            1 AS verify_host
        FROM site_registry
        WHERE TRIM(COALESCE(ftp_host, '')) != ''
        """,
        (BuiltinRemoteConnectionType.FTP.value,),
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS site_registry_migrated (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            framework_type TEXT NOT NULL,
            local_path TEXT NOT NULL UNIQUE,
            default_locale TEXT NOT NULL,
            is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        INSERT INTO site_registry_migrated (
            id,
            name,
            framework_type,
            local_path,
            default_locale,
            is_active
        )
        SELECT
            id,
            name,
            framework_type,
            local_path,
            default_locale,
            is_active
        FROM site_registry
        """
    )
    connection.execute("DROP TABLE site_registry")
    connection.execute("ALTER TABLE site_registry_migrated RENAME TO site_registry")
    connection.execute(
        """
        INSERT INTO site_remote_connections (
            id,
            site_project_id,
            connection_type,
            host,
            port,
            username,
            password_encrypted,
            remote_path,
            passive_mode,
            verify_host
        )
        SELECT
            legacy.id,
            legacy.site_project_id,
            legacy.connection_type,
            legacy.host,
            legacy.port,
            legacy.username,
            legacy.password_encrypted,
            legacy.remote_path,
            legacy.passive_mode,
            legacy.verify_host
        FROM site_remote_connections_legacy_migration AS legacy
        WHERE NOT EXISTS (
            SELECT 1
            FROM site_remote_connections
            WHERE site_project_id = legacy.site_project_id
        )
        """
    )
    connection.execute("DROP TABLE site_remote_connections_legacy_migration")


def _get_table_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(row["name"]) for row in rows]


def _project_params(project: SiteProject) -> tuple[object, ...]:
    return (
        project.id,
        project.name,
        project.framework_type,
        project.local_path,
        project.default_locale,
        int(project.is_active),
    )


def _project_update_params(project: SiteProject) -> tuple[object, ...]:
    return (
        project.name,
        project.framework_type,
        project.local_path,
        project.default_locale,
        int(project.is_active),
        project.id,
    )


def _connection_params(
    connection: RemoteConnectionConfig,
    secret_cipher: LocalKeySiteSecretCipher,
) -> tuple[object, ...]:
    return (
        connection.id,
        connection.site_project_id,
        connection.connection_type,
        connection.host,
        connection.port,
        connection.username,
        secret_cipher.encrypt(connection.password),
        connection.remote_path,
        int(connection.flags.passive_mode),
        int(connection.flags.verify_host),
    )


def _map_row_to_site(
    row: sqlite3.Row,
    secret_cipher: LocalKeySiteSecretCipher,
) -> RegisteredSite:
    project = SiteProject(
        id=str(row["id"]),
        name=str(row["name"]),
        framework_type=str(row["framework_type"]),
        local_path=str(row["local_path"]),
        default_locale=str(row["default_locale"]),
        is_active=bool(row["is_active"]),
    )
    remote_connection: RemoteConnectionConfig | None = None
    if row["remote_id"] is not None:
        remote_connection = RemoteConnectionConfig(
            id=str(row["remote_id"]),
            site_project_id=project.id,
            connection_type=str(row["connection_type"]),
            host=str(row["host"]),
            port=int(row["port"]),
            username=str(row["username"]),
            password=secret_cipher.decrypt(str(row["password_encrypted"])),
            remote_path=str(row["remote_path"]),
            flags=RemoteConnectionFlags(
                passive_mode=bool(row["passive_mode"]),
                verify_host=bool(row["verify_host"]),
            ),
        )
    return RegisteredSite(project=project, remote_connection=remote_connection)


def _map_integrity_error(site_name: str) -> SiteRegistryConflictError:
    msg = f"A site with the name '{site_name}' already exists."
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
