"""Unit tests for TOML-backed frontend settings persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

import polyglot_site_translator.infrastructure.settings as settings_module
from polyglot_site_translator.infrastructure.settings import (
    SETTINGS_FILENAME,
    TomlSettingsService,
    _resolve_posix_config_dir,
    _resolve_windows_config_dir,
    build_default_settings_service,
    resolve_user_config_dir,
)
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.view_models import AppSettingsViewModel

SETTINGS_MODULE = cast(Any, settings_module)


def test_load_settings_returns_defaults_when_file_does_not_exist(tmp_path: Path) -> None:
    service = TomlSettingsService(tmp_path / SETTINGS_FILENAME)

    settings_state = service.load_settings()

    assert settings_state.app_settings.theme_mode == "system"
    assert settings_state.app_settings.window_width == 1280
    assert settings_state.app_settings.last_opened_screen == "dashboard"


def test_save_settings_writes_toml_and_roundtrips_values(tmp_path: Path) -> None:
    settings_path = tmp_path / SETTINGS_FILENAME
    service = TomlSettingsService(settings_path)

    saved_state = service.save_settings(
        AppSettingsViewModel(
            theme_mode="dark",
            window_width=1440,
            window_height=900,
            remember_last_screen=True,
            last_opened_screen="settings",
            developer_mode=True,
            ui_language="es",
        )
    )

    reloaded_state = service.load_settings()

    assert saved_state.app_settings.last_opened_screen == "settings"
    assert reloaded_state.app_settings.theme_mode == "dark"
    assert reloaded_state.app_settings.window_width == 1440
    assert reloaded_state.app_settings.window_height == 900
    assert reloaded_state.app_settings.remember_last_screen is True
    assert reloaded_state.app_settings.last_opened_screen == "settings"
    assert reloaded_state.app_settings.developer_mode is True
    assert reloaded_state.app_settings.ui_language == "es"
    assert 'theme_mode = "dark"' in settings_path.read_text(encoding="utf-8")


def test_load_settings_rejects_invalid_toml_values(tmp_path: Path) -> None:
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text(
        '[app]\nwindow_width = 0\nlast_opened_screen = "dashboard"\n',
        encoding="utf-8",
    )
    service = TomlSettingsService(settings_path)

    with pytest.raises(
        ControlledServiceError,
        match=r"Window dimensions must be positive integers\.",
    ):
        service.load_settings()


def test_reset_settings_restores_defaults_and_persists_them(tmp_path: Path) -> None:
    service = TomlSettingsService(tmp_path / SETTINGS_FILENAME)
    service.save_settings(
        AppSettingsViewModel(
            theme_mode="dark",
            window_width=1440,
            window_height=900,
            remember_last_screen=True,
            last_opened_screen="settings",
            developer_mode=True,
            ui_language="es",
        )
    )

    reset_state = service.reset_settings()

    assert reset_state.status == "defaults-restored"
    assert reset_state.app_settings.theme_mode == "system"
    assert reset_state.app_settings.last_opened_screen == "dashboard"
    assert service.load_settings().app_settings.ui_language == "en"


def test_build_default_settings_service_uses_explicit_config_dir(tmp_path: Path) -> None:
    service = build_default_settings_service(config_dir=tmp_path)

    assert isinstance(service, TomlSettingsService)
    assert service.settings_path == tmp_path / SETTINGS_FILENAME


def test_load_settings_uses_defaults_for_empty_toml_document(tmp_path: Path) -> None:
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text("", encoding="utf-8")
    service = TomlSettingsService(settings_path)

    settings_state = service.load_settings()

    assert settings_state.app_settings.window_width == 1280
    assert settings_state.app_settings.ui_language == "en"


def test_load_settings_uses_defaults_when_app_table_is_missing(tmp_path: Path) -> None:
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text("[meta]\nschema_version = 1\n", encoding="utf-8")
    service = TomlSettingsService(settings_path)

    settings_state = service.load_settings()

    assert settings_state.app_settings.theme_mode == "system"


def test_load_settings_accepts_partial_app_table_and_fills_defaults(tmp_path: Path) -> None:
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text('[app]\ntheme_mode = "dark"\n', encoding="utf-8")
    service = TomlSettingsService(settings_path)

    settings_state = service.load_settings()

    assert settings_state.app_settings.theme_mode == "dark"
    assert settings_state.app_settings.window_width == 1280
    assert settings_state.app_settings.last_opened_screen == "dashboard"


def test_load_settings_rejects_invalid_toml_syntax(tmp_path: Path) -> None:
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text("[app\n", encoding="utf-8")
    service = TomlSettingsService(settings_path)

    with pytest.raises(ControlledServiceError, match=r"App settings contain invalid TOML"):
        service.load_settings()


@pytest.mark.parametrize(
    ("document", "expected_message"),
    [
        ("app = 3\n", r"The \[app\] settings section must be a TOML table\."),
        ("[app]\ntheme_mode = 3\n", r"The app setting 'theme_mode' must be a string\."),
        (
            '[app]\nwindow_width = "wide"\n',
            r"The app setting 'window_width' must be an integer\.",
        ),
        (
            '[app]\nremember_last_screen = "yes"\n',
            r"The app setting 'remember_last_screen' must be a boolean\.",
        ),
        ('[app]\ntheme_mode = "neon"\n', r"Unsupported theme mode: neon"),
        ('[app]\nui_language = "fr"\n', r"Unsupported UI language: fr"),
        (
            '[app]\nlast_opened_screen = "sync-preview"\n',
            r"Unsupported last opened screen: sync-preview",
        ),
    ],
)
def test_load_settings_rejects_invalid_values(
    tmp_path: Path,
    document: str,
    expected_message: str,
) -> None:
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text(document, encoding="utf-8")
    service = TomlSettingsService(settings_path)

    with pytest.raises(ControlledServiceError, match=expected_message):
        service.load_settings()


def test_load_settings_wraps_os_errors_from_reading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings_path = tmp_path / SETTINGS_FILENAME
    settings_path.write_text('[app]\ntheme_mode = "dark"\n', encoding="utf-8")
    service = TomlSettingsService(settings_path)

    def fail_read_text(_self: Path, *, encoding: str) -> str:
        msg = "boom"
        raise OSError(msg)

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    with pytest.raises(ControlledServiceError, match=r"App settings could not be loaded from"):
        service.load_settings()


def test_save_settings_wraps_os_errors_from_writing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    service = TomlSettingsService(tmp_path / SETTINGS_FILENAME)

    def fail_write_text(_self: Path, _content: str, *, encoding: str) -> int:
        msg = "boom"
        raise OSError(msg)

    monkeypatch.setattr(Path, "write_text", fail_write_text)

    with pytest.raises(ControlledServiceError, match=r"App settings could not be saved to"):
        service.save_settings(_custom_settings())


def test_resolve_user_config_dir_prefers_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(settings_module.CONFIG_DIR_ENV_VAR, "~/custom-config")

    assert resolve_user_config_dir() == Path("~/custom-config").expanduser()


def test_resolve_windows_config_dir_uses_appdata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPDATA", "/tmp/appdata")

    assert _resolve_windows_config_dir() == Path("/tmp/appdata/polyglot-site-translator")


def test_resolve_windows_config_dir_uses_fallback_when_appdata_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.Path, "home", lambda: Path("/home/tester"))

    assert _resolve_windows_config_dir() == Path(
        "/home/tester/AppData/Roaming/polyglot-site-translator"
    )


def test_resolve_user_config_dir_uses_darwin_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(settings_module.CONFIG_DIR_ENV_VAR, raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.os, "name", "posix", raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.sys, "platform", "darwin", raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.Path, "home", lambda: Path("/Users/tester"))

    assert resolve_user_config_dir() == Path(
        "/Users/tester/Library/Application Support/polyglot-site-translator"
    )


def test_resolve_user_config_dir_uses_xdg_config_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/xdg")

    assert _resolve_posix_config_dir() == Path("/tmp/xdg/polyglot-site-translator")


def test_resolve_posix_config_dir_uses_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(SETTINGS_MODULE.Path, "home", lambda: Path("/home/tester"))

    assert _resolve_posix_config_dir() == Path("/home/tester/.config/polyglot-site-translator")


def _custom_settings() -> AppSettingsViewModel:
    return AppSettingsViewModel(
        theme_mode="dark",
        window_width=1440,
        window_height=900,
        remember_last_screen=True,
        last_opened_screen="settings",
        developer_mode=True,
        ui_language="es",
    )
