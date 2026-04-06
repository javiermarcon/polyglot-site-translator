"""Unit tests for frontend settings orchestration."""

from __future__ import annotations

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.presentation.fakes import (
    build_failing_settings_load_services,
    build_failing_settings_save_services,
    build_seeded_services,
)
from polyglot_site_translator.presentation.router import RouteName


def test_open_settings_loads_sections_and_defaults() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_settings()

    assert shell.router.current.name is RouteName.SETTINGS
    assert shell.settings_state is not None
    assert shell.settings_state.selected_section_key == "app-ui-kivy"
    assert shell.settings_state.app_settings.window_width == 1280
    assert shell.settings_state.app_settings.remember_last_screen is False
    assert shell.settings_state.theme_mode_field.control_type == "choice"
    assert [option.value for option in shell.settings_state.theme_mode_field.options] == [
        "system",
        "light",
        "dark",
    ]
    assert shell.settings_state.theme_mode_field.help_text != ""


def test_selecting_planned_settings_section_updates_context() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_settings()
    shell.select_settings_section("translation")

    assert shell.settings_state is not None
    assert shell.settings_state.selected_section_key == "translation"
    assert shell.settings_state.status_message == "Translation Settings will be available later."


def test_update_and_save_settings_persists_fake_state() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_settings()
    shell.set_settings_theme_mode("dark")
    shell.toggle_remember_last_screen()
    shell.toggle_developer_mode()
    shell.set_settings_window_size(width=1440, height=900)
    shell.save_settings()

    assert shell.settings_state is not None
    assert shell.settings_state.status == "saved"

    shell.open_settings()

    assert shell.settings_state is not None
    assert shell.settings_state.app_settings.theme_mode == "dark"
    assert shell.settings_state.app_settings.remember_last_screen is True
    assert shell.settings_state.app_settings.developer_mode is True
    assert shell.settings_state.app_settings.window_width == 1440
    assert shell.settings_state.app_settings.window_height == 900
    assert shell.settings_state.status == "loaded"


def test_restore_defaults_uses_settings_service() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_settings()
    shell.toggle_remember_last_screen()
    shell.set_settings_window_size(width=1440, height=900)
    shell.save_settings()
    shell.restore_default_settings()

    assert shell.settings_state is not None
    assert shell.settings_state.app_settings.window_width == 1280
    assert shell.settings_state.app_settings.window_height == 720
    assert shell.settings_state.app_settings.remember_last_screen is False
    assert shell.settings_state.status == "defaults-restored"


def test_settings_load_failure_is_exposed() -> None:
    shell = create_frontend_shell(build_failing_settings_load_services())

    shell.open_settings()

    assert shell.settings_state is not None
    assert shell.settings_state.status == "failed"
    assert shell.latest_error == "App settings are temporarily unavailable."


def test_settings_save_failure_keeps_error_state() -> None:
    shell = create_frontend_shell(build_failing_settings_save_services())

    shell.open_settings()
    shell.toggle_remember_last_screen()
    shell.save_settings()

    assert shell.settings_state is not None
    assert shell.settings_state.status == "failed"
    assert shell.latest_error == "App settings could not be saved."
