"""Settings screen."""

from __future__ import annotations

from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen


class SettingsScreen(BaseShellScreen):
    """Screen showing the extensible frontend settings area."""

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        super().__init__(
            screen_name="settings",
            title="Settings",
            shell=shell,
            manager_ref=manager_ref,
        )
        self.add_nav_button("Back to Dashboard", self._back_to_dashboard)
        self.add_nav_button("Theme: Dark", self._set_dark_theme)
        self.add_nav_button("Theme: Light", self._set_light_theme)
        self.add_nav_button("Toggle Remember Last Screen", self._toggle_remember_last_screen)
        self.add_nav_button("Toggle Developer Mode", self._toggle_developer_mode)
        self.add_nav_button("Preset: 1440x900", self._set_large_window)
        self.add_nav_button("Apply Settings", self._apply_settings)
        self.add_nav_button("Restore Defaults", self._restore_defaults)
        self._summary_label = Label(halign="left", valign="top")
        self._content.add_widget(self._summary_label)
        self.refresh()

    def _back_to_dashboard(self, *_args: object) -> None:
        self._shell.open_dashboard()
        self.show_route("dashboard")

    def _set_dark_theme(self, *_args: object) -> None:
        self._shell.set_settings_theme_mode("dark")
        self.refresh()

    def _set_light_theme(self, *_args: object) -> None:
        self._shell.set_settings_theme_mode("light")
        self.refresh()

    def _toggle_remember_last_screen(self, *_args: object) -> None:
        self._shell.toggle_remember_last_screen()
        self.refresh()

    def _toggle_developer_mode(self, *_args: object) -> None:
        self._shell.toggle_developer_mode()
        self.refresh()

    def _set_large_window(self, *_args: object) -> None:
        self._shell.set_settings_window_size(width=1440, height=900)
        self.refresh()

    def _apply_settings(self, *_args: object) -> None:
        self._shell.save_settings()
        self.show_route("settings")

    def _restore_defaults(self, *_args: object) -> None:
        self._shell.restore_default_settings()
        self.show_route("settings")

    def refresh(self) -> None:
        state = self._shell.settings_state
        if state is None:
            self._summary_label.text = "Settings are not loaded yet."
        else:
            sections = "\n".join(
                f"{section.title} ({'available' if section.is_available else 'planned'})"
                for section in state.sections
            )
            app_settings = state.app_settings
            self._summary_label.text = (
                f"Sections:\n{sections}\n\n"
                f"Theme: {app_settings.theme_mode}\n"
                f"Window: {app_settings.window_width}x{app_settings.window_height}\n"
                f"Remember Last Screen: {app_settings.remember_last_screen}\n"
                f"Developer Mode: {app_settings.developer_mode}\n"
                f"UI Language: {app_settings.ui_language}\n"
                f"Status: {state.status}\n"
                f"{state.status_message or ''}"
            )
        self.update_error_label()
