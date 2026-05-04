"""Integration tests for Kivy screen callbacks and navigation helpers."""

from __future__ import annotations

from typing import Any, cast

from pytest import MonkeyPatch

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.presentation.kivy.screens.base import _route_to_screen_name
from polyglot_site_translator.presentation.view_models import (
    POProcessingSummaryViewModel,
    SyncStatusViewModel,
)
from tests.support.frontend_doubles import build_seeded_services


def test_dashboard_screen_buttons_navigate_to_projects_and_settings() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    dashboard_screen = root.get_screen("dashboard")

    root.current = "dashboard"
    dashboard_screen._open_projects()
    assert root.current == "projects"

    root.current = "dashboard"
    dashboard_screen._open_settings()
    assert root.current == "settings"


def test_projects_screen_refresh_and_navigation_cover_empty_and_populated_states() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    projects_screen = root.get_screen("projects")
    shell = projects_screen._shell

    shell.projects_state = shell.projects_state.__class__(
        projects=[],
        empty_message="No projects registered yet.",
    )
    projects_screen.refresh()
    assert projects_screen._list_label.text == "No projects registered yet."

    shell.open_projects()
    root.current = "projects"
    projects_screen.refresh()
    assert len(projects_screen._project_buttons) == 2

    projects_screen._open_project("wp-site")
    assert root.current == "project_detail"

    projects_screen._go_dashboard()
    assert root.current == "dashboard"

    root.current = "projects"
    projects_screen._open_create_project()
    assert root.current == "project_editor"


def test_project_detail_screen_refresh_edit_sync_and_audit_actions_navigate() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    detail_screen = root.get_screen("project_detail")
    shell = detail_screen._shell

    shell.project_detail_state = None
    detail_screen.refresh()
    assert detail_screen._detail_label.text == "No project selected."
    root.current = "project_detail"
    detail_screen._edit_project()
    assert root.current == "project_detail"

    shell.open_projects()
    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen.refresh()
    assert "Marketing Site [WordPress]" in detail_screen._detail_label.text
    detail_screen._edit_project()
    assert root.current == "project_editor"

    shell.select_project("wp-site")
    root.current = "project_detail"

    detail_screen._start_sync()
    assert root.current == "project_detail"
    assert detail_screen._sync_progress_popup is not None
    existing_sync_popup = detail_screen._sync_progress_popup

    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen._start_sync()
    assert detail_screen._sync_progress_popup is existing_sync_popup

    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen._start_sync_to_remote()
    assert root.current == "project_detail"
    assert detail_screen._sync_progress_popup is not None
    assert detail_screen._sync_progress_popup is existing_sync_popup

    detail_screen._sync_progress_popup = None
    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen._start_sync_to_remote()
    assert detail_screen._sync_progress_popup is not None

    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen._start_audit()
    assert root.current == "audit"


def test_project_detail_screen_po_processing_and_back_navigation() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    detail_screen = root.get_screen("project_detail")
    shell = detail_screen._shell

    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen._start_po_processing()
    assert detail_screen._po_locale_popup is not None
    detail_screen._confirm_po_processing("en_US", True, True)
    assert root.current == "po_processing"

    shell.project_detail_state = None
    detail_screen._start_po_processing()
    assert detail_screen._po_locale_popup is not None

    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen._back_to_projects()
    assert root.current == "projects"


def test_workflow_screens_render_empty_and_loaded_states_and_return_to_detail() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    shell = root.get_screen("dashboard")._shell
    shell.open_projects()
    shell.select_project("wp-site")

    sync_screen = root.get_screen("sync")
    shell.sync_state = None
    sync_screen.refresh()
    assert sync_screen._summary_label.text == "No sync action started."
    shell.start_sync()
    sync_screen.refresh()
    assert "Files: 12" in sync_screen._summary_label.text
    sync_screen._back_to_project()
    assert root.current == "project_detail"

    shell.select_project("wp-site")
    audit_screen = root.get_screen("audit")
    shell.audit_state = None
    audit_screen.refresh()
    assert audit_screen._summary_label.text == "No audit action started."
    shell.start_audit()
    audit_screen.refresh()
    assert "Findings: 0" in audit_screen._summary_label.text
    assert "No supported framework was detected" in audit_screen._summary_label.text
    audit_screen._back_to_project()
    assert root.current == "project_detail"

    shell.select_project("wp-site")
    po_screen = root.get_screen("po_processing")
    shell.po_processing_state = None
    po_screen.refresh()
    assert po_screen._summary_label.text == "No translation action started."
    shell.start_po_processing()
    po_screen.refresh()
    assert "Families: 4" in po_screen._summary_label.text
    assert "Progress: 0/0" in po_screen._summary_label.text
    assert "Completed entries: 0/0" in po_screen._summary_label.text
    assert po_screen._progress_bar.value == 1
    po_screen._back_to_project()
    assert root.current == "project_detail"


def test_sync_and_audit_screens_back_navigation_without_selected_project() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    shell = root.get_screen("dashboard")._shell
    shell.project_detail_state = None

    sync_screen = root.get_screen("sync")
    root.current = "sync"
    sync_screen._back_to_project()
    assert root.current == "project_detail"

    audit_screen = root.get_screen("audit")
    root.current = "audit"
    audit_screen._back_to_project()
    assert root.current == "project_detail"


def test_sync_screen_refresh_includes_error_code_when_present() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    sync_screen = root.get_screen("sync")
    shell = root.get_screen("dashboard")._shell
    shell.sync_state = SyncStatusViewModel(
        status="failed",
        files_synced=0,
        summary="Authentication failed.",
        error_code="ssh_authentication_failed",
    )

    sync_screen.refresh()

    assert "Error Code: ssh_authentication_failed" in sync_screen._summary_label.text


def test_po_processing_screen_shows_current_file_and_entry() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    po_screen = root.get_screen("po_processing")
    shell = po_screen._shell

    shell.po_processing_state = POProcessingSummaryViewModel(
        status="running",
        processed_families=1,
        progress_current=3,
        progress_total=8,
        progress_is_indeterminate=False,
        summary="Processing PO family 1 of 2.",
        current_file="locale/messages-es_ES.po",
        current_entry="Title",
    )

    po_screen.refresh()

    assert "Current file: locale/messages-es_ES.po" in po_screen._summary_label.text
    assert "Current entry: Title" in po_screen._summary_label.text


def test_po_processing_screen_refresh_loop_and_back_navigation_branches(
    monkeypatch: MonkeyPatch,
) -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    po_screen = root.get_screen("po_processing")
    shell = po_screen._shell
    shell.project_detail_state = None
    root.current = "po_processing"

    scheduled: list[Any] = []

    class _FakeEvent:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    def _schedule_interval(callback: object, _interval: float) -> _FakeEvent:
        del callback
        event = _FakeEvent()
        scheduled.append(event)
        return event

    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.screens.po_processing.Clock.schedule_interval",
        _schedule_interval,
    )

    shell.po_processing_state = POProcessingSummaryViewModel(
        status="running",
        processed_families=1,
        progress_current=1,
        progress_total=5,
        progress_is_indeterminate=False,
        summary="Running.",
        current_file=None,
        current_entry=None,
    )
    po_screen.refresh()
    assert scheduled
    assert po_screen._refresh_event is scheduled[0]

    shell.po_processing_state = POProcessingSummaryViewModel(
        status="completed",
        processed_families=1,
        progress_current=5,
        progress_total=5,
        progress_is_indeterminate=False,
        summary="Completed.",
        current_file=None,
        current_entry=None,
    )
    po_screen.refresh()
    assert scheduled[0].cancelled is True
    assert po_screen._refresh_event is None

    po_screen._refresh_from_clock(0.1)
    po_screen.on_leave()
    assert po_screen._refresh_event is None

    class _ManualEvent:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    manual_event = _ManualEvent()
    po_screen._refresh_event = manual_event
    po_screen.on_leave()
    assert manual_event.cancelled is True
    assert po_screen._refresh_event is None
    po_screen.on_leave()

    po_screen._back_to_project()
    assert root.current == "project_detail"


def test_base_screen_helpers_cover_menu_building_copy_updates_and_route_mapping(
    monkeypatch: MonkeyPatch,
) -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    dashboard_screen = root.get_screen("dashboard")

    dashboard_screen.set_screen_copy(title="Updated Title", subtitle="Updated subtitle")
    assert dashboard_screen._screen_title.text == "Updated Title"
    assert dashboard_screen._screen_subtitle.text == "Updated subtitle"

    refresh_calls: list[str] = []

    def _record_refresh() -> None:
        refresh_calls.append("refresh")

    monkeypatch.setattr(dashboard_screen, "refresh", _record_refresh)
    root.current = "dashboard"
    dashboard_screen.show_route("dashboard")
    assert refresh_calls == ["refresh"]

    dashboard_screen._open_application_menu()
    assert dashboard_screen._menu_dropdown is not None
    assert len(dashboard_screen._menu_dropdown.children) > 0

    dashboard_screen._open_menu_route("projects")
    assert root.current == "projects"
    assert _route_to_screen_name("po-processing") == "po_processing"


def test_base_screen_menu_opens_when_parent_window_exists_and_route_opens_without_dropdown(
    monkeypatch: MonkeyPatch,
) -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    dashboard_screen = root.get_screen("dashboard")
    open_calls: list[object] = []

    class _FakeDropdown:
        def __init__(self, **_kwargs: object) -> None:
            self.children: list[object] = []

        def add_widget(self, widget: object) -> None:
            self.children.append(widget)

        def open(self, widget: object) -> None:
            open_calls.append(widget)

        def dismiss(self) -> None:
            open_calls.append("dismissed")

    def _parent_window() -> object:
        return object()

    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.screens.base.DropDown",
        _FakeDropdown,
    )
    monkeypatch.setattr(
        dashboard_screen._menu_button,
        "get_parent_window",
        _parent_window,
    )

    dashboard_screen._open_application_menu()

    assert open_calls == [dashboard_screen._menu_button]

    dashboard_screen._menu_dropdown = None
    dashboard_screen._open_menu_route("settings")
    assert root.current == "settings"


def test_base_screen_apply_theme_delegates_to_widget_tree(monkeypatch: MonkeyPatch) -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    dashboard_screen = root.get_screen("dashboard")
    calls: list[object] = []

    def _apply_theme(widget: object) -> None:
        calls.append(widget)

    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.screens.base.apply_theme_to_widget_tree",
        _apply_theme,
    )

    dashboard_screen.apply_theme()

    assert calls == [dashboard_screen._container]
