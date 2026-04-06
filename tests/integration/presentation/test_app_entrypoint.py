"""Integration tests for the application entrypoint wiring."""

from __future__ import annotations

from typing import Any, cast

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.presentation.fakes import build_seeded_services
from polyglot_site_translator.presentation.kivy.app import PolyglotSiteTranslatorApp
from polyglot_site_translator.presentation.kivy.theme import get_active_theme_mode
from polyglot_site_translator.presentation.view_models import AppSettingsViewModel


def test_create_kivy_app_builds_root_with_expected_screens() -> None:
    app = cast(Any, create_kivy_app())

    root = app.build()

    assert root.current == "dashboard"
    assert [screen.name for screen in root.screens] == [
        "dashboard",
        "projects",
        "project_detail",
        "sync",
        "audit",
        "po_processing",
        "settings",
    ]


def test_apply_runtime_settings_without_built_root_still_updates_theme_mode() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)

    app.apply_runtime_settings(
        AppSettingsViewModel(
            theme_mode="dark",
            window_width=1440,
            window_height=900,
            remember_last_screen=False,
            developer_mode=False,
            ui_language="en",
        )
    )

    assert get_active_theme_mode() == "dark"
