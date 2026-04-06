"""Projects list screen."""

from __future__ import annotations

from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.widgets.common import AppButton, WrappedLabel


class ProjectsScreen(BaseShellScreen):
    """Screen showing registered projects."""

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        super().__init__(
            screen_name="projects",
            title="Projects",
            subtitle="Browse the managed sites and applications registry.",
            shell=shell,
            manager_ref=manager_ref,
        )
        self.add_nav_button("Back to Dashboard", self._go_dashboard)
        self._list_label = WrappedLabel(font_size=15)
        self._content.add_widget(self._list_label)
        self._project_buttons: list[AppButton] = []
        self.refresh()

    def _go_dashboard(self, *_args: object) -> None:
        self._shell.open_dashboard()
        self.show_route("dashboard")

    def _open_project(self, project_id: str) -> None:
        self._shell.select_project(project_id)
        self.show_route("project_detail")

    def refresh(self) -> None:
        for button in self._project_buttons:
            self._content.remove_widget(button)
        self._project_buttons = []

        if self._shell.projects_state.projects:
            self._list_label.text = "\n".join(
                (f"{project.name} [{project.framework}] {project.local_path} ({project.status})")
                for project in self._shell.projects_state.projects
            )
            for project in self._shell.projects_state.projects:
                button = AppButton(
                    text=f"Open {project.name}",
                    primary=False,
                )
                button.bind(on_release=lambda *_args, pid=project.id: self._open_project(pid))
                self._project_buttons.append(button)
                self._content.add_widget(button)
        else:
            self._list_label.text = self._shell.projects_state.empty_message or ""

        self.update_error_label()
