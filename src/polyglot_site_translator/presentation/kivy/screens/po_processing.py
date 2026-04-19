"""PO processing screen."""

from __future__ import annotations

from kivy.clock import Clock, ClockEvent
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.widgets.common import WrappedLabel


class POProcessingScreen(BaseShellScreen):
    """Screen showing PO processing workflow state."""

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        super().__init__(
            screen_name="po_processing",
            title="PO Processing",
            subtitle="Project-scoped PO workflow summary and prepared locale families.",
            shell=shell,
            manager_ref=manager_ref,
        )
        self.add_nav_button("Back to Project", self._back_to_project)
        self._summary_label = WrappedLabel(font_size=15)
        self._progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=20)
        self._refresh_event: ClockEvent | None = None
        self._content.add_widget(self._progress_bar)
        self._content.add_widget(self._summary_label)
        self.refresh()

    def _back_to_project(self, *_args: object) -> None:
        if self._shell.project_detail_state is not None:
            self._shell.select_project(self._shell.project_detail_state.project.id)
        self.show_route("project_detail")

    def refresh(self) -> None:
        state = self._shell.po_processing_state
        if state is None:
            self._progress_bar.max = 1
            self._progress_bar.value = 0
            self._summary_label.text = "No PO processing action started."
        else:
            progress_max = state.progress_total if state.progress_total > 0 else 1
            progress_value = state.progress_current
            if not state.progress_is_indeterminate and state.progress_total == 0:
                progress_value = 1
            self._progress_bar.max = progress_max
            self._progress_bar.value = min(progress_value, progress_max)
            self._summary_label.text = (
                f"Status: {state.status}\n"
                f"Families: {state.processed_families}\n"
                f"Progress: {state.progress_current}/{state.progress_total}\n"
                f"Completed entries: {state.progress_current}/{state.progress_total}\n"
                f"{state.summary}"
            )
        self.update_error_label()
        if state is not None and state.status == "running" and self._refresh_event is None:
            self._refresh_event = Clock.schedule_interval(self._refresh_from_clock, 0.25)
        if (state is None or state.status != "running") and self._refresh_event is not None:
            self._refresh_event.cancel()
            self._refresh_event = None

    def _refresh_from_clock(self, _dt: float) -> None:
        self.refresh()

    def on_leave(self, *args: object) -> None:
        super().on_leave(*args)
        if self._refresh_event is not None:
            self._refresh_event.cancel()
            self._refresh_event = None
