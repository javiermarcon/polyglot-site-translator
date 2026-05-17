"""BDD steps for the frontend shell."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
import tempfile
from typing import NoReturn, Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.domain.sync.scope import (
    ConfiguredSyncRule,
    FrameworkSyncRuleSet,
    SyncFilterType,
    SyncRuleBehavior,
)
from polyglot_site_translator.infrastructure.settings import (
    build_default_settings_service,
)
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.router import RouteName
from tests.support.frontend_doubles import (
    build_empty_services,
    build_failing_audit_services,
    build_failing_po_processing_services,
    build_failing_settings_load_services,
    build_failing_settings_save_services,
    build_failing_sync_services,
    build_seeded_services,
    build_seeded_services_with_settings,
)

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

given = cast(
    Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.given
)
when = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.when)
then = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.then)


def _raise_bdd_expectation_failure(location: str) -> NoReturn:
    """Raise an explicit Behave expectation failure.

    Args:
        location:
            Source location of the failed BDD expectation.

    Returns:
        value:
            This helper never returns; it always raises AssertionError.

    Raises:
        AssertionError:
            Raised every time this helper is called so Behave reports the
            step as failed without relying on optimized-away assertions.
    """
    message = f"BDD expectation failed at {location}."
    raise AssertionError(message)


class BehaveShellContext(Protocol):
    """BDD helper for BehaveShellContext.

    Attributes:
        shell:
            Documented attribute exposed by this type.
        settings_temp_dir:
            Documented attribute exposed by this type.
    """

    shell: FrontendShell
    settings_temp_dir: tempfile.TemporaryDirectory[str]


def _context_with_shell(context: object) -> BehaveShellContext:
    """Handle context with shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return cast(BehaveShellContext, context)


@given("the frontend shell is wired with seeded frontend test doubles")
def step_seeded_shell(context: object) -> None:
    """Run the BDD step for seeded shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_seeded_services())


@given("the frontend shell is wired with TOML-backed settings persistence")
def step_seeded_toml_shell(context: object) -> None:
    """Run the BDD step for seeded toml shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.settings_temp_dir = tempfile.TemporaryDirectory()
    settings_service = build_default_settings_service(
        config_dir=Path(typed_context.settings_temp_dir.name)
    )
    typed_context.shell = create_frontend_shell(
        build_seeded_services_with_settings(settings_service)
    )


@given("the frontend shell is wired with an empty frontend test catalog")
def step_empty_shell(context: object) -> None:
    """Run the BDD step for empty shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_empty_services())


@given("the frontend shell is wired with a failing sync test double")
def step_failing_sync_shell(context: object) -> None:
    """Run the BDD step for failing sync shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_failing_sync_services())


@given("the frontend shell is wired with a failing audit test double")
def step_failing_audit_shell(context: object) -> None:
    """Run the BDD step for failing audit shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_failing_audit_services())


@given("the frontend shell is wired with a failing translation test double")
def step_failing_po_shell(context: object) -> None:
    """Run the BDD step for failing po shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_failing_po_processing_services())


@given("the frontend shell is wired with a failing settings-load test double")
def step_failing_settings_load_shell(context: object) -> None:
    """Run the BDD step for failing settings load shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_failing_settings_load_services())


@given("the frontend shell is wired with a failing settings-save test double")
def step_failing_settings_save_shell(context: object) -> None:
    """Run the BDD step for failing settings save shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell = create_frontend_shell(build_failing_settings_save_services())


@given('the operator has opened the detail for project "{project_id}"')
def step_open_project_detail(context: object, project_id: str) -> None:
    """Run the BDD step for open project detail.

    Args:
        context:
            Value supplied to this callable.
        project_id:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_projects()
    typed_context.shell.select_project(project_id)


@given("the operator has opened the settings screen")
def step_open_settings_screen(context: object) -> None:
    """Run the BDD step for open settings screen.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_settings()


@given("the operator has saved custom settings")
def step_saved_custom_settings(context: object) -> None:
    """Run the BDD step for saved custom settings.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_settings()
    typed_context.shell.set_settings_theme_mode("dark")
    typed_context.shell.toggle_remember_last_screen()
    typed_context.shell.toggle_developer_mode()
    typed_context.shell.set_settings_window_size(width=1440, height=900)
    typed_context.shell.save_settings()


@when("the operator restarts the frontend shell")
def step_restart_frontend_shell(context: object) -> None:
    """Run the BDD step for restart frontend shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    settings_service = build_default_settings_service(
        config_dir=Path(typed_context.settings_temp_dir.name)
    )
    typed_context.shell = create_frontend_shell(
        build_seeded_services_with_settings(settings_service)
    )


@when("the operator opens the application")
def step_open_application(context: object) -> None:
    """Run the BDD step for open application.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_dashboard()


@when("the operator opens the projects list")
def step_open_projects(context: object) -> None:
    """Run the BDD step for open projects.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_projects()


@when('the operator selects the project "{project_id}"')
def step_select_project(context: object, project_id: str) -> None:
    """Run the BDD step for select project.

    Args:
        context:
            Value supplied to this callable.
        project_id:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.select_project(project_id)


@when("the operator starts the sync workflow")
def step_start_sync(context: object) -> None:
    """Run the BDD step for start sync.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.start_sync()


@when("the operator starts the audit workflow")
def step_start_audit(context: object) -> None:
    """Run the BDD step for start audit.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.start_audit()


@when("the operator starts the po processing workflow")
def step_start_po_processing(context: object) -> None:
    """Run the BDD step for start po processing.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.start_po_processing()


@when("the operator opens the settings screen")
def step_open_settings(context: object) -> None:
    """Run the BDD step for open settings.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_settings()


@when("the operator opens the application menu")
def step_open_application_menu(context: object) -> None:
    """Run the BDD step for open application menu.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_application_menu()


@when("the operator opens the settings screen from the application menu")
def step_open_settings_from_menu(context: object) -> None:
    """Run the BDD step for open settings from menu.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_settings()


@when("the operator enables remember last screen")
def step_enable_remember_last_screen(context: object) -> None:
    """Run the BDD step for enable remember last screen.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.toggle_remember_last_screen()


@when("the operator enables developer mode")
def step_enable_developer_mode(context: object) -> None:
    """Run the BDD step for enable developer mode.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.toggle_developer_mode()


@when('the operator sets the theme mode to "{theme_mode}"')
def step_set_theme_mode(context: object, theme_mode: str) -> None:
    """Run the BDD step for set theme mode.

    Args:
        context:
            Value supplied to this callable.
        theme_mode:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_theme_mode(theme_mode)


@when('the operator sets the UI language to "{ui_language}"')
def step_set_ui_language(context: object, ui_language: str) -> None:
    """Run the BDD step for set ui language.

    Args:
        context:
            Value supplied to this callable.
        ui_language:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_ui_language(ui_language)


@when('the operator sets the default project locale to "{default_locale}"')
def step_set_default_project_locale(context: object, default_locale: str) -> None:
    """Run the BDD step for set default project locale.

    Args:
        context:
            Value supplied to this callable.
        default_locale:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_project_locale(default_locale)


@when("the operator enables default MO compilation")
def step_enable_default_mo_compilation(context: object) -> None:
    """Run the BDD step for enable default mo compilation.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_compile_mo(True)


@when("the operator disables default MO compilation")
def step_disable_default_mo_compilation(context: object) -> None:
    """Run the BDD step for disable default mo compilation.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_compile_mo(False)


@when("the operator enables the default external translator")
def step_enable_default_external_translator(context: object) -> None:
    """Run the BDD step for enable default external translator.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_use_external_translator(True)


@when("the operator disables the default external translator")
def step_disable_default_external_translator(context: object) -> None:
    """Run the BDD step for disable default external translator.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_use_external_translator(False)


@when("the operator disables the default translation cache")
def step_disable_default_translation_cache(context: object) -> None:
    """Run the BDD step for disable default translation cache.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_use_translation_cache(False)


@when("the operator enables default only-fuzzy mode")
def step_enable_default_only_fuzzy(context: object) -> None:
    """Run the BDD step for enable default only fuzzy.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_only_fuzzy(True)


@when('the operator sets the translation cache path to "{cache_path}"')
def step_set_translation_cache_path(context: object, cache_path: str) -> None:
    """Run the BDD step for set translation cache path.

    Args:
        context:
            Value supplied to this callable.
        cache_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_translation_cache_path(cache_path)


@when("the operator enables default dry-run mode")
def step_enable_default_dry_run(context: object) -> None:
    """Run the BDD step for enable default dry run.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_dry_run(True)


@when("the operator disables default stats-only mode")
def step_disable_default_stats_only(context: object) -> None:
    """Run the BDD step for disable default stats only.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_stats_only(False)


@when("the operator enables default stats-only mode")
def step_enable_default_stats_only(context: object) -> None:
    """Run the BDD step for enable default stats only.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_stats_only(True)


@when("the operator enables default inconsistency reporting")
def step_enable_default_inconsistency_reporting(context: object) -> None:
    """Run the BDD step for enable default inconsistency reporting.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_default_report_inconsistencies(True)


@when("the operator sets the window size to 1440 by 900")
def step_set_window_size(context: object) -> None:
    """Run the BDD step for set window size.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_window_size(
        width=CUSTOM_WINDOW_WIDTH,
        height=CUSTOM_WINDOW_HEIGHT,
    )


@when("the operator sets the compact window size to 550 by 700")
def step_set_compact_window_size(context: object) -> None:
    """Run the BDD step for set compact window size.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_window_size(
        width=COMPACT_WINDOW_WIDTH,
        height=COMPACT_WINDOW_HEIGHT,
    )


@when("the operator applies the settings changes")
def step_apply_settings(context: object) -> None:
    """Run the BDD step for apply settings.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_settings()


@when("the operator restores the default settings")
def step_restore_settings(context: object) -> None:
    """Run the BDD step for restore settings.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.restore_default_settings()


@when('the operator selects the settings section "{section_key}"')
def step_select_settings_section(context: object, section_key: str) -> None:
    """Run the BDD step for select settings section.

    Args:
        context:
            Value supplied to this callable.
        section_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.select_settings_section(section_key)


@when("the operator enables gitignore-based sync exclusions")
def step_enable_gitignore_sync_exclusions(context: object) -> None:
    """Run the BDD step for enable gitignore sync exclusions.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    state = typed_context.shell.settings_state
    if state is None:
        msg = "Settings must be loaded before editing gitignore sync exclusions."
        raise AssertionError(msg)
    typed_context.shell.update_settings_draft(
        replace(
            state.app_settings,
            sync_scope_settings=replace(
                state.app_settings.sync_scope_settings,
                use_gitignore_rules=True,
            ),
        )
    )


@when(
    'the operator adds the global sync rule "{relative_path}" as '
    '"{behavior}" "{filter_type}"'
)
def step_add_global_sync_rule(
    context: object,
    relative_path: str,
    behavior: str,
    filter_type: str,
) -> None:
    """Run the BDD step for add global sync rule.

    Args:
        context:
            Value supplied to this callable.
        relative_path:
            Value supplied to this callable.
        behavior:
            Value supplied to this callable.
        filter_type:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    state = typed_context.shell.settings_state
    if state is None:
        msg = "Settings must be loaded before editing global sync rules."
        raise AssertionError(msg)
    new_rule = ConfiguredSyncRule(
        relative_path=relative_path,
        filter_type=SyncFilterType(filter_type),
        behavior=SyncRuleBehavior(behavior),
        description=relative_path,
        is_enabled=True,
    )
    typed_context.shell.update_settings_draft(
        replace(
            state.app_settings,
            sync_scope_settings=replace(
                state.app_settings.sync_scope_settings,
                global_rules=(
                    *state.app_settings.sync_scope_settings.global_rules,
                    new_rule,
                ),
            ),
        )
    )


@when(
    'the operator adds the framework sync rule "{relative_path}" '
    'for "{framework_type}" as "{behavior}" "{filter_type}"'
)
def step_add_framework_sync_rule(
    context: object,
    relative_path: str,
    framework_type: str,
    behavior: str,
    filter_type: str,
) -> None:
    """Run the BDD step for add framework sync rule.

    Args:
        context:
            Value supplied to this callable.
        relative_path:
            Value supplied to this callable.
        framework_type:
            Value supplied to this callable.
        behavior:
            Value supplied to this callable.
        filter_type:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    state = typed_context.shell.settings_state
    if state is None:
        msg = "Settings must be loaded before editing framework sync rules."
        raise AssertionError(msg)
    new_rule = ConfiguredSyncRule(
        relative_path=relative_path,
        filter_type=SyncFilterType(filter_type),
        behavior=SyncRuleBehavior(behavior),
        description=relative_path,
        is_enabled=True,
    )
    framework_rules = list(state.app_settings.sync_scope_settings.framework_rule_sets)
    framework_rules.append(
        FrameworkSyncRuleSet(
            framework_type=framework_type,
            rules=(new_rule,),
        )
    )
    typed_context.shell.update_settings_draft(
        replace(
            state.app_settings,
            sync_scope_settings=replace(
                state.app_settings.sync_scope_settings,
                framework_rule_sets=tuple(framework_rules),
            ),
        )
    )


@then("the dashboard is the active route")
def step_assert_dashboard_route(context: object) -> None:
    """Run the BDD step for assert dashboard route.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.router.current.name is not RouteName.DASHBOARD:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:955")


@then("the saved settings enable gitignore-based sync exclusions")
def step_assert_saved_gitignore_sync_exclusions(context: object) -> None:
    """Run the BDD step for assert saved gitignore sync exclusions.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:975")
    settings_state = typed_context.shell.settings_state
    if not settings_state.app_settings.sync_scope_settings.use_gitignore_rules:
        raise AssertionError


@then('the saved settings contain the global sync rule "{relative_path}"')
def step_assert_saved_global_sync_rule(context: object, relative_path: str) -> None:
    """Run the BDD step for assert saved global sync rule.

    Args:
        context:
            Value supplied to this callable.
        relative_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1000")
    if relative_path not in [
        rule.relative_path
        for rule in (
            typed_context.shell.settings_state.app_settings.sync_scope_settings.global_rules
        )
    ]:
        raise AssertionError


@then(
    'the saved settings contain the framework sync rule "{relative_path}" '
    'for "{framework_type}"'
)
def step_assert_saved_framework_sync_rule(
    context: object,
    relative_path: str,
    framework_type: str,
) -> None:
    """Run the BDD step for assert saved framework sync rule.

    Args:
        context:
            Value supplied to this callable.
        relative_path:
            Value supplied to this callable.
        framework_type:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1038")
    settings_state = typed_context.shell.settings_state
    framework_rule_sets = (
        settings_state.app_settings.sync_scope_settings.framework_rule_sets
    )
    framework_rules = [
        rule_set
        for rule_set in framework_rule_sets
        if rule_set.framework_type == framework_type
    ]
    if framework_rules == []:
        raise AssertionError
    if relative_path not in [rule.relative_path for rule in framework_rules[0].rules]:
        raise AssertionError


@then("the dashboard shows the main workflow sections")
def step_assert_dashboard_sections(context: object) -> None:
    """Run the BDD step for assert dashboard sections.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    section_keys = [
        section.key for section in typed_context.shell.dashboard_state.sections
    ]
    if section_keys != ["projects", "sync", "audit", "po-processing", "settings"]:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1070")


@then('the project detail route is active for "{project_id}"')
def step_assert_project_detail_route(context: object, project_id: str) -> None:
    """Run the BDD step for assert project detail route.

    Args:
        context:
            Value supplied to this callable.
        project_id:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.router.current.name is not RouteName.PROJECT_DETAIL:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1088")
    if typed_context.shell.router.current.project_id != project_id:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1089")


@then("the project detail shows available workflow actions")
def step_assert_project_actions(context: object) -> None:
    """Run the BDD step for assert project actions.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1105")
    action_keys = [
        action.key for action in typed_context.shell.project_detail_state.actions
    ]
    if action_keys != ["sync", "audit", "po-processing"]:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1109")


@then("the sync panel shows a completed status")
def step_assert_sync_completed(context: object) -> None:
    """Run the BDD step for assert sync completed.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.sync_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1125")
    if typed_context.shell.sync_state.status != "completed":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1126")


@then("the sync panel reports the synchronized file count")
def step_assert_sync_file_count(context: object) -> None:
    """Run the BDD step for assert sync file count.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.sync_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1142")
    if typed_context.shell.sync_state.files_synced != SYNCED_FILES:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1143")


@then("the audit panel shows a completed status")
def step_assert_audit_completed(context: object) -> None:
    """Run the BDD step for assert audit completed.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.audit_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1159")
    if typed_context.shell.audit_state.status != "completed":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1160")


@then("the audit panel reports the finding summary")
def step_assert_audit_summary(context: object) -> None:
    """Run the BDD step for assert audit summary.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.audit_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1176")
    if (
        typed_context.shell.audit_state.findings_summary
        != "No supported framework was detected for this project."
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1177")


@then("the audit panel shows a failed status")
def step_assert_audit_failed(context: object) -> None:
    """Run the BDD step for assert audit failed.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.audit_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1200")
    if typed_context.shell.audit_state.status != "failed":
        raise AssertionError


@then("the po processing panel shows a completed status")
def step_assert_po_completed(context: object) -> None:
    """Run the BDD step for assert po completed.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.po_processing_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1218")
    if typed_context.shell.po_processing_state.status != "completed":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1219")


@then("the po processing panel reports the processed family count")
def step_assert_po_family_count(context: object) -> None:
    """Run the BDD step for assert po family count.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.po_processing_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1235")
    if typed_context.shell.po_processing_state.processed_families != PROCESSED_FAMILIES:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1236")


@then("the po processing panel shows a failed status")
def step_assert_po_failed(context: object) -> None:
    """Run the BDD step for assert po failed.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.po_processing_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1258")
    if typed_context.shell.po_processing_state.status != "failed":
        raise AssertionError


@then("the projects list is empty")
def step_assert_empty_projects(context: object) -> None:
    """Run the BDD step for assert empty projects.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.projects_state.projects != []:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1276")


@then("the projects screen shows an empty state message")
def step_assert_empty_state_message(context: object) -> None:
    """Run the BDD step for assert empty state message.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if (
        typed_context.shell.projects_state.empty_message
        != "No projects registered yet."
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1292")


@then("the sync panel shows a failed status")
def step_assert_sync_failed(context: object) -> None:
    """Run the BDD step for assert sync failed.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.sync_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1311")
    if typed_context.shell.sync_state.status != "failed":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1312")


@then("the frontend shell shows the controlled error message")
def step_assert_error_message(context: object) -> None:
    """Run the BDD step for assert error message.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if (
        typed_context.shell.latest_error
        != "Sync preview is unavailable for this project."
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1328")


@then("the frontend shell shows the controlled audit error message")
def step_assert_audit_error_message(context: object) -> None:
    """Run the BDD step for assert audit error message.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if (
        typed_context.shell.latest_error
        != "Audit preview is unavailable for this project."
    ):
        raise AssertionError


@then("the frontend shell shows the controlled translation error message")
def step_assert_translation_error_message(context: object) -> None:
    """Run the BDD step for assert translation error message.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if (
        typed_context.shell.latest_error
        != "Translation workflow is unavailable for this project."
    ):
        raise AssertionError


@then("the settings route is active")
def step_assert_settings_route(context: object) -> None:
    """Run the BDD step for assert settings route.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.router.current.name is not RouteName.SETTINGS:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1395")


@then("the settings screen shows the App / UI / Kivy section")
def step_assert_settings_section(context: object) -> None:
    """Run the BDD step for assert settings section.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1411")
    section_keys = [
        section.key for section in typed_context.shell.settings_state.sections
    ]
    if "app-ui-kivy" not in section_keys:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1415")


@then("the application menu shows the main navigation groups")
def step_assert_application_menu_groups(context: object) -> None:
    """Run the BDD step for assert application menu groups.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    section_keys = [
        section.key for section in typed_context.shell.navigation_menu.sections
    ]
    if section_keys != ["workspace", "operations", "system"]:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1434")


@then("the settings draft uses the default window size")
def step_assert_default_window_size(context: object) -> None:
    """Run the BDD step for assert default window size.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1450")
    if (
        typed_context.shell.settings_state.app_settings.window_width
        != DEFAULT_WINDOW_WIDTH
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1451")
    if (
        typed_context.shell.settings_state.app_settings.window_height
        != DEFAULT_WINDOW_HEIGHT
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1455")


@then("the settings draft keeps remember last screen disabled")
def step_assert_default_remember_last_screen(context: object) -> None:
    """Run the BDD step for assert default remember last screen.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1474")
    if (
        typed_context.shell.settings_state.app_settings.remember_last_screen
        is not False
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1475")


@then("the settings screen shows a single theme selector with explanations")
def step_assert_theme_selector(context: object) -> None:
    """Run the BDD step for assert theme selector.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1491")
    if typed_context.shell.settings_state.theme_mode_field.control_type != "choice":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1492")
    if (
        len(typed_context.shell.settings_state.theme_mode_field.options)
        != THEME_OPTION_COUNT
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1493")
    if typed_context.shell.settings_state.theme_mode_field.help_text == "":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1497")


@then("the settings screen lists UI languages from packaged gettext catalogs")
def step_assert_ui_language_catalog_options(context: object) -> None:
    """Run the BDD step for assert ui language catalog options.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1513")
    options = typed_context.shell.settings_state.ui_language_field.options
    if [option.value for option in options] != ["en", "es"]:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1515")
    if [option.label for option in options] != ["English", "Castellano"]:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1516")


@then("the settings screen shows the changes as saved")
def step_assert_settings_saved(context: object) -> None:
    """Run the BDD step for assert settings saved.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1532")
    if typed_context.shell.settings_state.status != "saved":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1533")


@then("the settings save exposes a saved confirmation message")
def step_assert_settings_saved_message(context: object) -> None:
    """Run the BDD step for assert settings saved message.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1549")
    if typed_context.shell.settings_state.status_message != "Settings saved.":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1550")


@then("the saved settings keep remember last screen enabled")
def step_assert_saved_remember_last_screen(context: object) -> None:
    """Run the BDD step for assert saved remember last screen.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1566")
    if typed_context.shell.settings_state.app_settings.remember_last_screen is not True:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1567")


@then("the saved settings keep the selected window size")
def step_assert_saved_window_size(context: object) -> None:
    """Run the BDD step for assert saved window size.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1583")
    if (
        typed_context.shell.settings_state.app_settings.window_width
        != CUSTOM_WINDOW_WIDTH
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1584")
    if (
        typed_context.shell.settings_state.app_settings.window_height
        != CUSTOM_WINDOW_HEIGHT
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1588")


@then('the saved settings keep UI language "{ui_language}"')
def step_assert_saved_ui_language(context: object, ui_language: str) -> None:
    """Run the BDD step for assert saved ui language.

    Args:
        context:
            Value supplied to this callable.
        ui_language:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1609")
    if typed_context.shell.settings_state.app_settings.ui_language != ui_language:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1610")


@then("the saved settings keep the compact window size")
def step_assert_saved_compact_window_size(context: object) -> None:
    """Run the BDD step for assert saved compact window size.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1626")
    if (
        typed_context.shell.settings_state.app_settings.window_width
        != COMPACT_WINDOW_WIDTH
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1627")
    if (
        typed_context.shell.settings_state.app_settings.window_height
        != COMPACT_WINDOW_HEIGHT
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1631")


@then("the settings draft shows the persisted custom values")
def step_assert_persisted_settings(context: object) -> None:
    """Run the BDD step for assert persisted settings.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1650")
    if typed_context.shell.settings_state.app_settings.theme_mode != "dark":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1651")
    if typed_context.shell.settings_state.app_settings.developer_mode is not True:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1652")
    if typed_context.shell.settings_state.app_settings.remember_last_screen is not True:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1653")
    if (
        typed_context.shell.settings_state.app_settings.window_width
        != CUSTOM_WINDOW_WIDTH
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1654")
    if (
        typed_context.shell.settings_state.app_settings.window_height
        != CUSTOM_WINDOW_HEIGHT
    ):
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1658")


@then("the settings screen shows a failed status")
def step_assert_settings_failed(context: object) -> None:
    """Run the BDD step for assert settings failed.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1677")
    if typed_context.shell.settings_state.status != "failed":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1678")


@then("the frontend shell shows the controlled settings error message")
def step_assert_settings_error_message(context: object) -> None:
    """Run the BDD step for assert settings error message.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.latest_error not in {
        "App settings are temporarily unavailable.",
        "App settings could not be saved.",
    }:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1694")


@then("the settings screen shows the translation settings section")
def step_assert_translation_settings_section(context: object) -> None:
    """Run the BDD step for assert translation settings section.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1713")
    if typed_context.shell.settings_state.selected_section_key != "translation":
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1714")
    if typed_context.shell.settings_state.selected_section_is_available is not True:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1715")


@then('the saved settings keep the default project locale "{default_locale}"')
def step_assert_saved_default_project_locale(
    context: object, default_locale: str
) -> None:
    """Run the BDD step for assert saved default project locale.

    Args:
        context:
            Value supplied to this callable.
        default_locale:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1739")
    if (
        typed_context.shell.settings_state.app_settings.default_project_locale
        != default_locale
    ):
        raise AssertionError


@then("the saved settings keep default MO compilation enabled")
def step_assert_saved_default_mo_compilation_enabled(context: object) -> None:
    """Run the BDD step for assert saved default mo compilation enabled.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1764")
    if typed_context.shell.settings_state.app_settings.default_compile_mo is not True:
        raise AssertionError


@then("the saved settings keep the default external translator disabled")
def step_assert_saved_default_external_translator_disabled(context: object) -> None:
    """Run the BDD step for assert saved default external translator disabled.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1786")
    if (
        typed_context.shell.settings_state.app_settings.default_use_external_translator
        is not False
    ):
        raise AssertionError


@then("the saved settings keep the default translation cache disabled")
def step_assert_saved_default_translation_cache_disabled(context: object) -> None:
    """Run the BDD step for assert saved default translation cache disabled.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1811")
    if (
        typed_context.shell.settings_state.app_settings.default_use_translation_cache
        is not False
    ):
        raise AssertionError


@then('the saved settings keep the translation cache path "{cache_path}"')
def step_assert_saved_translation_cache_path(context: object, cache_path: str) -> None:
    """Run the BDD step for assert saved translation cache path.

    Args:
        context:
            Value supplied to this callable.
        cache_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1838")
    if (
        typed_context.shell.settings_state.app_settings.translation_cache_path
        != cache_path
    ):
        raise AssertionError


@then("the saved settings keep default only-fuzzy mode enabled")
def step_assert_saved_default_only_fuzzy_enabled(context: object) -> None:
    """Run the BDD step for assert saved default only fuzzy enabled.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1863")
    if typed_context.shell.settings_state.app_settings.default_only_fuzzy is not True:
        raise AssertionError


@then("the saved settings keep default dry-run mode enabled")
def step_assert_saved_default_dry_run_enabled(context: object) -> None:
    """Run the BDD step for assert saved default dry run enabled.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1885")
    if typed_context.shell.settings_state.app_settings.default_dry_run is not True:
        raise AssertionError


@then("the saved settings keep default stats-only mode disabled")
def step_assert_saved_default_stats_only_disabled(context: object) -> None:
    """Run the BDD step for assert saved default stats only disabled.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1907")
    if typed_context.shell.settings_state.app_settings.default_stats_only is not False:
        raise AssertionError


@then("the saved settings keep default inconsistency reporting enabled")
def step_assert_saved_default_inconsistency_reporting_enabled(context: object) -> None:
    """Run the BDD step for assert saved default inconsistency reporting enabled.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/frontend_shell_steps.py:1929")
    if (
        typed_context.shell.settings_state.app_settings.default_report_inconsistencies
        is not True
    ):
        raise AssertionError
