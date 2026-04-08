"""Integration tests for the application entrypoint wiring."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.infrastructure.settings import TomlSettingsService
from polyglot_site_translator.presentation.fakes import (
    build_seeded_services,
    build_seeded_services_with_settings,
)
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
        "project_editor",
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
            last_opened_screen="dashboard",
            developer_mode=False,
            ui_language="en",
        )
    )

    assert get_active_theme_mode() == "dark"


def test_create_kivy_app_uses_toml_settings_service_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("POLYGLOT_SITE_TRANSLATOR_CONFIG_DIR", str(tmp_path))

    app = cast(Any, create_kivy_app())

    assert isinstance(app._shell.services.settings, TomlSettingsService)
    assert app._shell.services.settings.settings_path == tmp_path / "settings.toml"


def test_build_uses_persisted_settings_as_initial_runtime_state(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.save_settings(
        AppSettingsViewModel(
            theme_mode="dark",
            window_width=1440,
            window_height=900,
            remember_last_screen=True,
            last_opened_screen="settings",
            developer_mode=False,
            ui_language="en",
        )
    )
    app = cast(
        Any,
        create_kivy_app(services=build_seeded_services_with_settings(settings_service)),
    )

    root = app.build()

    assert root.current == "settings"
    assert get_active_theme_mode() == "dark"


def test_navigation_updates_the_persisted_last_opened_screen(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.save_settings(
        AppSettingsViewModel(
            theme_mode="dark",
            window_width=1440,
            window_height=900,
            remember_last_screen=True,
            last_opened_screen="dashboard",
            developer_mode=False,
            ui_language="en",
        )
    )
    shell = create_frontend_shell(build_seeded_services_with_settings(settings_service))

    shell.open_settings()
    shell.open_projects()

    assert settings_service.load_settings().app_settings.last_opened_screen == "projects"


def test_build_falls_back_to_dashboard_when_startup_keeps_no_settings_state() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)

    def clear_settings_state() -> None:
        shell.settings_state = None

    cast(Any, shell).open_settings = clear_settings_state

    root = app.build()

    assert root.current == "dashboard"


def test_build_returns_to_dashboard_when_remember_last_screen_is_disabled(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.save_settings(
        AppSettingsViewModel(
            theme_mode="dark",
            window_width=1440,
            window_height=900,
            remember_last_screen=False,
            last_opened_screen="settings",
            developer_mode=False,
            ui_language="en",
        )
    )
    app = cast(
        Any,
        create_kivy_app(services=build_seeded_services_with_settings(settings_service)),
    )

    root = app.build()

    assert root.current == "dashboard"


def test_build_returns_to_dashboard_for_unsupported_safe_start_route(
    tmp_path: Path,
) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.save_settings(
        AppSettingsViewModel(
            theme_mode="dark",
            window_width=1440,
            window_height=900,
            remember_last_screen=True,
            last_opened_screen="dashboard",
            developer_mode=False,
            ui_language="en",
        )
    )
    app = cast(
        Any,
        create_kivy_app(services=build_seeded_services_with_settings(settings_service)),
    )

    root = app.build()

    assert root.current == "dashboard"


def test_build_uses_projects_when_the_last_screen_is_projects(tmp_path: Path) -> None:
    settings_service = TomlSettingsService(tmp_path / "settings.toml")
    settings_service.save_settings(
        AppSettingsViewModel(
            theme_mode="dark",
            window_width=1440,
            window_height=900,
            remember_last_screen=True,
            last_opened_screen="projects",
            developer_mode=False,
            ui_language="en",
        )
    )
    app = cast(
        Any,
        create_kivy_app(services=build_seeded_services_with_settings(settings_service)),
    )

    root = app.build()

    assert root.current == "projects"
