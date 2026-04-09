"""Popup window for long-running sync progress."""

from __future__ import annotations

from kivy.clock import Clock, ClockEvent
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.widgets.common import AppButton, WrappedLabel


class SyncProgressPopup(Popup):  # type: ignore[misc]
    """Dedicated window that shows sync progress and transport command logs."""

    def __init__(self, *, shell: FrontendShell) -> None:
        super().__init__(
            title="Remote Sync Progress",
            size_hint=(0.92, 0.85),
            auto_dismiss=False,
        )
        self._shell = shell
        self._refresh_event: ClockEvent | None = None

        container = BoxLayout(orientation="vertical", spacing=12, padding=12)
        self._status_label = WrappedLabel(text="No sync started yet.", font_size=16, bold=True)
        self._progress_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=20)
        self._message_label = WrappedLabel(text="", font_size=14)
        command_scroll = ScrollView(scroll_type=["bars", "content"], bar_width=8)
        self._command_log_label = WrappedLabel(
            text="Waiting for sync commands.",
            font_size=13,
        )
        command_scroll.add_widget(self._command_log_label)
        close_button = AppButton(text="Close", primary=False, size_hint_y=None, height=48)
        close_button.bind(on_release=lambda *_args: self.dismiss())

        container.add_widget(self._status_label)
        container.add_widget(self._progress_bar)
        container.add_widget(self._message_label)
        container.add_widget(command_scroll)
        container.add_widget(close_button)
        self.content = container

    def open_for_sync(self) -> None:
        """Open the popup and keep it refreshed while sync state changes."""
        self.refresh()
        if self._refresh_event is None:
            self._refresh_event = Clock.schedule_interval(self._refresh_from_clock, 0.1)
        if self.parent is None:
            self.open()

    def refresh(self) -> None:
        """Refresh the popup contents from the shell progress state."""
        state = self._shell.sync_progress_state
        if state is None:
            self._status_label.text = "No sync started yet."
            self._message_label.text = ""
            self._progress_bar.max = 1
            self._progress_bar.value = 0
            self._command_log_label.text = "Waiting for sync commands."
            return
        self.title = f"Remote Sync Progress: {state.project_name}"
        self._status_label.text = f"Status: {state.status}"
        self._message_label.text = state.message
        progress_max = state.progress_total if state.progress_total > 0 else 1
        progress_value = state.progress_current
        if not state.progress_is_indeterminate and state.progress_total == 0:
            progress_value = 1
        self._progress_bar.max = progress_max
        self._progress_bar.value = min(progress_value, progress_max)
        if state.command_log:
            self._command_log_label.text = "\n".join(
                entry.command_text for entry in state.command_log
            )
            return
        self._command_log_label.text = "Waiting for sync commands."

    def on_dismiss(self) -> None:
        """Stop the automatic refresh loop when the popup is closed."""
        if self._refresh_event is not None:
            self._refresh_event.cancel()
            self._refresh_event = None
        super().on_dismiss()

    def _refresh_from_clock(self, _delta: float) -> None:
        self.refresh()
