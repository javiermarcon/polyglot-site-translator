"""PO processing screen."""

from __future__ import annotations

from kivy.clock import Clock, ClockEvent
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.design_tokens import COMPONENT_SIZES
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.widgets.actions import (
    ActionIntent,
    ActionRow,
    build_action_button,
)
from polyglot_site_translator.presentation.kivy.widgets.common import WrappedLabel
from polyglot_site_translator.presentation.kivy.widgets.surfaces import (
    AppCard,
    StatusBanner,
    StatusTone,
    status_tone_from_workflow_status,
)
from polyglot_site_translator.presentation.ui_localization import tr


class POProcessingScreen(BaseShellScreen):
    """Screen showing PO processing workflow state.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        """Build the translation workflow screen and its progress widgets.

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
            screen_name="po_processing",
            title="Translation",
            subtitle=(
                "Project-scoped translation workflow summary and prepared "
                "locale families."
            ),
            shell=shell,
            manager_ref=manager_ref,
        )
        self._summary_label = WrappedLabel()
        self._progress_bar = ProgressBar(
            max=1,
            value=0,
            size_hint_y=None,
            height=COMPONENT_SIZES.progress_height,
        )
        self._refresh_event: ClockEvent | None = None
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
        """Refresh the progress bar and summary from translation workflow state.

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
            text=tr("Back to Project"),
            intent=ActionIntent.SECONDARY,
        )
        back_button.bind(on_release=self._back_to_project)
        actions.add_widget(back_button)
        self._content.add_widget(actions)

        state = self._shell.po_processing_state
        if state is None:
            self._progress_bar = ProgressBar(
                max=1,
                value=0,
                size_hint_y=None,
                height=COMPONENT_SIZES.progress_height,
            )
            self._summary_label = WrappedLabel(text="No translation action started.")
            self._content.add_widget(
                StatusBanner(
                    title=tr("Translation not started"),
                    body=tr("Run translation from the project detail screen."),
                    tone=StatusTone.EMPTY,
                )
            )
        else:
            progress_max = state.progress_total if state.progress_total > 0 else 1
            progress_value = state.progress_current
            if not state.progress_is_indeterminate and state.progress_total == 0:
                progress_value = 1
            current_file_line = ""
            if state.current_file is not None:
                current_file_line = f"Current file: {state.current_file}\n"
            current_entry_line = ""
            if state.current_entry is not None:
                current_entry_line = f"Current entry: {state.current_entry}\n"
            progress_bar = ProgressBar(
                max=progress_max,
                value=min(progress_value, progress_max),
                size_hint_y=None,
                height=COMPONENT_SIZES.progress_height,
            )
            self._progress_bar = progress_bar
            self._summary_label = WrappedLabel(
                text=(
                    f"Status: {state.status}\n"
                    f"Families: {state.processed_families}\n"
                    f"Progress: {state.progress_current}/{state.progress_total}\n"
                    "Completed entries: "
                    f"{state.progress_current}/{state.progress_total}\n"
                    f"{current_file_line}"
                    f"{current_entry_line}"
                    f"{state.summary}"
                ),
                font_size=15,
                color_role="text_muted",
            )
            self._content.add_widget(
                StatusBanner(
                    title=f"Translation {state.status}",
                    body=(
                        f"Families: {state.processed_families}\n"
                        "Completed entries: "
                        f"{state.progress_current}/{state.progress_total}"
                    ),
                    tone=status_tone_from_workflow_status(state.status),
                )
            )
            progress_card = AppCard()
            progress_card.add_widget(progress_bar)
            progress_card.add_widget(self._summary_label)
            self._content.add_widget(progress_card)
        self.update_error_label()
        if (
            state is not None
            and state.status == "running"
            and self._refresh_event is None
        ):
            self._refresh_event = Clock.schedule_interval(
                self._refresh_from_clock, 0.25
            )
        if (
            state is None or state.status != "running"
        ) and self._refresh_event is not None:
            self._refresh_event.cancel()
            self._refresh_event = None

    def _refresh_from_clock(self, _dt: float) -> None:
        """Refresh from clock.

        Args:
            self:
                Value supplied to this callable.
            _dt:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.refresh()

    def on_leave(self, *args: object) -> None:
        """Cancel the periodic refresh loop when the screen is left.

        Args:
            self:
                Value supplied to this callable.
            *args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().on_leave(*args)
        if self._refresh_event is not None:
            self._refresh_event.cancel()
            self._refresh_event = None
