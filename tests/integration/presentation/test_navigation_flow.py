"""Integration tests for the frontend navigation flow."""

from __future__ import annotations

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.presentation.router import RouteName
from tests.support.frontend_doubles import build_seeded_services


def test_navigation_flow_keeps_selected_project_context() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_dashboard()
    shell.open_projects()
    shell.select_project("dj-admin")
    shell.open_projects()
    shell.select_project("wp-site")

    assert shell.router.current.name is RouteName.PROJECT_DETAIL
    assert shell.router.current.project_id == "wp-site"
    assert shell.project_detail_state is not None
    assert shell.project_detail_state.project.name == "Marketing Site"
