"""TOML-backed frontend settings persistence."""

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import tomllib
from typing import Any

from polyglot_site_translator.domain.site_registry.errors import SiteRegistryValidationError
from polyglot_site_translator.domain.site_registry.locales import normalize_default_locale
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScopeSettings,
    ConfiguredSyncRule,
    FrameworkSyncRuleSet,
    SyncFilterType,
    SyncRuleBehavior,
)
from polyglot_site_translator.infrastructure.database_location import (
    DEFAULT_DATABASE_FILENAME,
    normalize_database_filename,
    validate_database_directory,
)
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.router import RouteName
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    SettingsStateViewModel,
    build_default_app_settings,
    build_settings_state,
)

CONFIG_DIR_ENV_VAR = "POLYGLOT_SITE_TRANSLATOR_CONFIG_DIR"
APP_CONFIG_DIRNAME = "polyglot-site-translator"
SETTINGS_FILENAME = "settings.toml"
SETTINGS_SCHEMA_VERSION = 1
_ALLOWED_THEME_MODES = {"system", "light", "dark"}
_ALLOWED_UI_LANGUAGES = {"en", "es"}
_ALLOWED_ROUTE_NAMES = {route_name.value for route_name in RouteName}


def resolve_user_config_dir(explicit_dir: Path | None = None) -> Path:
    """Return the platform-aware per-user configuration directory."""
    if explicit_dir is not None:
        return explicit_dir

    override_dir = os.getenv(CONFIG_DIR_ENV_VAR)
    if override_dir:
        return Path(override_dir).expanduser()

    if os.name == "nt":
        return _resolve_windows_config_dir()

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_CONFIG_DIRNAME

    return _resolve_posix_config_dir()


def build_default_settings_service(config_dir: Path | None = None) -> TomlSettingsService:
    """Build the default TOML-backed settings service for the current user."""
    settings_path = resolve_user_config_dir(config_dir) / SETTINGS_FILENAME
    return TomlSettingsService(settings_path=settings_path)


def _resolve_windows_config_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_CONFIG_DIRNAME
    return Path.home() / "AppData" / "Roaming" / APP_CONFIG_DIRNAME


def _resolve_posix_config_dir() -> Path:
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / APP_CONFIG_DIRNAME
    return Path.home() / ".config" / APP_CONFIG_DIRNAME


class TomlSettingsService:
    """Persist frontend app settings in a TOML file."""

    def __init__(self, settings_path: Path) -> None:
        self._settings_path = settings_path

    @property
    def settings_path(self) -> Path:
        """Return the backing TOML file path."""
        return self._settings_path

    def load_settings(self) -> SettingsStateViewModel:
        """Load settings from TOML or fall back to defaults."""
        try:
            app_settings = self._load_app_settings()
        except OSError as error:
            msg = f"App settings could not be loaded from {self._settings_path}."
            raise ControlledServiceError(msg) from error
        except tomllib.TOMLDecodeError as error:
            msg = f"App settings contain invalid TOML in {self._settings_path}."
            raise ControlledServiceError(msg) from error
        return build_settings_state(
            app_settings=app_settings,
            status="loaded",
            status_message="Settings loaded.",
        )

    def save_settings(self, app_settings: AppSettingsViewModel) -> SettingsStateViewModel:
        """Persist the provided settings as TOML."""
        normalized_settings = _validate_app_settings(
            _with_default_database_directory(
                app_settings,
                default_directory=self._settings_path.parent,
            )
        )
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            self._settings_path.write_text(
                _serialize_settings_document(normalized_settings),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"App settings could not be saved to {self._settings_path}."
            raise ControlledServiceError(msg) from error
        return build_settings_state(
            app_settings=normalized_settings,
            status="saved",
            status_message="Settings saved.",
        )

    def reset_settings(self) -> SettingsStateViewModel:
        """Restore and persist frontend defaults."""
        default_settings = build_default_app_settings(
            database_directory=str(self._settings_path.parent),
            database_filename=DEFAULT_DATABASE_FILENAME,
        )
        return replace(
            self.save_settings(default_settings),
            status="defaults-restored",
            status_message="Settings restored to defaults.",
        )

    def _load_app_settings(self) -> AppSettingsViewModel:
        if not self._settings_path.exists():
            return _build_default_persisted_settings(self._settings_path.parent)

        raw_document = tomllib.loads(self._settings_path.read_text(encoding="utf-8"))
        if not raw_document:
            return _build_default_persisted_settings(self._settings_path.parent)

        raw_settings = _read_app_table(raw_document)
        default_settings = _build_default_persisted_settings(self._settings_path.parent)
        app_settings = replace(
            default_settings,
            theme_mode=_read_string(raw_settings, "theme_mode", default_settings.theme_mode),
            window_width=_read_int(raw_settings, "window_width", default_settings.window_width),
            window_height=_read_int(raw_settings, "window_height", default_settings.window_height),
            remember_last_screen=_read_bool(
                raw_settings,
                "remember_last_screen",
                default_settings.remember_last_screen,
            ),
            last_opened_screen=_read_string(
                raw_settings,
                "last_opened_screen",
                default_settings.last_opened_screen,
            ),
            developer_mode=_read_bool(
                raw_settings,
                "developer_mode",
                default_settings.developer_mode,
            ),
            ui_language=_read_string(raw_settings, "ui_language", default_settings.ui_language),
            default_project_locale=_read_translation_default_project_locale(
                raw_document,
                default_settings.default_project_locale,
            ),
            default_compile_mo=_read_translation_default_compile_mo(
                raw_document,
                default_settings.default_compile_mo,
            ),
            default_use_external_translator=_read_translation_default_use_external_translator(
                raw_document,
                default_settings.default_use_external_translator,
            ),
            database_directory=_read_string(
                raw_settings,
                "database_directory",
                default_settings.database_directory,
            ),
            database_filename=_read_string(
                raw_settings,
                "database_filename",
                default_settings.database_filename,
            ),
            sync_progress_log_limit=_read_int(
                raw_settings,
                "sync_progress_log_limit",
                default_settings.sync_progress_log_limit,
            ),
            sync_scope_settings=_read_sync_scope_settings(
                raw_document,
                default_settings.sync_scope_settings,
            ),
        )
        return _validate_app_settings(app_settings)


def _build_default_persisted_settings(settings_directory: Path) -> AppSettingsViewModel:
    return build_default_app_settings(database_directory=str(settings_directory))


def _with_default_database_directory(
    app_settings: AppSettingsViewModel,
    *,
    default_directory: Path,
) -> AppSettingsViewModel:
    if app_settings.database_directory.strip():
        return app_settings
    return replace(app_settings, database_directory=str(default_directory))


def _read_app_table(raw_document: dict[str, Any]) -> dict[str, Any]:
    raw_app_settings = raw_document.get("app")
    if raw_app_settings is None:
        return {}
    if isinstance(raw_app_settings, dict):
        return raw_app_settings
    msg = "The [app] settings section must be a TOML table."
    raise ControlledServiceError(msg)


def _read_string(raw_settings: dict[str, Any], key: str, default: str) -> str:
    raw_value = raw_settings.get(key, default)
    if isinstance(raw_value, str):
        return raw_value
    msg = f"The app setting '{key}' must be a string."
    raise ControlledServiceError(msg)


def _read_int(raw_settings: dict[str, Any], key: str, default: int) -> int:
    raw_value = raw_settings.get(key, default)
    if isinstance(raw_value, int) and not isinstance(raw_value, bool):
        return raw_value
    msg = f"The app setting '{key}' must be an integer."
    raise ControlledServiceError(msg)


def _read_bool(raw_settings: dict[str, Any], key: str, default: bool) -> bool:
    raw_value = raw_settings.get(key, default)
    if isinstance(raw_value, bool):
        return raw_value
    msg = f"The app setting '{key}' must be a boolean."
    raise ControlledServiceError(msg)


def _validate_app_settings(app_settings: AppSettingsViewModel) -> AppSettingsViewModel:
    if app_settings.theme_mode not in _ALLOWED_THEME_MODES:
        msg = f"Unsupported theme mode: {app_settings.theme_mode}"
        raise ControlledServiceError(msg)
    if app_settings.window_width <= 0 or app_settings.window_height <= 0:
        msg = "Window dimensions must be positive integers."
        raise ControlledServiceError(msg)
    if app_settings.ui_language not in _ALLOWED_UI_LANGUAGES:
        msg = f"Unsupported UI language: {app_settings.ui_language}"
        raise ControlledServiceError(msg)
    if app_settings.last_opened_screen not in _ALLOWED_ROUTE_NAMES:
        msg = f"Unsupported last opened screen: {app_settings.last_opened_screen}"
        raise ControlledServiceError(msg)
    if app_settings.sync_progress_log_limit <= 0:
        msg = "Sync progress log limit must be a positive integer."
        raise ControlledServiceError(msg)
    try:
        default_project_locale = normalize_default_locale(
            app_settings.default_project_locale,
            label="Default project locale",
        )
    except SiteRegistryValidationError as error:
        raise ControlledServiceError(str(error)) from error
    try:
        database_directory = str(validate_database_directory(app_settings.database_directory))
        database_filename = normalize_database_filename(app_settings.database_filename)
    except ValueError as error:
        raise ControlledServiceError(str(error)) from error
    return replace(
        app_settings,
        default_project_locale=default_project_locale,
        database_directory=database_directory,
        database_filename=database_filename,
        sync_scope_settings=_validate_sync_scope_settings(app_settings.sync_scope_settings),
    )


def _serialize_settings_document(app_settings: AppSettingsViewModel) -> str:
    document = (
        "# Polyglot Site Translator frontend settings\n"
        "[meta]\n"
        f"schema_version = {SETTINGS_SCHEMA_VERSION}\n\n"
        "[app]\n"
        f"theme_mode = {_format_toml_string(app_settings.theme_mode)}\n"
        f"window_width = {app_settings.window_width}\n"
        f"window_height = {app_settings.window_height}\n"
        f"remember_last_screen = {_format_toml_bool(app_settings.remember_last_screen)}\n"
        f"last_opened_screen = {_format_toml_string(app_settings.last_opened_screen)}\n"
        f"developer_mode = {_format_toml_bool(app_settings.developer_mode)}\n"
        f"ui_language = {_format_toml_string(app_settings.ui_language)}\n"
        f"database_directory = {_format_toml_string(app_settings.database_directory)}\n"
        f"database_filename = {_format_toml_string(app_settings.database_filename)}\n"
        f"sync_progress_log_limit = {app_settings.sync_progress_log_limit}\n"
        "\n"
        "[translation]\n"
        f"default_project_locale = {_format_toml_string(app_settings.default_project_locale)}\n"
        f"default_compile_mo = {_format_toml_bool(app_settings.default_compile_mo)}\n"
        "default_use_external_translator = "
        f"{_format_toml_bool(app_settings.default_use_external_translator)}\n"
    )
    document += _serialize_sync_scope_settings(app_settings.sync_scope_settings)
    return document


def _format_toml_string(value: str) -> str:
    return json.dumps(value)


def _format_toml_bool(value: bool) -> str:
    if value:
        return "true"
    return "false"


def _read_translation_default_project_locale(
    raw_document: dict[str, Any],
    default_locale: str,
) -> str:
    raw_translation = raw_document.get("translation")
    if raw_translation is None:
        return default_locale
    if not isinstance(raw_translation, dict):
        msg = "The [translation] settings section must be a TOML table."
        raise ControlledServiceError(msg)
    raw_value = raw_translation.get("default_project_locale", default_locale)
    if isinstance(raw_value, str):
        return raw_value
    msg = "The translation setting 'default_project_locale' must be a string."
    raise ControlledServiceError(msg)


def _read_translation_default_compile_mo(
    raw_document: dict[str, Any],
    default_compile_mo: bool,
) -> bool:
    raw_translation = raw_document.get("translation")
    if raw_translation is None:
        return default_compile_mo
    if not isinstance(raw_translation, dict):
        msg = "The [translation] settings section must be a TOML table."
        raise ControlledServiceError(msg)
    raw_value = raw_translation.get("default_compile_mo", default_compile_mo)
    if isinstance(raw_value, bool):
        return raw_value
    msg = "The translation setting 'default_compile_mo' must be a boolean."
    raise ControlledServiceError(msg)


def _read_translation_default_use_external_translator(
    raw_document: dict[str, Any],
    default_use_external_translator: bool,
) -> bool:
    raw_translation = raw_document.get("translation")
    if raw_translation is None:
        return default_use_external_translator
    if not isinstance(raw_translation, dict):
        msg = "The [translation] settings section must be a TOML table."
        raise ControlledServiceError(msg)
    raw_value = raw_translation.get(
        "default_use_external_translator",
        default_use_external_translator,
    )
    if isinstance(raw_value, bool):
        return raw_value
    msg = "The translation setting 'default_use_external_translator' must be a boolean."
    raise ControlledServiceError(msg)


def _read_sync_scope_settings(
    raw_document: dict[str, Any],
    default_settings: AdapterSyncScopeSettings,
) -> AdapterSyncScopeSettings:
    raw_sync_scope = raw_document.get("sync_scope")
    if raw_sync_scope is None:
        return default_settings
    if not isinstance(raw_sync_scope, dict):
        msg = "The [sync_scope] settings section must be a TOML table."
        raise ControlledServiceError(msg)
    return AdapterSyncScopeSettings(
        global_rules=_read_configured_rules(
            raw_sync_scope.get("global_rules"),
            key="sync_scope.global_rules",
        ),
        framework_rule_sets=_read_framework_rule_sets(
            raw_sync_scope.get("framework_rules"),
        ),
        use_gitignore_rules=_read_bool(
            raw_sync_scope,
            "use_gitignore_rules",
            default_settings.use_gitignore_rules,
        ),
    )


def _read_configured_rules(
    raw_rules: Any,
    *,
    key: str,
) -> tuple[ConfiguredSyncRule, ...]:
    if raw_rules is None:
        return ()
    if not isinstance(raw_rules, list):
        msg = f"The {key} setting must be an array of TOML tables."
        raise ControlledServiceError(msg)
    configured_rules: list[ConfiguredSyncRule] = []
    for index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, dict):
            msg = f"The {key}[{index}] setting must be a TOML table."
            raise ControlledServiceError(msg)
        configured_rules.append(
            ConfiguredSyncRule(
                relative_path=_read_string(raw_rule, "relative_path", ""),
                filter_type=_read_sync_filter_type(raw_rule, key=f"{key}[{index}]"),
                behavior=_read_sync_rule_behavior(raw_rule, key=f"{key}[{index}]"),
                description=_read_string(raw_rule, "description", ""),
                is_enabled=_read_bool(raw_rule, "is_enabled", True),
            )
        )
    return tuple(configured_rules)


def _read_framework_rule_sets(raw_framework_rules: Any) -> tuple[FrameworkSyncRuleSet, ...]:
    if raw_framework_rules is None:
        return ()
    if not isinstance(raw_framework_rules, list):
        msg = "The sync_scope.framework_rules setting must be an array of TOML tables."
        raise ControlledServiceError(msg)
    framework_rules: dict[str, list[ConfiguredSyncRule]] = {}
    for index, raw_rule in enumerate(raw_framework_rules):
        if not isinstance(raw_rule, dict):
            msg = f"The sync_scope.framework_rules[{index}] setting must be a TOML table."
            raise ControlledServiceError(msg)
        framework_type = _read_string(raw_rule, "framework_type", "").strip().lower()
        if framework_type == "":
            msg = "Framework sync rules require a non-empty framework_type."
            raise ControlledServiceError(msg)
        framework_rules.setdefault(framework_type, []).append(
            ConfiguredSyncRule(
                relative_path=_read_string(raw_rule, "relative_path", ""),
                filter_type=_read_sync_filter_type(
                    raw_rule,
                    key=f"sync_scope.framework_rules[{index}]",
                ),
                behavior=_read_sync_rule_behavior(
                    raw_rule,
                    key=f"sync_scope.framework_rules[{index}]",
                ),
                description=_read_string(raw_rule, "description", ""),
                is_enabled=_read_bool(raw_rule, "is_enabled", True),
            )
        )
    return tuple(
        FrameworkSyncRuleSet(framework_type=framework_type, rules=tuple(rules))
        for framework_type, rules in sorted(framework_rules.items())
    )


def _read_sync_filter_type(raw_settings: dict[str, Any], *, key: str) -> SyncFilterType:
    raw_value = _read_string(raw_settings, "filter_type", "")
    try:
        return SyncFilterType(raw_value)
    except ValueError as error:
        msg = f"Unsupported sync filter type in {key}: {raw_value}"
        raise ControlledServiceError(msg) from error


def _read_sync_rule_behavior(raw_settings: dict[str, Any], *, key: str) -> SyncRuleBehavior:
    raw_value = _read_string(raw_settings, "behavior", "")
    try:
        return SyncRuleBehavior(raw_value)
    except ValueError as error:
        msg = f"Unsupported sync rule behavior in {key}: {raw_value}"
        raise ControlledServiceError(msg) from error


def _validate_sync_scope_settings(
    sync_scope_settings: AdapterSyncScopeSettings,
) -> AdapterSyncScopeSettings:
    validated_global_rules = tuple(
        _validate_configured_rule(rule, context="global sync rule")
        for rule in sync_scope_settings.global_rules
    )
    validated_framework_rule_sets: list[FrameworkSyncRuleSet] = []
    for rule_set in sync_scope_settings.framework_rule_sets:
        normalized_framework_type = rule_set.normalized_framework_type()
        if normalized_framework_type == "":
            msg = "Framework sync rules require a non-empty framework type."
            raise ControlledServiceError(msg)
        validated_framework_rule_sets.append(
            FrameworkSyncRuleSet(
                framework_type=normalized_framework_type,
                rules=tuple(
                    _validate_configured_rule(
                        rule,
                        context=f"framework sync rule for '{normalized_framework_type}'",
                    )
                    for rule in rule_set.rules
                ),
            )
        )
    return AdapterSyncScopeSettings(
        global_rules=validated_global_rules,
        framework_rule_sets=tuple(validated_framework_rule_sets),
        use_gitignore_rules=sync_scope_settings.use_gitignore_rules,
    )


def _validate_configured_rule(
    rule: ConfiguredSyncRule,
    *,
    context: str,
) -> ConfiguredSyncRule:
    normalized_relative_path = rule.relative_path.strip().strip("/")
    if normalized_relative_path == "":
        msg = f"{context.capitalize()} requires a non-empty relative path."
        raise ControlledServiceError(msg)
    normalized_description = rule.description.strip()
    if normalized_description == "":
        normalized_description = normalized_relative_path
    return ConfiguredSyncRule(
        relative_path=normalized_relative_path,
        filter_type=rule.filter_type,
        behavior=rule.behavior,
        description=normalized_description,
        is_enabled=rule.is_enabled,
    )


def _serialize_sync_scope_settings(sync_scope_settings: AdapterSyncScopeSettings) -> str:
    document = "\n[sync_scope]\n"
    document += (
        f"use_gitignore_rules = {_format_toml_bool(sync_scope_settings.use_gitignore_rules)}\n"
    )
    for rule in sync_scope_settings.global_rules:
        document += "\n[[sync_scope.global_rules]]\n"
        document += _serialize_configured_rule(rule)
    for rule_set in sync_scope_settings.framework_rule_sets:
        for rule in rule_set.rules:
            document += "\n[[sync_scope.framework_rules]]\n"
            document += (
                f"framework_type = {_format_toml_string(rule_set.normalized_framework_type())}\n"
            )
            document += _serialize_configured_rule(rule)
    return document


def _serialize_configured_rule(rule: ConfiguredSyncRule) -> str:
    return (
        f"relative_path = {_format_toml_string(rule.relative_path)}\n"
        f"filter_type = {_format_toml_string(rule.filter_type.value)}\n"
        f"behavior = {_format_toml_string(rule.behavior.value)}\n"
        f"description = {_format_toml_string(rule.description)}\n"
        f"is_enabled = {_format_toml_bool(rule.is_enabled)}\n"
    )
