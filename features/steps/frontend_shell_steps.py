"""BDD steps for the frontend shell."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.presentation.fakes import (
    build_empty_services,
    build_failing_sync_services,
    build_seeded_services,
)
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.router import RouteName

SYNCED_FILES = 12
PROCESSED_FAMILIES = 4
StepFunction = TypeVar("StepFunction", bound=Callable[..., object])

given = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.given)
when = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.when)
then = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.then)


class BehaveShellContext(Protocol):
    """Typed subset of behave context used by this feature."""

    shell: FrontendShell


def _context_with_shell(context: object) -> BehaveShellContext:
    return cast(BehaveShellContext, context)


@given("the frontend shell is wired with seeded fake services")
def step_seeded_shell(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_seeded_services())


@given("the frontend shell is wired with an empty fake catalog")
def step_empty_shell(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_empty_services())


@given("the frontend shell is wired with a failing sync service")
def step_failing_sync_shell(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_failing_sync_services())


@given('the operator has opened the detail for project "{project_id}"')
def step_open_project_detail(context: object, project_id: str) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_projects()
    typed_context.shell.select_project(project_id)


@when("the operator opens the application")
def step_open_application(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_dashboard()


@when("the operator opens the projects list")
def step_open_projects(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_projects()


@when('the operator selects the project "{project_id}"')
def step_select_project(context: object, project_id: str) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.select_project(project_id)


@when("the operator starts the sync workflow")
def step_start_sync(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.start_sync()


@when("the operator starts the audit workflow")
def step_start_audit(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.start_audit()


@when("the operator starts the po processing workflow")
def step_start_po_processing(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.start_po_processing()


@then("the dashboard is the active route")
def step_assert_dashboard_route(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.router.current.name is RouteName.DASHBOARD


@then("the dashboard shows the main workflow sections")
def step_assert_dashboard_sections(context: object) -> None:
    typed_context = _context_with_shell(context)
    section_keys = [section.key for section in typed_context.shell.dashboard_state.sections]
    assert section_keys == ["projects", "sync", "audit", "po-processing"]


@then('the project detail route is active for "{project_id}"')
def step_assert_project_detail_route(context: object, project_id: str) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.router.current.name is RouteName.PROJECT_DETAIL
    assert typed_context.shell.router.current.project_id == project_id


@then("the project detail shows available workflow actions")
def step_assert_project_actions(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_detail_state is not None
    action_keys = [action.key for action in typed_context.shell.project_detail_state.actions]
    assert action_keys == ["sync", "audit", "po-processing"]


@then("the sync panel shows a completed status")
def step_assert_sync_completed(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.sync_state is not None
    assert typed_context.shell.sync_state.status == "completed"


@then("the sync panel reports the synchronized file count")
def step_assert_sync_file_count(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.sync_state is not None
    assert typed_context.shell.sync_state.files_synced == SYNCED_FILES


@then("the audit panel shows a completed status")
def step_assert_audit_completed(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.audit_state is not None
    assert typed_context.shell.audit_state.status == "completed"


@then("the audit panel reports the finding summary")
def step_assert_audit_summary(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.audit_state is not None
    assert (
        typed_context.shell.audit_state.findings_summary == "3 findings across code and templates"
    )


@then("the po processing panel shows a completed status")
def step_assert_po_completed(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.po_processing_state is not None
    assert typed_context.shell.po_processing_state.status == "completed"


@then("the po processing panel reports the processed family count")
def step_assert_po_family_count(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.po_processing_state is not None
    assert typed_context.shell.po_processing_state.processed_families == PROCESSED_FAMILIES


@then("the projects list is empty")
def step_assert_empty_projects(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.projects_state.projects == []


@then("the projects screen shows an empty state message")
def step_assert_empty_state_message(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.projects_state.empty_message == "No projects registered yet."


@then("the sync panel shows a failed status")
def step_assert_sync_failed(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.sync_state is not None
    assert typed_context.shell.sync_state.status == "failed"


@then("the frontend shell shows the controlled error message")
def step_assert_error_message(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.latest_error == "Sync preview is unavailable for this project."
