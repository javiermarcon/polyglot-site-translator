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
)
from tests.support.frontend_doubles import build_seeded_services


@dataclass
class _FakeClockEvent:
    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True


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
