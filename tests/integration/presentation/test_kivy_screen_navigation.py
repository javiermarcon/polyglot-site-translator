"""Integration tests for Kivy screen callbacks and navigation helpers."""

from __future__ import annotations

from typing import Any, cast

from pytest import MonkeyPatch

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.presentation.kivy.screens.base import _route_to_screen_name
from polyglot_site_translator.presentation.view_models import POProcessingSummaryViewModel
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


def test_project_detail_screen_refresh_and_action_buttons_navigate() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    detail_screen = root.get_screen("project_detail")
    shell = detail_screen._shell

    shell.project_detail_state = None
    detail_screen.refresh()
    assert detail_screen._detail_label.text == "No project selected."

    shell.open_projects()
    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen.refresh()
    assert "Marketing Site [WordPress]" in detail_screen._detail_label.text

    detail_screen._start_sync()
    assert root.current == "project_detail"
    assert detail_screen._sync_progress_popup is not None

    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen._start_sync_to_remote()
    assert root.current == "project_detail"
    assert detail_screen._sync_progress_popup is not None

    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen._start_audit()
    assert root.current == "audit"

    shell.select_project("wp-site")
    root.current = "project_detail"
    detail_screen._start_po_processing()
    assert detail_screen._po_locale_popup is not None
    detail_screen._confirm_po_processing("en_US", True, True)
    assert root.current == "po_processing"

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
