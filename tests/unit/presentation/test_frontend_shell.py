"""Unit tests for the frontend presentation shell."""

from __future__ import annotations

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.presentation.fakes import (
    build_empty_services,
    build_failing_sync_services,
    build_seeded_services,
)
from polyglot_site_translator.presentation.router import RouteName


def test_dashboard_sections_are_available_on_startup() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_dashboard()

    assert shell.router.current.name is RouteName.DASHBOARD
    assert [section.key for section in shell.dashboard_state.sections] == [
        "projects",
        "sync",
        "audit",
        "po-processing",
    ]


def test_projects_screen_loads_summaries_and_empty_state() -> None:
    shell = create_frontend_shell(build_empty_services())

    shell.open_projects()

    assert shell.projects_state.projects == []
    assert shell.projects_state.empty_message == "No projects registered yet."


def test_selecting_project_loads_detail_and_actions() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_projects()
    shell.select_project("wp-site")

    assert shell.router.current.name is RouteName.PROJECT_DETAIL
    assert shell.project_detail_state is not None
    assert shell.project_detail_state.project.id == "wp-site"
    assert [action.key for action in shell.project_detail_state.actions] == [
        "sync",
        "audit",
        "po-processing",
    ]


def test_sync_action_uses_fake_service_and_updates_state() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_sync()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "completed"
    assert shell.sync_state.files_synced == 12
    assert shell.latest_error is None


def test_sync_failure_is_exposed_without_crashing() -> None:
    shell = create_frontend_shell(build_failing_sync_services())

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_sync()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "failed"
    assert shell.latest_error == "Sync preview is unavailable for this project."


def test_audit_and_po_actions_update_independent_panels() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_audit()
    shell.start_po_processing()

    assert shell.audit_state is not None
    assert shell.audit_state.status == "completed"
    assert shell.audit_state.findings_summary == "3 findings across code and templates"
    assert shell.po_processing_state is not None
    assert shell.po_processing_state.status == "completed"
    assert shell.po_processing_state.processed_families == 4
