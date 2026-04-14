"""SQLite-backed persistence for shared sync scope settings."""

from __future__ import annotations

import sqlite3

from polyglot_site_translator.domain.sync.errors import SyncScopePersistenceError
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScopeSettings,
    ConfiguredSyncRule,
    FrameworkSyncRuleSet,
    SyncFilterType,
    SyncRuleBehavior,
    build_default_sync_scope_settings,
    build_framework_sync_rule_key,
    build_global_sync_rule_key,
)
from polyglot_site_translator.infrastructure.database_location import (
    SQLiteDatabaseLocation,
    resolve_sqlite_database_location,
)
from polyglot_site_translator.infrastructure.settings import TomlSettingsService


class SqliteSyncScopeRepository:
    """Persist shared sync scope settings in the configured SQLite database."""

    def __init__(self, *, location: SQLiteDatabaseLocation) -> None:
        self._location = location
        self._ensure_schema()

    def load_sync_scope_settings(
        self,
        default_settings: AdapterSyncScopeSettings | None = None,
    ) -> AdapterSyncScopeSettings:
        """Load shared sync scope settings from SQLite.

        If the database does not yet contain sync scope settings, the provided
        default_settings are returned unchanged.
        """
        default_settings = default_settings or build_default_sync_scope_settings()
        try:
            with self._connect() as connection:
                global_rules = _fetch_configured_rules(connection, "sync_scope_global_rules")
                framework_rule_sets = _fetch_framework_rule_sets(connection)
                use_gitignore_rules = _fetch_configuration_flag(
                    connection,
                    "use_gitignore_rules",
                    default_settings.use_gitignore_rules,
                )
                configuration_exists = _configuration_exists(connection)
        except sqlite3.Error as error:
            msg = f"SQLite sync scope persistence read failed at {self._location.database_path}."
            raise SyncScopePersistenceError(msg) from error

        if not global_rules and not framework_rule_sets and not configuration_exists:
            return default_settings

        return AdapterSyncScopeSettings(
            global_rules=global_rules,
            framework_rule_sets=framework_rule_sets,
            use_gitignore_rules=use_gitignore_rules,
        )

    def save_sync_scope_settings(self, sync_scope_settings: AdapterSyncScopeSettings) -> None:
        """Persist shared sync scope settings into SQLite."""
        try:
            with self._connect() as connection:
                connection.execute("DELETE FROM sync_scope_global_rules")
                connection.execute("DELETE FROM sync_scope_framework_rules")
                connection.execute("DELETE FROM sync_scope_configuration")
                _insert_configured_global_rules(connection, sync_scope_settings.global_rules)
                _insert_configured_framework_rules(
                    connection,
                    sync_scope_settings.framework_rule_sets,
                )
                _insert_configuration_flag(
                    connection,
                    "use_gitignore_rules",
                    sync_scope_settings.use_gitignore_rules,
                )
        except sqlite3.Error as error:
            msg = f"SQLite sync scope persistence write failed at {self._location.database_path}."
            raise SyncScopePersistenceError(msg) from error

    def _ensure_schema(self) -> None:
        try:
            self._location.directory.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                _ensure_sync_scope_global_rules_table(connection)
                _ensure_sync_scope_framework_rules_table(connection)
                _ensure_sync_scope_configuration_table(connection)
        except sqlite3.Error as error:
            msg = (
                f"SQLite sync scope schema initialization failed at {self._location.database_path}."
            )
            raise SyncScopePersistenceError(msg) from error
        except OSError as error:
            msg = (
                f"SQLite sync scope directory could not be prepared at {self._location.directory}."
            )
            raise SyncScopePersistenceError(msg) from error

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._location.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class ConfiguredSqliteSyncScopeRepository:
    """Resolve the SQLite location from app settings before each sync scope operation."""

    def __init__(self, settings_service: TomlSettingsService) -> None:
        self._settings_service = settings_service

    def load_sync_scope_settings(
        self,
        default_settings: AdapterSyncScopeSettings | None = None,
    ) -> AdapterSyncScopeSettings:
        settings_state = self._settings_service.load_settings()
        location = resolve_sqlite_database_location(settings_state.app_settings)
        default_settings = default_settings or settings_state.app_settings.sync_scope_settings
        repository = SqliteSyncScopeRepository(location=location)
        return repository.load_sync_scope_settings(default_settings=default_settings)

    def save_sync_scope_settings(self, sync_scope_settings: AdapterSyncScopeSettings) -> None:
        settings_state = self._settings_service.load_settings()
        location = resolve_sqlite_database_location(settings_state.app_settings)
        repository = SqliteSyncScopeRepository(location=location)
        repository.save_sync_scope_settings(sync_scope_settings)


def _ensure_sync_scope_global_rules_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_scope_global_rules (
            rule_key TEXT PRIMARY KEY,
            relative_path TEXT NOT NULL,
            filter_type TEXT NOT NULL,
            rule_behavior TEXT NOT NULL,
            description TEXT NOT NULL,
            is_enabled INTEGER NOT NULL CHECK (is_enabled IN (0, 1))
        )
        """
    )


def _ensure_sync_scope_framework_rules_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_scope_framework_rules (
            rule_key TEXT PRIMARY KEY,
            framework_type TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            filter_type TEXT NOT NULL,
            rule_behavior TEXT NOT NULL,
            description TEXT NOT NULL,
            is_enabled INTEGER NOT NULL CHECK (is_enabled IN (0, 1))
        )
        """
    )


def _ensure_sync_scope_configuration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_scope_configuration (
            config_key TEXT PRIMARY KEY,
            config_value TEXT NOT NULL
        )
        """
    )


def _fetch_configured_rules(
    connection: sqlite3.Connection,
    table_name: str,
) -> tuple[ConfiguredSyncRule, ...]:
    rows = connection.execute(
        f"""
        SELECT relative_path,
               filter_type,
               rule_behavior,
               description,
               is_enabled
        FROM {table_name}
        ORDER BY rowid
        """
    ).fetchall()
    return tuple(
        ConfiguredSyncRule(
            relative_path=str(row["relative_path"]),
            filter_type=SyncFilterType(str(row["filter_type"])),
            behavior=SyncRuleBehavior(str(row["rule_behavior"])),
            description=str(row["description"]),
            is_enabled=bool(row["is_enabled"]),
        )
        for row in rows
    )


def _fetch_framework_rule_sets(connection: sqlite3.Connection) -> tuple[FrameworkSyncRuleSet, ...]:
    rows = connection.execute(
        """
        SELECT framework_type,
               relative_path,
               filter_type,
               rule_behavior,
               description,
               is_enabled
        FROM sync_scope_framework_rules
        ORDER BY framework_type, rowid
        """
    ).fetchall()
    rules_by_framework: dict[str, list[ConfiguredSyncRule]] = {}
    for row in rows:
        normalized_framework_type = str(row["framework_type"]).strip().lower()
        rules_by_framework.setdefault(normalized_framework_type, []).append(
            ConfiguredSyncRule(
                relative_path=str(row["relative_path"]),
                filter_type=SyncFilterType(str(row["filter_type"])),
                behavior=SyncRuleBehavior(str(row["rule_behavior"])),
                description=str(row["description"]),
                is_enabled=bool(row["is_enabled"]),
            )
        )
    return tuple(
        FrameworkSyncRuleSet(framework_type=framework_type, rules=tuple(rules))
        for framework_type, rules in sorted(rules_by_framework.items())
    )


def _fetch_configuration_flag(
    connection: sqlite3.Connection,
    config_key: str,
    default_value: bool,
) -> bool:
    row = connection.execute(
        "SELECT config_value FROM sync_scope_configuration WHERE config_key = ?",
        (config_key,),
    ).fetchone()
    if row is None:
        return default_value
    value = str(row["config_value"]).strip()
    if value not in {"0", "1"}:
        msg = f"Invalid sync scope configuration value for '{config_key}': {value}"
        raise SyncScopePersistenceError(msg)
    return value == "1"


def _configuration_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute("SELECT 1 FROM sync_scope_configuration LIMIT 1").fetchone()
    return row is not None


def _insert_configured_global_rules(
    connection: sqlite3.Connection,
    configured_rules: tuple[ConfiguredSyncRule, ...],
) -> None:
    if not configured_rules:
        return
    connection.executemany(
        """
        INSERT INTO sync_scope_global_rules (
            rule_key,
            relative_path,
            filter_type,
            rule_behavior,
            description,
            is_enabled
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                build_global_sync_rule_key(
                    relative_path=rule.relative_path,
                    filter_type=rule.filter_type,
                    behavior=rule.behavior,
                ),
                rule.relative_path,
                rule.filter_type.value,
                rule.behavior.value,
                rule.description,
                int(rule.is_enabled),
            )
            for rule in configured_rules
        ],
    )


def _insert_configured_framework_rules(
    connection: sqlite3.Connection,
    framework_rule_sets: tuple[FrameworkSyncRuleSet, ...],
) -> None:
    if not framework_rule_sets:
        return
    records: list[tuple[str, str, str, str, str, str, int]] = []
    for rule_set in framework_rule_sets:
        normalized_framework_type = rule_set.normalized_framework_type()
        for rule in rule_set.rules:
            records.append(
                (
                    build_framework_sync_rule_key(
                        framework_type=normalized_framework_type,
                        relative_path=rule.relative_path,
                        filter_type=rule.filter_type,
                        behavior=rule.behavior,
                    ),
                    normalized_framework_type,
                    rule.relative_path,
                    rule.filter_type.value,
                    rule.behavior.value,
                    rule.description,
                    int(rule.is_enabled),
                )
            )
    connection.executemany(
        """
        INSERT INTO sync_scope_framework_rules (
            rule_key,
            framework_type,
            relative_path,
            filter_type,
            rule_behavior,
            description,
            is_enabled
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )


def _insert_configuration_flag(
    connection: sqlite3.Connection,
    config_key: str,
    value: bool,
) -> None:
    connection.execute(
        "INSERT INTO sync_scope_configuration (config_key, config_value) VALUES (?, ?)",
        (config_key, "1" if value else "0"),
    )
