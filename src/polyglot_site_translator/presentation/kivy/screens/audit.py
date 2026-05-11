"""Audit screen."""

from __future__ import annotations

from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.widgets.common import WrappedLabel


class AuditScreen(BaseShellScreen):
    """Screen showing audit workflow state.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        """Build the audit summary screen and its navigation actions.

        Args:
            shell (FrontendShell): Value supplied to this callable.
            manager_ref (ScreenManager): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        super().__init__(
            screen_name="audit",
            title="Audit",
            subtitle="Project-scoped audit overview and normalized findings summary.",
            shell=shell,
            manager_ref=manager_ref,
        )
        self.add_nav_button("Back to Project", self._back_to_project)
        self._summary_label = WrappedLabel(font_size=15)
        self._content.add_widget(self._summary_label)
        self.refresh()

    def _back_to_project(self, *_args: object) -> None:
        """Handle back to project.

        Args:
            _args (object): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        if self._shell.project_detail_state is not None:
            self._shell.select_project(self._shell.project_detail_state.project.id)
        self.show_route("project_detail")

    def refresh(self) -> None:
        """Refresh the audit summary from the latest workflow state.

        Returns:
            None: This callable does not return a value.
        """
        state = self._shell.audit_state
        if state is None:
            self._summary_label.text = "No audit action started."
        else:
            self._summary_label.text = (
                f"Status: {state.status}\nFindings: {state.findings_count}\n"
                f"{state.findings_summary}"
            )
        self.update_error_label()
