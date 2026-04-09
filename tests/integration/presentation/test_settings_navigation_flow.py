"""Integration tests for the settings navigation flow."""

from __future__ import annotations

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.presentation.router import RouteName
from tests.support.frontend_doubles import build_seeded_services


def test_dashboard_to_settings_and_back_keeps_saved_state() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_dashboard()
    shell.open_settings()
    shell.toggle_remember_last_screen()
    shell.save_settings()
    shell.open_dashboard()
    shell.open_settings()

    assert shell.router.current.name is RouteName.SETTINGS
    assert shell.settings_state is not None
    assert shell.settings_state.app_settings.remember_last_screen is True
