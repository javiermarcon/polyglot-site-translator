"""Kivy application bootstrap."""

from __future__ import annotations

from typing import Any

from kivy.app import App
from kivy.core.window import Window

from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.root import build_root_widget
from polyglot_site_translator.presentation.kivy.theme import set_active_theme_mode
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    SettingsStateViewModel,
    build_default_app_settings,
    build_settings_state,
)


class PolyglotSiteTranslatorApp(App):  # type: ignore[misc]
    """Thin Kivy application wrapper around the presentation shell."""

    def __init__(self, shell: FrontendShell, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._shell = shell
        self._built_root: Any | None = None

    def build(self) -> Any:
        """Build the root widget tree."""
        self.title = "Polyglot Site Translator"
        self._open_initial_route()
        self._built_root = build_root_widget(self._shell, self.apply_runtime_settings)
        return self._built_root

    def apply_runtime_settings(self, app_settings: AppSettingsViewModel) -> None:
        """Apply runtime Kivy settings after a successful save."""
        set_active_theme_mode(app_settings.theme_mode)
        Window.size = (app_settings.window_width, app_settings.window_height)
        root = self.root or self._built_root
        if root is None:
            return
        for screen in root.screens:
            if hasattr(screen, "apply_theme"):
                screen.apply_theme()
        current_screen = root.current_screen
        if current_screen is not None:
            current_screen.refresh()

    def _open_initial_route(self) -> None:
        """Load persisted frontend settings before choosing the initial route."""
        state = self._load_startup_settings()
        if state is None:
            self._shell.open_dashboard()
            return
        self.apply_runtime_settings(state.app_settings)
        if not state.app_settings.remember_last_screen:
            self._shell.open_dashboard()
            return
        if state.app_settings.last_opened_screen == "settings":
            self._shell.open_settings()
            return
        if state.app_settings.last_opened_screen == "projects":
            self._shell.open_projects()
            return
        self._shell.open_dashboard()

    def _load_startup_settings(self) -> SettingsStateViewModel | None:
        """Load settings for startup without mutating remembered navigation first."""
        try:
            state = self._shell.services.settings.load_settings()
            self._shell.settings_state = state
            self._shell.latest_error = None
        except ControlledServiceError as error:
            state = build_settings_state(
                app_settings=build_default_app_settings(),
                status="failed",
                status_message=str(error),
            )
            self._shell.settings_state = state
            self._shell.latest_error = str(error)
        return self._shell.settings_state
