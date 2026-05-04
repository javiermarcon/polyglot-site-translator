"""Unit tests for SQLite-backed sync scope settings persistence."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sqlite3

import pytest

from polyglot_site_translator.domain.sync.errors import SyncScopePersistenceError
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScopeSettings,
    ConfiguredSyncRule,
    FrameworkSyncRuleSet,
    SyncFilterType,
    SyncRuleBehavior,
    build_default_sync_scope_settings,
)
from polyglot_site_translator.infrastructure.database_location import (
    SQLiteDatabaseLocation,
)
from polyglot_site_translator.infrastructure.settings import TomlSettingsService
from polyglot_site_translator.infrastructure.sync_scope_sqlite import (
    ConfiguredSqliteSyncScopeRepository,
    SqliteSyncScopeRepository,
    _configuration_exists,
    _fetch_configuration_flag,
    _insert_configuration_flag,
    _insert_configured_framework_rules,
    _insert_configured_global_rules,
)


def test_sqlite_sync_scope_repository_roundtrips_global_and_framework_rules(
    tmp_path: Path,
) -> None:
    location = SQLiteDatabaseLocation(
        directory=tmp_path,
        filename="site_registry.sqlite3",
        database_path=tmp_path / "site_registry.sqlite3",
    )
    repository = SqliteSyncScopeRepository(location=location)
    settings = AdapterSyncScopeSettings(
        global_rules=(
            ConfiguredSyncRule(
                relative_path=".cache",
                filter_type=SyncFilterType.DIRECTORY,
                behavior=SyncRuleBehavior.EXCLUDE,
                description="Ignore cache directories.",
                is_enabled=True,
            ),
        ),
        framework_rule_sets=(
            FrameworkSyncRuleSet(
                framework_type="django",
                rules=(
                    ConfiguredSyncRule(
                        relative_path="staticfiles",
                        filter_type=SyncFilterType.DIRECTORY,
                        behavior=SyncRuleBehavior.EXCLUDE,
                        description="Ignore collected static files.",
                        is_enabled=True,
                    ),
                ),
            ),
        ),
        use_gitignore_rules=True,
    )

    repository.save_sync_scope_settings(settings)
    loaded_settings = repository.load_sync_scope_settings(
        default_settings=build_default_sync_scope_settings(),
    )

    assert loaded_settings.use_gitignore_rules is True
    assert loaded_settings.global_rules == settings.global_rules
    assert loaded_settings.framework_rule_sets == settings.framework_rule_sets


def test_sqlite_sync_scope_repository_returns_default_settings_when_empty(
    tmp_path: Path,
) -> None:
    location = SQLiteDatabaseLocation(
        directory=tmp_path,
        filename="site_registry.sqlite3",
        database_path=tmp_path / "site_registry.sqlite3",
    )
    repository = SqliteSyncScopeRepository(location=location)
    default_settings = build_default_sync_scope_settings()

    loaded_settings = repository.load_sync_scope_settings(default_settings=default_settings)

    assert loaded_settings == default_settings


def test_configured_sqlite_sync_scope_repository_falls_back_to_toml_settings_when_db_is_empty(
    tmp_path: Path,
) -> None:
    settings_path = tmp_path / "settings.toml"
    settings_service = TomlSettingsService(settings_path=settings_path)
    saved_settings = settings_service.save_settings(
        replace(
            settings_service.load_settings().app_settings,
            sync_scope_settings=AdapterSyncScopeSettings(
                global_rules=(
                    ConfiguredSyncRule(
                        relative_path=".cache",
                        filter_type=SyncFilterType.DIRECTORY,
                        behavior=SyncRuleBehavior.EXCLUDE,
                        description="Ignore cache directories.",
                        is_enabled=True,
                    ),
                ),
                framework_rule_sets=(
                    FrameworkSyncRuleSet(
                        framework_type="flask",
                        rules=(
                            ConfiguredSyncRule(
                                relative_path="instance",
                                filter_type=SyncFilterType.DIRECTORY,
                                behavior=SyncRuleBehavior.EXCLUDE,
                                description="Ignore Flask instance folders.",
                                is_enabled=True,
                            ),
                        ),
                    ),
                ),
                use_gitignore_rules=False,
            ),
        )
    ).app_settings

    wrapper = ConfiguredSqliteSyncScopeRepository(settings_service)
    loaded_settings = wrapper.load_sync_scope_settings()

    assert loaded_settings == saved_settings.sync_scope_settings


def test_sqlite_sync_scope_repository_wraps_schema_read_and_write_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location = SQLiteDatabaseLocation(
        directory=tmp_path,
        filename="site_registry.sqlite3",
        database_path=tmp_path / "site_registry.sqlite3",
    )

    def _failing_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        del self, args, kwargs
        msg = "directory denied"
        raise OSError(msg)

    monkeypatch.setattr(Path, "mkdir", _failing_mkdir)

    with pytest.raises(SyncScopePersistenceError, match="directory could not be prepared"):
        SqliteSyncScopeRepository(location=location)


def test_sqlite_sync_scope_repository_wraps_schema_sqlite_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location = SQLiteDatabaseLocation(
        directory=tmp_path,
        filename="site_registry.sqlite3",
        database_path=tmp_path / "site_registry.sqlite3",
    )

    def _raise_sqlite_error(_database_path: Path) -> sqlite3.Connection:
        msg = "schema failed"
        raise sqlite3.OperationalError(msg)

    monkeypatch.setattr(sqlite3, "connect", _raise_sqlite_error)

    with pytest.raises(SyncScopePersistenceError, match="schema initialization failed"):
        SqliteSyncScopeRepository(location=location)


def test_sqlite_sync_scope_repository_wraps_sqlite_failures_for_read_and_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location = SQLiteDatabaseLocation(
        directory=tmp_path,
        filename="site_registry.sqlite3",
        database_path=tmp_path / "site_registry.sqlite3",
    )
    repository = SqliteSyncScopeRepository(location=location)

    def _broken_connect(self: SqliteSyncScopeRepository) -> sqlite3.Connection:
        del self
        msg = "db broken"
        raise sqlite3.OperationalError(msg)

    monkeypatch.setattr(SqliteSyncScopeRepository, "_connect", _broken_connect)

    with pytest.raises(SyncScopePersistenceError, match="persistence read failed"):
        repository.load_sync_scope_settings()

    with pytest.raises(SyncScopePersistenceError, match="persistence write failed"):
        repository.save_sync_scope_settings(build_default_sync_scope_settings())


def test_sqlite_sync_scope_repository_helpers_cover_invalid_and_empty_cases(
    tmp_path: Path,
) -> None:
    connection = sqlite3.connect(tmp_path / "sync_scope.sqlite3")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE sync_scope_configuration (
            config_key TEXT PRIMARY KEY,
            config_value TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE sync_scope_global_rules (
            rule_key TEXT PRIMARY KEY,
            relative_path TEXT NOT NULL,
            filter_type TEXT NOT NULL,
            rule_behavior TEXT NOT NULL,
            description TEXT NOT NULL,
            is_enabled INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE sync_scope_framework_rules (
            rule_key TEXT PRIMARY KEY,
            framework_type TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            filter_type TEXT NOT NULL,
            rule_behavior TEXT NOT NULL,
            description TEXT NOT NULL,
            is_enabled INTEGER NOT NULL
        )
        """
    )

    assert _configuration_exists(connection) is False
    assert _fetch_configuration_flag(connection, "use_gitignore_rules", True) is True

    connection.execute(
        "INSERT INTO sync_scope_configuration (config_key, config_value) VALUES (?, ?)",
        ("use_gitignore_rules", "broken"),
    )
    with pytest.raises(SyncScopePersistenceError, match="Invalid sync scope configuration value"):
        _fetch_configuration_flag(connection, "use_gitignore_rules", False)

    connection.execute("DELETE FROM sync_scope_configuration")
    _insert_configuration_flag(connection, "use_gitignore_rules", False)
    assert _configuration_exists(connection) is True
    assert _fetch_configuration_flag(connection, "use_gitignore_rules", True) is False

    _insert_configured_global_rules(connection, ())
    _insert_configured_framework_rules(connection, ())

    assert connection.execute("SELECT COUNT(*) FROM sync_scope_global_rules").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM sync_scope_framework_rules").fetchone()[0] == 0


def test_configured_sqlite_sync_scope_repository_save_resolves_location(
    tmp_path: Path,
) -> None:
    settings_path = tmp_path / "settings.toml"
    settings_service = TomlSettingsService(settings_path=settings_path)
    settings_state = settings_service.save_settings(
        replace(
            settings_service.load_settings().app_settings,
            database_directory=str(tmp_path),
            database_filename="site_registry.sqlite3",
        )
    )
    repository = ConfiguredSqliteSyncScopeRepository(settings_service)
    sync_scope_settings = replace(
        settings_state.app_settings.sync_scope_settings,
        use_gitignore_rules=True,
    )

    repository.save_sync_scope_settings(sync_scope_settings)
    loaded = repository.load_sync_scope_settings()

    assert loaded.use_gitignore_rules is True
