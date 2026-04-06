"""BDD steps for the frontend shell."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.presentation.fakes import (
    build_empty_services,
    build_failing_settings_load_services,
    build_failing_settings_save_services,
    build_failing_sync_services,
    build_seeded_services,
)
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.router import RouteName

SYNCED_FILES = 12
PROCESSED_FAMILIES = 4
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 720
THEME_OPTION_COUNT = 3
CUSTOM_WINDOW_WIDTH = 1440
CUSTOM_WINDOW_HEIGHT = 900
COMPACT_WINDOW_WIDTH = 550
COMPACT_WINDOW_HEIGHT = 700
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


@given("the frontend shell is wired with a failing settings load service")
def step_failing_settings_load_shell(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_failing_settings_load_services())


@given("the frontend shell is wired with a failing settings save service")
def step_failing_settings_save_shell(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_failing_settings_save_services())


@given('the operator has opened the detail for project "{project_id}"')
def step_open_project_detail(context: object, project_id: str) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_projects()
    typed_context.shell.select_project(project_id)


@given("the operator has opened the settings screen")
def step_open_settings_screen(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_settings()


@given("the operator has saved custom settings")
def step_saved_custom_settings(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_settings()
    typed_context.shell.set_settings_theme_mode("dark")
    typed_context.shell.toggle_remember_last_screen()
    typed_context.shell.toggle_developer_mode()
    typed_context.shell.set_settings_window_size(width=1440, height=900)
    typed_context.shell.save_settings()


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


@when("the operator opens the settings screen")
def step_open_settings(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_settings()


@when("the operator opens the application menu")
def step_open_application_menu(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_application_menu()


@when("the operator opens the settings screen from the application menu")
def step_open_settings_from_menu(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_settings()


@when("the operator enables remember last screen")
def step_enable_remember_last_screen(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.toggle_remember_last_screen()


@when("the operator enables developer mode")
def step_enable_developer_mode(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.toggle_developer_mode()


@when('the operator sets the theme mode to "{theme_mode}"')
def step_set_theme_mode(context: object, theme_mode: str) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_theme_mode(theme_mode)


@when("the operator sets the window size to 1440 by 900")
def step_set_window_size(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_window_size(
        width=CUSTOM_WINDOW_WIDTH,
        height=CUSTOM_WINDOW_HEIGHT,
    )


@when("the operator sets the compact window size to 550 by 700")
def step_set_compact_window_size(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_window_size(
        width=COMPACT_WINDOW_WIDTH,
        height=COMPACT_WINDOW_HEIGHT,
    )


@when("the operator applies the settings changes")
def step_apply_settings(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.save_settings()


@when("the operator restores the default settings")
def step_restore_settings(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.restore_default_settings()


@when('the operator selects the settings section "{section_key}"')
def step_select_settings_section(context: object, section_key: str) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.select_settings_section(section_key)


@then("the dashboard is the active route")
def step_assert_dashboard_route(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.router.current.name is RouteName.DASHBOARD


@then("the dashboard shows the main workflow sections")
def step_assert_dashboard_sections(context: object) -> None:
    typed_context = _context_with_shell(context)
    section_keys = [section.key for section in typed_context.shell.dashboard_state.sections]
    assert section_keys == ["projects", "sync", "audit", "po-processing", "settings"]


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


@then("the settings route is active")
def step_assert_settings_route(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.router.current.name is RouteName.SETTINGS


@then("the settings screen shows the App / UI / Kivy section")
def step_assert_settings_section(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    section_keys = [section.key for section in typed_context.shell.settings_state.sections]
    assert "app-ui-kivy" in section_keys


@then("the application menu shows the main navigation groups")
def step_assert_application_menu_groups(context: object) -> None:
    typed_context = _context_with_shell(context)
    section_keys = [section.key for section in typed_context.shell.navigation_menu.sections]
    assert section_keys == ["workspace", "operations", "system"]


@then("the settings draft uses the default window size")
def step_assert_default_window_size(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.app_settings.window_width == DEFAULT_WINDOW_WIDTH
    assert typed_context.shell.settings_state.app_settings.window_height == DEFAULT_WINDOW_HEIGHT


@then("the settings draft keeps remember last screen disabled")
def step_assert_default_remember_last_screen(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.app_settings.remember_last_screen is False


@then("the settings screen shows a single theme selector with explanations")
def step_assert_theme_selector(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.theme_mode_field.control_type == "choice"
    assert len(typed_context.shell.settings_state.theme_mode_field.options) == THEME_OPTION_COUNT
    assert typed_context.shell.settings_state.theme_mode_field.help_text != ""


@then("the settings screen shows the changes as saved")
def step_assert_settings_saved(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.status == "saved"


@then("the settings save exposes a saved confirmation message")
def step_assert_settings_saved_message(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.status_message == "Settings saved."


@then("the saved settings keep remember last screen enabled")
def step_assert_saved_remember_last_screen(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.app_settings.remember_last_screen is True


@then("the saved settings keep the selected window size")
def step_assert_saved_window_size(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.app_settings.window_width == CUSTOM_WINDOW_WIDTH
    assert typed_context.shell.settings_state.app_settings.window_height == CUSTOM_WINDOW_HEIGHT


@then("the saved settings keep the compact window size")
def step_assert_saved_compact_window_size(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.app_settings.window_width == COMPACT_WINDOW_WIDTH
    assert typed_context.shell.settings_state.app_settings.window_height == COMPACT_WINDOW_HEIGHT


@then("the settings draft shows the persisted custom values")
def step_assert_persisted_settings(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.app_settings.theme_mode == "dark"
    assert typed_context.shell.settings_state.app_settings.developer_mode is True
    assert typed_context.shell.settings_state.app_settings.remember_last_screen is True
    assert typed_context.shell.settings_state.app_settings.window_width == CUSTOM_WINDOW_WIDTH
    assert typed_context.shell.settings_state.app_settings.window_height == CUSTOM_WINDOW_HEIGHT


@then("the settings screen shows a failed status")
def step_assert_settings_failed(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.status == "failed"


@then("the frontend shell shows the controlled settings error message")
def step_assert_settings_error_message(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.latest_error in {
        "App settings are temporarily unavailable.",
        "App settings could not be saved.",
    }


@then("the settings screen shows the selected planned section")
def step_assert_planned_section(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.selected_section_key == "translation"
    assert typed_context.shell.settings_state.status_message == (
        "Translation Settings will be available later."
    )
