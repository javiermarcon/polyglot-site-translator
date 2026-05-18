"""Projects list screen."""

from __future__ import annotations

from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.widgets.actions import (
    ActionIntent,
    ActionRow,
    build_action_button,
)
from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    WrappedLabel,
)
from polyglot_site_translator.presentation.kivy.widgets.surfaces import (
    AppCard,
    EmptyStatePanel,
    SectionHeader,
)
from polyglot_site_translator.presentation.ui_localization import tr


class ProjectsScreen(BaseShellScreen):
    """Screen showing registered projects.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        """Build the project list screen and its navigation actions.

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
            screen_name="projects",
            title="Projects",
            subtitle="Browse the managed sites and applications registry.",
            shell=shell,
            manager_ref=manager_ref,
        )
        self._list_label = WrappedLabel()
        self._project_buttons: list[AppButton] = []
        self.refresh()

    def _go_dashboard(self, *_args: object) -> None:
        """Handle go dashboard.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.open_dashboard()
        self.show_route("dashboard")

    def _open_project(self, project_id: str) -> None:
        """Open project.

        Args:
            self:
                Value supplied to this callable.
            project_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.select_project(project_id)
        self.show_route("project_detail")

    def _open_create_project(self, *_args: object) -> None:
        """Open create project.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.open_project_editor_create()
        self.show_route("project_editor")

    def refresh(self) -> None:
        """Refresh the visible project list from the catalog-backed shell state.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.clear_content()
        self._project_buttons = []
        actions = ActionRow()
        dashboard_button = build_action_button(
            text=tr("Back to Dashboard"),
            intent=ActionIntent.SECONDARY,
        )
        register_button = build_action_button(
            text=tr("Register Project"),
            intent=ActionIntent.PRIMARY,
        )
        dashboard_button.bind(on_release=self._go_dashboard)
        register_button.bind(on_release=self._open_create_project)
        actions.add_widget(dashboard_button)
        actions.add_widget(register_button)
        self._content.add_widget(actions)

        if self._shell.projects_state.projects:
            for project in self._shell.projects_state.projects:
                card = AppCard()
                card.add_widget(
                    SectionHeader(
                        title=f"{project.name} [{project.framework}]",
                        description=f"{project.local_path} ({project.status})",
                    )
                )
                button = build_action_button(
                    text=tr("Open {project_name}").format(project_name=project.name),
                    intent=ActionIntent.SECONDARY,
                )
                button.bind(
                    on_release=lambda *_args, pid=project.id: self._open_project(pid)
                )
                self._project_buttons.append(button)
                card.add_widget(button)
                self._content.add_widget(card)
        else:
            empty_panel = EmptyStatePanel(
                title=tr("No projects registered"),
                body=self._shell.projects_state.empty_message or "",
            )
            self._list_label = empty_panel.body_label
            self._content.add_widget(empty_panel)

        self.update_error_label()
