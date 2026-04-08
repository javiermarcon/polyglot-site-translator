"""TOML-backed frontend settings persistence."""

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import tomllib
from typing import Any

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
    try:
        database_directory = str(validate_database_directory(app_settings.database_directory))
        database_filename = normalize_database_filename(app_settings.database_filename)
    except ValueError as error:
        raise ControlledServiceError(str(error)) from error
    return replace(
        app_settings,
        database_directory=database_directory,
        database_filename=database_filename,
    )


def _serialize_settings_document(app_settings: AppSettingsViewModel) -> str:
    return (
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
    )


def _format_toml_string(value: str) -> str:
    return json.dumps(value)


def _format_toml_bool(value: bool) -> str:
    if value:
        return "true"
    return "false"
