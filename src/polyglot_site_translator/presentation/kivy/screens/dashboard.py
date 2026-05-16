"""Dashboard screen."""

from __future__ import annotations

from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.widgets.actions import (
    ActionIntent,
    ActionRow,
    build_action_button,
)


class DashboardScreen(BaseShellScreen):
    """Entry screen for the application shell.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        """Build the dashboard actions and descriptive overview labels.

        Args:
            self:
                Value supplied to this callable.
            shell:
                Value supplied to this callable.
            manager_ref:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(
            screen_name="dashboard",
            title="Dashboard",
            subtitle=(
                "Main entry point for projects, operations and system configuration."
            ),
            shell=shell,
            manager_ref=manager_ref,
        )
        self.refresh()

    def _open_projects(self, *_args: object) -> None:
        """Open projects.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.open_projects()
        self.show_route("projects")

    def _open_settings(self, *_args: object) -> None:
        """Open settings.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.open_settings()
        self.show_route("settings")

    def refresh(self) -> None:
        """Refresh dashboard copy from the current shell state.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.clear_content()
        actions = ActionRow()
        projects_button = build_action_button(
            text="Open Projects",
            intent=ActionIntent.PRIMARY,
        )
        settings_button = build_action_button(
            text="Open Settings",
            intent=ActionIntent.SECONDARY,
        )
        projects_button.bind(on_release=self._open_projects)
        settings_button.bind(on_release=self._open_settings)
        actions.add_widget(projects_button)
        actions.add_widget(settings_button)
        self._content.add_widget(actions)
        self.update_error_label()
