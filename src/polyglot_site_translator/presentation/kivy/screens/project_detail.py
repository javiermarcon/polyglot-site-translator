"""Project detail screen."""

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
    AppCard,
    EmptyStatePanel,
    SectionHeader,
)
from polyglot_site_translator.presentation.ui_localization import tr
from polyglot_site_translator.presentation.view_models import (
    TranslationWorkflowRequestViewModel,
)

from ..widgets.po_locale_selection_popup import POLocaleSelectionPopup
from ..widgets.sync_progress_popup import SyncProgressPopup


class ProjectDetailScreen(BaseShellScreen):
    """Screen showing project details and workflow actions.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        """Build project actions, summary labels, and workflow popups.

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
            screen_name="project_detail",
            title="Project Detail",
            subtitle="Contextual actions for the currently selected project.",
            shell=shell,
            manager_ref=manager_ref,
        )
        self._sync_progress_popup: SyncProgressPopup | None = None
        self._po_locale_popup: POLocaleSelectionPopup | None = None
        self._detail_label = WrappedLabel()
        self.refresh()

    @property
    def sync_progress_popup(self) -> SyncProgressPopup | None:
        """Return the sync progress popup managed by this screen.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                The popup instance when a sync workflow opened it, otherwise
                ``None``.
        """
        return self._sync_progress_popup

    def clear_sync_progress_popup(self) -> None:
        """Clear the managed sync progress popup reference.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._sync_progress_popup = None

    def _back_to_projects(self, *_args: object) -> None:
        """Handle back to projects.

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

    def _start_sync(self, *_args: object) -> None:
        """Handle start sync.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.start_sync_async()
        if self._sync_progress_popup is None:
            self._sync_progress_popup = SyncProgressPopup(shell=self._shell)
        self._sync_progress_popup.open_for_sync()

    def _start_sync_to_remote(self, *_args: object) -> None:
        """Handle start sync to remote.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.start_sync_to_remote_async()
        if self._sync_progress_popup is None:
            self._sync_progress_popup = SyncProgressPopup(shell=self._shell)
        self._sync_progress_popup.open_for_sync()

    def _start_audit(self, *_args: object) -> None:
        """Handle start audit.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.start_audit()
        self.show_route("audit")

    def _start_po_processing(self, *_args: object) -> None:
        """Handle start po processing.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
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
            self:
                Value supplied to this callable.
            request:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.start_po_processing_async(
            request.locales,
            options=request.options,
        )
        self.show_route("po_processing")

    def _edit_project(self, *_args: object) -> None:
        """Handle edit project.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        detail = self._shell.project_detail_state
        if detail is None:
            return
        self._shell.open_project_editor_edit(detail.project.id)
        self.show_route("project_editor")

    def refresh(self) -> None:
        """Refresh the detail summary from the selected project state.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.clear_content()
        detail = self._shell.project_detail_state
        if detail is None:
            empty_panel = EmptyStatePanel(
                title=tr("No project selected"),
                body=tr("Choose a project from the registry before running workflows."),
            )
            self._detail_label = WrappedLabel(text=f"{tr('No project selected')}.")
            self._content.add_widget(empty_panel)
        else:
            nav_actions = ActionRow()
            back_button = build_action_button(
                text=tr("Back to Projects"),
                intent=ActionIntent.SECONDARY,
            )
            edit_button = build_action_button(
                text=tr("Edit Project"),
                intent=ActionIntent.SECONDARY,
            )
            back_button.bind(on_release=self._back_to_projects)
            edit_button.bind(on_release=self._edit_project)
            nav_actions.add_widget(back_button)
            nav_actions.add_widget(edit_button)
            self._content.add_widget(nav_actions)

            workflow_actions = ActionRow()
            sync_button = build_action_button(text=tr("Sync Remote to Local"))
            upload_button = build_action_button(
                text=tr("Sync Local to Remote"),
                intent=ActionIntent.SECONDARY,
            )
            audit_button = build_action_button(
                text=tr("Run Audit"),
                intent=ActionIntent.SECONDARY,
            )
            translate_button = build_action_button(text=tr("Translate"))
            sync_button.bind(on_release=self._start_sync)
            upload_button.bind(on_release=self._start_sync_to_remote)
            audit_button.bind(on_release=self._start_audit)
            translate_button.bind(on_release=self._start_po_processing)
            workflow_actions.add_widget(sync_button)
            workflow_actions.add_widget(upload_button)
            workflow_actions.add_widget(audit_button)
            workflow_actions.add_widget(translate_button)
            self._content.add_widget(workflow_actions)

            action_labels = ", ".join(tr(action.label) for action in detail.actions)
            action_line = f"\nActions: {action_labels}" if action_labels else ""
            detail_card = AppCard()
            detail_card.add_widget(
                SectionHeader(
                    title=f"{detail.project.name} [{detail.project.framework}]",
                    description=detail.metadata_summary,
                )
            )
            self._detail_label = WrappedLabel(
                text=(
                    f"{detail.project.name} [{detail.project.framework}]\n"
                    f"{detail.metadata_summary}\n"
                    f"{detail.configuration_summary}"
                    f"{action_line}"
                ),
                font_size=15,
            )
            detail_card.add_widget(
                WrappedLabel(
                    text=detail.configuration_summary,
                    font_size=15,
                    color_role="text_muted",
                )
            )
            if action_labels:
                detail_card.add_widget(
                    WrappedLabel(
                        text=tr("Available actions: {actions}").format(
                            actions=action_labels
                        ),
                        font_size=15,
                    )
                )
            self._content.add_widget(detail_card)
        self.update_error_label()
