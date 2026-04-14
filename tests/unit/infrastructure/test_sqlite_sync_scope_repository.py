"""Unit tests for SQLite-backed sync scope settings persistence."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

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
