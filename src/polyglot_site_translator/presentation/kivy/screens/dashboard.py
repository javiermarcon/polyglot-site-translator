"""Dashboard screen."""

from __future__ import annotations

from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen


class DashboardScreen(BaseShellScreen):
    """Entry screen for the application shell."""

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        super().__init__(
            screen_name="dashboard",
            title="Dashboard",
            shell=shell,
            manager_ref=manager_ref,
        )
        self.add_nav_button("Open Projects", self._open_projects)
        self.add_nav_button("Open Settings", self._open_settings)
        self._sections_label = Label(halign="left", valign="top")
        self._content.add_widget(self._sections_label)
        self.refresh()

    def _open_projects(self, *_args: object) -> None:
        self._shell.open_projects()
        self.show_route("projects")

    def _open_settings(self, *_args: object) -> None:
        self._shell.open_settings()
        self.show_route("settings")

    def refresh(self) -> None:
        self._sections_label.text = "\n".join(
            f"{section.title}: {section.description}"
            for section in self._shell.dashboard_state.sections
        )
        self.update_error_label()
