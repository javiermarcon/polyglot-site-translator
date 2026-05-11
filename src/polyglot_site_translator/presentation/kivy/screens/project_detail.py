"""Project detail screen."""

from __future__ import annotations

from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.widgets.common import WrappedLabel
from polyglot_site_translator.presentation.kivy.widgets.po_locale_selection_popup import (
    POLocaleSelectionPopup,
)
from polyglot_site_translator.presentation.kivy.widgets.sync_progress_popup import (
    SyncProgressPopup,
)
from polyglot_site_translator.presentation.view_models import (
    TranslationWorkflowRequestViewModel,
)


class ProjectDetailScreen(BaseShellScreen):
    """Screen showing project details and workflow actions.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        """Build project actions, summary labels, and workflow popups.

        Args:
            shell (FrontendShell): Value supplied to this callable.
            manager_ref (ScreenManager): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        super().__init__(
            screen_name="project_detail",
            title="Project Detail",
            subtitle="Contextual actions for the currently selected project.",
            shell=shell,
            manager_ref=manager_ref,
        )
        self.add_nav_button("Back to Projects", self._back_to_projects)
        self.add_nav_button("Edit Project", self._edit_project, primary=False)
        self.add_nav_button("Sync Remote", self._start_sync)
        self.add_nav_button("Sync Local to Remote", self._start_sync_to_remote)
        self.add_nav_button("Run Audit", self._start_audit)
        self.add_nav_button("Translate", self._start_po_processing)
        self._detail_label = WrappedLabel(font_size=15)
        self._sync_progress_popup: SyncProgressPopup | None = None
        self._po_locale_popup: POLocaleSelectionPopup | None = None
        self._content.add_widget(self._detail_label)
        self.refresh()

    def _back_to_projects(self, *_args: object) -> None:
        """Handle back to projects.

        Args:
            _args (object): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        self._shell.open_projects()
        self.show_route("projects")

    def _start_sync(self, *_args: object) -> None:
        """Handle start sync.

        Args:
            _args (object): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        self._shell.start_sync_async()
        if self._sync_progress_popup is None:
            self._sync_progress_popup = SyncProgressPopup(shell=self._shell)
        self._sync_progress_popup.open_for_sync()

    def _start_sync_to_remote(self, *_args: object) -> None:
        """Handle start sync to remote.

        Args:
            _args (object): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        self._shell.start_sync_to_remote_async()
        if self._sync_progress_popup is None:
            self._sync_progress_popup = SyncProgressPopup(shell=self._shell)
        self._sync_progress_popup.open_for_sync()

    def _start_audit(self, *_args: object) -> None:
        """Handle start audit.

        Args:
            _args (object): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        self._shell.start_audit()
        self.show_route("audit")

    def _start_po_processing(self, *_args: object) -> None:
        """Handle start po processing.

        Args:
            _args (object): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        detail = self._shell.project_detail_state
        if detail is None:
            return
        self._po_locale_popup = POLocaleSelectionPopup(
            default_locales=detail.default_locale,
            default_options=detail.translation_options,
            on_confirm=self._confirm_po_processing,
        )
        self._po_locale_popup.open()

    def _confirm_po_processing(
        self,
        request: TranslationWorkflowRequestViewModel,
    ) -> None:
        """Handle confirm po processing.

        Args:
            request (TranslationWorkflowRequestViewModel): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        self._shell.start_po_processing_async(
            request.locales,
            options=request.options,
        )
        self.show_route("po_processing")

    def _edit_project(self, *_args: object) -> None:
        """Handle edit project.

        Args:
            _args (object): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        detail = self._shell.project_detail_state
        if detail is None:
            return
        self._shell.open_project_editor_edit(detail.project.id)
        self.show_route("project_editor")

    def refresh(self) -> None:
        """Refresh the detail summary from the selected project state.

        Returns:
            None: This callable does not return a value.
        """
        detail = self._shell.project_detail_state
        if detail is None:
            self._detail_label.text = "No project selected."
        else:
            actions = ", ".join(action.label for action in detail.actions)
            self._detail_label.text = (
                f"{detail.project.name} [{detail.project.framework}]\n"
                f"{detail.metadata_summary}\n"
                f"{detail.configuration_summary}\n"
                f"Actions: {actions}"
            )
        self.update_error_label()
