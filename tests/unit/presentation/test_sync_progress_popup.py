"""Unit tests for the sync progress popup widget."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from pytest import MonkeyPatch

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.presentation.kivy.widgets.sync_progress_popup import (
    SyncProgressPopup,
)
from polyglot_site_translator.presentation.view_models import (
    SyncCommandLogEntryViewModel,
    SyncProgressStateViewModel,
    SyncStatusViewModel,
)
from tests.support.frontend_doubles import build_seeded_services


@dataclass
class _FakeClockEvent:
    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True


@dataclass
class _FakeConfirmationPopup:
    title: str = ""
    size_hint: tuple[float, float] | None = None
    auto_dismiss: bool = False
    content: object | None = None
    opened: bool = False
    dismissed: bool = False

    def dismiss(self) -> None:
        self.dismissed = True

    def open(self) -> None:
        self.opened = True


def test_sync_progress_popup_renders_empty_and_populated_states() -> None:
    shell = create_frontend_shell(build_seeded_services())
    popup = SyncProgressPopup(shell=shell)

    shell.sync_progress_state = None
    popup.refresh()
    assert popup._status_label.text == "No sync started yet."
    assert popup._command_log_label.text == "Waiting for sync commands."
    assert popup._progress_bar.value == 0

    shell.sync_progress_state = SyncProgressStateViewModel(
        project_id="site-123",
        project_name="Marketing Site",
        status="completed",
        message="Remote sync completed.",
        progress_current=0,
        progress_total=0,
        progress_is_indeterminate=False,
        command_log_limit=10,
        command_log=[],
    )
    popup.refresh()
    assert popup.title == "Remote Sync Progress: Marketing Site"
    assert popup._status_label.text == "Status: completed"
    assert popup._progress_bar.max == 1
    assert popup._progress_bar.value == 1
    assert popup._command_log_label.text == "Waiting for sync commands."

    shell.sync_progress_state = SyncProgressStateViewModel(
        project_id="site-123",
        project_name="Marketing Site",
        status="running",
        message="Downloading remote files.",
        progress_current=1,
        progress_total=2,
        progress_is_indeterminate=False,
        command_log_limit=10,
        command_log=[
            SyncCommandLogEntryViewModel(
                command_text="SFTP LIST /srv/app",
                message="Listing the remote source.",
            ),
            SyncCommandLogEntryViewModel(
                command_text="SFTP GET /srv/app/locale/es.po",
                message="Downloading a file.",
            ),
        ],
    )
    popup.refresh()
    assert popup._progress_bar.max == 2
    assert popup._progress_bar.value == 1
    assert "SFTP LIST /srv/app" in popup._command_log_label.text
    assert "SFTP GET /srv/app/locale/es.po" in popup._command_log_label.text


def test_sync_progress_popup_open_and_dismiss_manage_refresh_loop(
    monkeypatch: MonkeyPatch,
) -> None:
    shell = create_frontend_shell(build_seeded_services())
    popup = SyncProgressPopup(shell=shell)
    scheduled_events: list[_FakeClockEvent] = []
    open_calls: list[str] = []

    def record_schedule(_callback: object, _interval: float) -> _FakeClockEvent:
        event = _FakeClockEvent()
        scheduled_events.append(event)
        return event

    def record_open() -> None:
        open_calls.append("open")

    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.sync_progress_popup.Clock.schedule_interval",
        record_schedule,
    )
    monkeypatch.setattr(popup, "open", record_open)

    popup.open_for_sync()
    assert len(scheduled_events) == 1
    assert open_calls == ["open"]
    popup._refresh_event = cast(Any, scheduled_events[0])
    popup._refresh_from_clock(0.1)
    popup.on_dismiss()

    assert scheduled_events[0].cancelled is True
    assert popup._refresh_event is None


def test_sync_progress_popup_offers_host_key_trust_only_for_unknown_ssh_hosts() -> None:
    shell = create_frontend_shell(build_seeded_services())
    popup = SyncProgressPopup(shell=shell)
    shell.sync_progress_state = SyncProgressStateViewModel(
        project_id="site-123",
        project_name="Marketing Site",
        status="failed",
        message="Server '127.0.0.1' not found in known_hosts",
        progress_current=0,
        progress_total=0,
        progress_is_indeterminate=True,
        command_log_limit=10,
        command_log=[],
    )

    shell.sync_state = SyncStatusViewModel(
        status="failed",
        files_synced=0,
        summary="Server '127.0.0.1' not found in known_hosts",
        error_code="unknown_ssh_host_key",
    )
    popup.refresh()
    assert popup._trust_host_key_button.disabled is False
    assert popup._trust_host_key_button.opacity == 1

    shell.sync_state = SyncStatusViewModel(
        status="failed",
        files_synced=0,
        summary="Authentication failed.",
        error_code="ssh_authentication_failed",
    )
    popup.refresh()
    assert popup._trust_host_key_button.opacity == 0
    assert popup._trust_host_key_button.disabled is True


def test_sync_progress_popup_hides_host_key_trust_while_retry_is_running() -> None:
    shell = create_frontend_shell(build_seeded_services())
    popup = SyncProgressPopup(shell=shell)
    shell.sync_state = SyncStatusViewModel(
        status="failed",
        files_synced=0,
        summary="Server '127.0.0.1' not found in known_hosts",
        error_code="unknown_ssh_host_key",
    )
    shell.sync_progress_state = SyncProgressStateViewModel(
        project_id="site-123",
        project_name="Marketing Site",
        status="running",
        message="Starting remote sync after trusting the SSH host key.",
        progress_current=0,
        progress_total=0,
        progress_is_indeterminate=True,
        command_log_limit=10,
        command_log=[],
    )

    popup.refresh()

    assert popup._trust_host_key_button.opacity == 0
    assert popup._trust_host_key_button.disabled is True


def test_sync_progress_popup_trust_confirmation_delegates_to_shell(
    monkeypatch: MonkeyPatch,
) -> None:
    shell = create_frontend_shell(build_seeded_services())
    popup = SyncProgressPopup(shell=shell)
    confirmation = _FakeConfirmationPopup()
    trust_calls: list[str] = []

    def record_trust() -> None:
        trust_calls.append("trusted")

    monkeypatch.setattr(shell, "trust_selected_project_remote_host_key", record_trust)

    popup._accept_host_key_confirmation(cast(Any, confirmation))

    assert confirmation.dismissed is True
    assert trust_calls == ["trusted"]


def test_sync_progress_popup_opens_host_key_confirmation(
    monkeypatch: MonkeyPatch,
) -> None:
    shell = create_frontend_shell(build_seeded_services())
    popup = SyncProgressPopup(shell=shell)
    confirmations: list[_FakeConfirmationPopup] = []

    def build_confirmation_popup(
        *,
        title: str,
        size_hint: tuple[float, float],
        auto_dismiss: bool,
    ) -> _FakeConfirmationPopup:
        confirmation = _FakeConfirmationPopup(
            title=title,
            size_hint=size_hint,
            auto_dismiss=auto_dismiss,
        )
        confirmations.append(confirmation)
        return confirmation

    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.sync_progress_popup.Popup",
        build_confirmation_popup,
    )

    popup._open_host_key_confirmation()

    assert len(confirmations) == 1
    assert confirmations[0].title == "Trust SSH Host Key?"
    assert confirmations[0].auto_dismiss is False
    assert confirmations[0].content is not None
    assert confirmations[0].opened is True
