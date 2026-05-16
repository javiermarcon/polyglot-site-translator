"""Sync screen."""

from __future__ import annotations

from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.widgets.actions import (
    ActionIntent,
    ActionRow,
    build_action_button,
)
from polyglot_site_translator.presentation.kivy.widgets.common import WrappedLabel
from polyglot_site_translator.presentation.kivy.widgets.surfaces import (
    StatusBanner,
    StatusTone,
    status_tone_from_workflow_status,
)


class SyncScreen(BaseShellScreen):
    """Screen showing sync workflow state.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        """Build the sync summary screen and its back-navigation action.

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
            screen_name="sync",
            title="Sync",
            subtitle="Project-scoped synchronization preview and status.",
            shell=shell,
            manager_ref=manager_ref,
        )
        self._summary_label = WrappedLabel()
        self.refresh()

    def _back_to_project(self, *_args: object) -> None:
        """Handle back to project.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if self._shell.project_detail_state is not None:
            self._shell.select_project(self._shell.project_detail_state.project.id)
        self.show_route("project_detail")

    def refresh(self) -> None:
        """Refresh the sync summary from the latest workflow state.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.clear_content()
        actions = ActionRow()
        back_button = build_action_button(
            text="Back to Project",
            intent=ActionIntent.SECONDARY,
        )
        back_button.bind(on_release=self._back_to_project)
        actions.add_widget(back_button)
        self._content.add_widget(actions)

        state = self._shell.sync_state
        if state is None:
            self._summary_label = WrappedLabel(text="No sync action started.")
            self._content.add_widget(
                StatusBanner(
                    title="Sync not started",
                    body="Start a sync workflow from the project detail screen.",
                    tone=StatusTone.EMPTY,
                )
            )
        else:
            summary_lines = [
                f"Files: {state.files_synced}",
            ]
            if state.error_code is not None:
                summary_lines.append(f"Error Code: {state.error_code}")
            summary_lines.append(state.summary)
            self._summary_label = WrappedLabel(
                text=f"Status: {state.status}\n" + "\n".join(summary_lines)
            )
            self._content.add_widget(
                StatusBanner(
                    title=f"Sync {state.status}",
                    body="\n".join(summary_lines),
                    tone=status_tone_from_workflow_status(state.status),
                )
            )
        self.update_error_label()
