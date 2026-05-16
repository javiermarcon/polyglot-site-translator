"""Popup window for long-running sync progress."""

from __future__ import annotations

from kivy.clock import Clock, ClockEvent
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.design_tokens import (
    COMPONENT_SIZES,
    SPACING,
    TYPOGRAPHY,
)
from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
)

from .ssh_host_key_trust_dialog import open_ssh_host_key_trust_confirmation


class SyncProgressPopup(Popup):  # type: ignore[misc]
    """Dedicated window that shows sync progress and transport command logs.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, *, shell: FrontendShell) -> None:
        """Build the popup widgets that mirror shell-managed sync progress state.

        Args:
            self:
                Value supplied to this callable.
            shell:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(
            title="Sync Progress",
            size_hint=(0.92, 0.85),
            auto_dismiss=False,
        )
        self._shell = shell
        self._refresh_event: ClockEvent | None = None

        container = SurfaceBoxLayout(
            orientation="vertical",
            spacing=SPACING.md,
            padding=SPACING.md,
            background_role="card_background",
            border_role="border_color",
        )
        self._status_label = WrappedLabel(
            text="No sync started yet.",
            font_size=TYPOGRAPHY.label,
            bold=True,
        )
        self._progress_bar = ProgressBar(
            max=1,
            value=0,
            size_hint_y=None,
            height=COMPONENT_SIZES.progress_height,
        )
        self._message_label = WrappedLabel(text="", font_size=TYPOGRAPHY.caption)
        self._trust_host_key_button = AppButton(
            text="Trust SSH Host Key and Retry",
            primary=True,
            size_hint_y=None,
            height=COMPONENT_SIZES.button_height,
        )
        self._trust_host_key_button.bind(on_release=self._open_host_key_confirmation)
        command_scroll = ScrollView(scroll_type=["bars", "content"], bar_width=8)
        self._command_log_label = WrappedLabel(
            text="Waiting for sync commands.",
            font_size=TYPOGRAPHY.caption,
        )
        command_scroll.add_widget(self._command_log_label)
        close_button = AppButton(
            text="Close",
            primary=False,
            size_hint_y=None,
            height=COMPONENT_SIZES.button_height,
        )
        close_button.bind(on_release=lambda *_args: self.dismiss())

        container.add_widget(self._status_label)
        container.add_widget(self._progress_bar)
        container.add_widget(self._message_label)
        container.add_widget(self._trust_host_key_button)
        container.add_widget(command_scroll)
        container.add_widget(close_button)
        self.content = container

    def open_for_sync(self) -> None:
        """Open the popup and keep it refreshed while sync state changes.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.refresh()
        if self._refresh_event is None:
            self._refresh_event = Clock.schedule_interval(self._refresh_from_clock, 0.1)
        if self.parent is None:
            self.open()

    def refresh(self) -> None:
        """Refresh the popup contents from the shell progress state.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        state = self._shell.sync_progress_state
        if state is None:
            self._status_label.text = "No sync started yet."
            self._message_label.text = ""
            self._progress_bar.max = 1
            self._progress_bar.value = 0
            self._trust_host_key_button.disabled = True
            self._trust_host_key_button.opacity = 0
            self._command_log_label.text = "Waiting for sync commands."
            return
        self.title = f"Sync Progress: {state.project_name}"
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
        else:
            self._command_log_label.text = "Waiting for sync commands."
        can_trust_host_key = (
            state.status == "failed"
            and self._shell.sync_state is not None
            and self._shell.sync_state.error_code == "unknown_ssh_host_key"
        )
        self._trust_host_key_button.disabled = not can_trust_host_key
        self._trust_host_key_button.opacity = 1 if can_trust_host_key else 0

    def on_dismiss(self) -> None:
        """Stop the automatic refresh loop when the popup is closed.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if self._refresh_event is not None:
            self._refresh_event.cancel()
            self._refresh_event = None
        super().on_dismiss()

    def _refresh_from_clock(self, _delta: float) -> None:
        """Refresh from clock.

        Args:
            self:
                Value supplied to this callable.
            _delta:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.refresh()

    def _open_host_key_confirmation(self, *_args: object) -> None:
        """Open host key confirmation.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        open_ssh_host_key_trust_confirmation(
            on_trust=self._run_trust_host_key_after_confirmation,
            purpose="sync",
        )

    def _run_trust_host_key_after_confirmation(self) -> None:
        """Run trust host key after confirmation.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.trust_selected_project_remote_host_key()
        self.refresh()
