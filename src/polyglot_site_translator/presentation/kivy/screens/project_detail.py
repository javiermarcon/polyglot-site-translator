"""Project detail screen."""

from __future__ import annotations

from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.widgets.common import WrappedLabel
from polyglot_site_translator.presentation.kivy.widgets.sync_progress_popup import (
    SyncProgressPopup,
)


class ProjectDetailScreen(BaseShellScreen):
    """Screen showing project details and workflow actions."""

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
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
        self.add_nav_button("Run Audit", self._start_audit)
        self.add_nav_button("Process PO", self._start_po_processing)
        self._detail_label = WrappedLabel(font_size=15)
        self._sync_progress_popup: SyncProgressPopup | None = None
        self._content.add_widget(self._detail_label)
        self.refresh()

    def _back_to_projects(self, *_args: object) -> None:
        self._shell.open_projects()
        self.show_route("projects")

    def _start_sync(self, *_args: object) -> None:
        self._shell.start_sync_async()
        if self._sync_progress_popup is None:
            self._sync_progress_popup = SyncProgressPopup(shell=self._shell)
        self._sync_progress_popup.open_for_sync()

    def _start_audit(self, *_args: object) -> None:
        self._shell.start_audit()
        self.show_route("audit")

    def _start_po_processing(self, *_args: object) -> None:
        self._shell.start_po_processing()
        self.show_route("po_processing")

    def _edit_project(self, *_args: object) -> None:
        detail = self._shell.project_detail_state
        if detail is None:
            return
        self._shell.open_project_editor_edit(detail.project.id)
        self.show_route("project_editor")

    def refresh(self) -> None:
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
