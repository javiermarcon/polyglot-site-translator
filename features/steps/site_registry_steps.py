"""BDD steps for the SQLite-backed site registry flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
import tempfile
from typing import NoReturn, Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.infrastructure.settings import (
    build_default_settings_service,
)
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.view_models import (
    SiteEditorViewModel,
    SyncRuleEditorItemViewModel,
)
from tests.support.frontend_doubles import FailingSiteRegistryCatalogService

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


class BehaveSiteRegistryContext(Protocol):
    """BDD helper for BehaveSiteRegistryContext.

    Attributes:
        shell:
            Documented attribute exposed by this type.
        settings_temp_dir:
            Documented attribute exposed by this type.
        configured_database_directory:
            Documented attribute exposed by this type.
        created_site_id:
            Documented attribute exposed by this type.
    """

    shell: FrontendShell
    settings_temp_dir: tempfile.TemporaryDirectory[str]
    configured_database_directory: str
    created_site_id: str


def _context_with_shell(context: object) -> BehaveSiteRegistryContext:
    """Handle context with shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return cast(BehaveSiteRegistryContext, context)


@given("the frontend shell is wired with SQLite-backed site registry services")
def step_sqlite_site_registry_shell(context: object) -> None:
    """Run the BDD step for sqlite site registry shell.

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
        build_default_frontend_services(settings_service=settings_service)
    )


@given("a site has been registered in the SQLite registry")
def step_registered_site(context: object) -> None:
    """Run the BDD step for registered site.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_create()
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
            default_locale="en_US",
            compile_mo=True,
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:118")
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@given(
    "the frontend shell is wired with SQLite-backed services and invalid "
    "database settings"
)
def step_invalid_database_settings(context: object) -> None:
    """Run the BDD step for invalid database settings.

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
    database_directory = Path(typed_context.settings_temp_dir.name) / "polyglot-db"
    typed_context.configured_database_directory = str(database_directory)
    settings_service.settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_service.settings_path.write_text(
        (
            "[app]\n"
            'theme_mode = "system"\n'
            "window_width = 1280\n"
            "window_height = 720\n"
            "remember_last_screen = false\n"
            'last_opened_screen = "dashboard"\n'
            "developer_mode = false\n"
            'ui_language = "en"\n'
            f'database_directory = "{database_directory}"\n'
            'database_filename = ""\n'
        ),
        encoding="utf-8",
    )
    typed_context.shell = create_frontend_shell(
        build_default_frontend_services(settings_service=settings_service)
    )


@given("the frontend shell is wired with a failing SQLite-backed site registry service")
def step_failing_sqlite_service(context: object) -> None:
    """Run the BDD step for failing sqlite service.

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
        replace(
            build_default_frontend_services(settings_service=settings_service),
            catalog=FailingSiteRegistryCatalogService(),
        )
    )


@when("the operator opens the create project workflow")
def step_open_create_project(context: object) -> None:
    """Run the BDD step for open create project.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_create()


@when("the operator submits a new site registry entry")
def step_submit_new_site(context: object) -> None:
    """Run the BDD step for submit new site.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
            default_locale="en_US",
            compile_mo=True,
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:234")
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when(
    "the operator submits a new site registry entry with adapter sync filters enabled"
)
def step_submit_new_site_with_adapter_sync_filters(context: object) -> None:
    """Run the BDD step for submit new site with adapter sync filters.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Filtered Site",
            framework_type="wordpress",
            local_path="/workspace/filtered-site",
            default_locale="en_US",
            compile_mo=True,
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
            use_adapter_sync_filters=True,
        )
    )
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:271")
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when(
    "the operator submits a new site registry entry with a spaced default locale list"
)
def step_submit_new_site_with_spaced_default_locale_list(context: object) -> None:
    """Run the BDD step for submit new site with spaced default locale list.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
            default_locale="es_ES, es_AR",
            compile_mo=True,
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:307")
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when("the operator submits a new site registry entry with an invalid default locale")
def step_submit_new_site_with_invalid_default_locale(context: object) -> None:
    """Run the BDD step for submit new site with invalid default locale.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
            default_locale="asad@",
            compile_mo=True,
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )


@when(
    "the operator submits a new Django site registry entry with custom "
    "sync rule overrides"
)
def step_submit_django_site_with_custom_sync_rule_overrides(context: object) -> None:
    """Run the BDD step for submit django site with custom sync rule overrides.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    draft = SiteEditorViewModel(
        site_id=None,
        name="Django Filtered Site",
        framework_type="django",
        local_path="/workspace/django-filtered-site",
        default_locale="en_US",
        compile_mo=True,
        connection_type="ftp",
        remote_host="ftp.example.com",
        remote_port="21",
        remote_username="deploy",
        remote_password="super-secret",
        remote_path="/public_html",
        is_active=True,
        use_adapter_sync_filters=True,
    )
    typed_context.shell.preview_project_editor(draft)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:376")
    adjusted_items = (
        *(
            item
            if item.relative_path != "__pycache__"
            else SyncRuleEditorItemViewModel(
                rule_key=item.rule_key,
                target_rule_key=item.target_rule_key,
                relative_path=item.relative_path,
                filter_type=item.filter_type,
                behavior=item.behavior,
                description=item.description,
                source=item.source,
                is_enabled=False,
                is_removable=item.is_removable,
            )
            for item in typed_context.shell.project_editor_state.editor.sync_rule_items
        ),
        SyncRuleEditorItemViewModel(
            rule_key="",
            target_rule_key=None,
            relative_path="locale_custom",
            filter_type="directory",
            behavior="include",
            description="Project locale override",
            source="project",
            is_enabled=True,
            is_removable=True,
        ),
    )
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            **{
                **draft.__dict__,
                "sync_rule_items": adjusted_items,
            }
        )
    )
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:414")
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when("the operator restarts the SQLite-backed frontend shell")
def step_restart_sqlite_shell(context: object) -> None:
    """Run the BDD step for restart sqlite shell.

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
        build_default_frontend_services(settings_service=settings_service)
    )


@when('the operator sets the database directory to "{directory}"')
def step_set_database_directory(context: object, directory: str) -> None:
    """Run the BDD step for set database directory.

    Args:
        context:
            Value supplied to this callable.
        directory:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.configured_database_directory = directory
    typed_context.shell.set_settings_database_directory(directory)


@when("the operator sets the database directory to a temporary directory")
def step_set_temporary_database_directory(context: object) -> None:
    """Run the BDD step for setting a temporary database directory.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    directory = Path(typed_context.settings_temp_dir.name) / "polyglot-db"
    typed_context.configured_database_directory = str(directory)
    typed_context.shell.set_settings_database_directory(str(directory))


@when('the operator sets the database filename to "{filename}"')
def step_set_database_filename(context: object, filename: str) -> None:
    """Run the BDD step for set database filename.

    Args:
        context:
            Value supplied to this callable.
        filename:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_database_filename(filename)


@when("the operator opens the edit project workflow for the persisted site")
def step_open_edit_project(context: object) -> None:
    """Run the BDD step for open edit project.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)


@when("the operator updates the local path and remote connection data")
def step_update_site(context: object) -> None:
    """Run the BDD step for update site.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_project_edits(
        typed_context.created_site_id,
        SiteEditorViewModel(
            site_id=typed_context.created_site_id,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site-v2",
            default_locale="en_US",
            compile_mo=True,
            connection_type="ftp",
            remote_host="ftp-v2.example.com",
            remote_port="21",
            remote_username="deployer",
            remote_password="super-secret-v2",
            remote_path="/public_html/v2",
            is_active=True,
        ),
    )


@when("the operator updates the persisted site to remove the remote connection")
def step_remove_remote_connection(context: object) -> None:
    """Run the BDD step for remove remote connection.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_project_edits(
        typed_context.created_site_id,
        SiteEditorViewModel(
            site_id=typed_context.created_site_id,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site-v2",
            default_locale="en_US",
            compile_mo=True,
            connection_type="none",
            remote_host="",
            remote_port="",
            remote_username="",
            remote_password="",
            remote_path="",
            is_active=True,
        ),
    )


@when("the operator attempts to register another site with the same name")
def step_attempt_duplicate_site_name(context: object) -> None:
    """Run the BDD step for attempt duplicate site name.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_create()
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site-copy",
            default_locale="en_US",
            compile_mo=True,
            connection_type="ftp",
            remote_host="ftp-copy.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html-copy",
            is_active=True,
        )
    )


@then("the project detail route is active for the created site")
def step_assert_created_project_route(context: object) -> None:
    """Run the BDD step for assert created project route.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.router.current.project_id != typed_context.created_site_id:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:603")


@then("the project detail shows the persisted site registry values")
def step_assert_site_detail(context: object) -> None:
    """Run the BDD step for assert site detail.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:621")
    if typed_context.shell.project_detail_state.project.name != "Marketing Site":
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:622")


@then('the project detail shows the persisted default locale "{default_locale}"')
def step_assert_persisted_default_locale(context: object, default_locale: str) -> None:
    """Run the BDD step for assert persisted default locale.

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
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:644")
    if (
        f"Locale: {default_locale}"
        not in typed_context.shell.project_detail_state.configuration_summary
    ):
        raise AssertionError


@then("the projects list shows the persisted SQLite site")
def step_assert_persisted_site_list(context: object) -> None:
    """Run the BDD step for assert persisted site list.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if [project.name for project in typed_context.shell.projects_state.projects] != [
        "Marketing Site"
    ]:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:665")


@then("the project detail shows the updated persisted site registry values")
def step_assert_updated_site_detail(context: object) -> None:
    """Run the BDD step for assert updated site detail.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:683")
    if (
        typed_context.shell.project_detail_state.project.local_path
        != "/workspace/marketing-site-v2"
    ):
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:684")


@then("reopening the persisted site editor shows the updated remote connection values")
def step_assert_updated_remote_connection(context: object) -> None:
    """Run the BDD step for assert updated remote connection.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:703")
    if typed_context.shell.project_editor_state.editor.connection_type != "ftp":
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:704")
    if (
        typed_context.shell.project_editor_state.editor.remote_host
        != "ftp-v2.example.com"
    ):
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:705")
    if typed_context.shell.project_editor_state.editor.remote_port != "21":
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:709")
    if typed_context.shell.project_editor_state.editor.remote_username != "deployer":
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:710")
    if (
        typed_context.shell.project_editor_state.editor.remote_password
        != "super-secret-v2"
    ):
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:711")
    if typed_context.shell.project_editor_state.editor.remote_path != "/public_html/v2":
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:715")


@then(
    "reopening the persisted site editor shows the persisted default "
    'locale "{default_locale}"'
)
def step_assert_reopened_default_locale(context: object, default_locale: str) -> None:
    """Run the BDD step for assert reopened default locale.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:743")
    if typed_context.shell.project_editor_state.editor.default_locale != default_locale:
        raise AssertionError


@then('the project editor uses the default locale "{default_locale}"')
def step_assert_create_editor_default_locale(
    context: object, default_locale: str
) -> None:
    """Run the BDD step for assert create editor default locale.

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
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:769")
    if typed_context.shell.project_editor_state.editor.default_locale != default_locale:
        raise AssertionError


@then("the project editor uses MO compilation disabled")
def step_assert_create_editor_compile_mo_disabled(context: object) -> None:
    """Run the BDD step for assert create editor compile mo disabled.

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
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:791")
    if typed_context.shell.project_editor_state.editor.compile_mo is not False:
        raise AssertionError


@then("the project editor uses the external translator disabled")
def step_assert_create_editor_external_translator_disabled(context: object) -> None:
    """Run the BDD step for assert create editor external translator disabled.

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
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:813")
    if (
        typed_context.shell.project_editor_state.editor.use_external_translator
        is not False
    ):
        raise AssertionError


@then("the project editor uses the translation cache disabled")
def step_assert_create_editor_translation_cache_disabled(context: object) -> None:
    """Run the BDD step for assert create editor translation cache disabled.

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
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:838")
    if (
        typed_context.shell.project_editor_state.editor.use_translation_cache
        is not False
    ):
        raise AssertionError


@then("the project editor uses only-fuzzy mode enabled")
def step_assert_create_editor_only_fuzzy_enabled(context: object) -> None:
    """Run the BDD step for assert create editor only fuzzy enabled.

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
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:863")
    if typed_context.shell.project_editor_state.editor.only_fuzzy is not True:
        raise AssertionError


@then("the project editor uses dry-run mode enabled")
def step_assert_create_editor_dry_run_enabled(context: object) -> None:
    """Run the BDD step for assert create editor dry run enabled.

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
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:885")
    if typed_context.shell.project_editor_state.editor.dry_run is not True:
        raise AssertionError


@then("the project editor uses stats-only mode enabled")
def step_assert_create_editor_stats_only_enabled(context: object) -> None:
    """Run the BDD step for assert create editor stats only enabled.

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
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:907")
    if typed_context.shell.project_editor_state.editor.stats_only is not True:
        raise AssertionError


@then("the project editor uses inconsistency reporting enabled")
def step_assert_create_editor_inconsistency_reporting_enabled(context: object) -> None:
    """Run the BDD step for assert create editor inconsistency reporting enabled.

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
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:929")
    if (
        typed_context.shell.project_editor_state.editor.report_inconsistencies
        is not True
    ):
        raise AssertionError


@then('the project detail shows the persisted sync mode "{mode}"')
def step_assert_persisted_sync_mode(context: object, mode: str) -> None:
    """Run the BDD step for assert persisted sync mode.

    Args:
        context:
            Value supplied to this callable.
        mode:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:956")
    if (
        f"Sync mode: {mode}"
        not in typed_context.shell.project_detail_state.configuration_summary
    ):
        raise AssertionError


@then("reopening the persisted site editor shows adapter sync filters enabled")
def step_assert_persisted_adapter_sync_filters(context: object) -> None:
    """Run the BDD step for assert persisted adapter sync filters.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:982")
    if (
        typed_context.shell.project_editor_state.editor.use_adapter_sync_filters
        is not True
    ):
        raise AssertionError


@when("the operator submits a new site registry entry with MO compilation disabled")
def step_submit_new_site_with_compile_mo_disabled(context: object) -> None:
    """Run the BDD step for submit new site with compile mo disabled.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="No MO Site",
            framework_type="wordpress",
            local_path="/workspace/no-mo-site",
            default_locale="en_US",
            compile_mo=False,
            use_external_translator=True,
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1021")
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when(
    "the operator submits a new site registry entry with external translator disabled"
)
def step_submit_new_site_with_external_translator_disabled(context: object) -> None:
    """Run the BDD step for submit new site with external translator disabled.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="No External Translator Site",
            framework_type="wordpress",
            local_path="/workspace/no-external-translator-site",
            default_locale="en_US",
            compile_mo=True,
            use_external_translator=False,
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1058")
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when("the operator submits a new site registry entry with translation cache disabled")
def step_submit_new_site_with_translation_cache_disabled(context: object) -> None:
    """Run the BDD step for submit new site with translation cache disabled.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="No Translation Cache Site",
            framework_type="wordpress",
            local_path="/workspace/no-translation-cache-site",
            default_locale="en_US",
            compile_mo=True,
            use_external_translator=True,
            use_translation_cache=False,
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1094")
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when(
    "the operator submits a new site registry entry with translation "
    "preview settings enabled"
)
def step_submit_new_site_with_translation_preview_settings(context: object) -> None:
    """Run the BDD step for submit new site with translation preview settings.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Preview Site",
            framework_type="wordpress",
            local_path="/workspace/preview-site",
            default_locale="en_US",
            compile_mo=True,
            use_external_translator=True,
            only_fuzzy=True,
            dry_run=True,
            stats_only=True,
            report_inconsistencies=True,
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1136")
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when("the operator submits a new site registry entry with only-fuzzy mode enabled")
def step_submit_new_site_with_only_fuzzy(context: object) -> None:
    """Run the BDD step for submit new site with only fuzzy.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Only Fuzzy Site",
            framework_type="wordpress",
            local_path="/workspace/only-fuzzy-site",
            default_locale="en_US",
            compile_mo=True,
            use_external_translator=True,
            only_fuzzy=True,
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1172")
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@then("the project detail shows MO compilation disabled")
def step_assert_project_detail_compile_mo_disabled(context: object) -> None:
    """Run the BDD step for assert project detail compile mo disabled.

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
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1193")
    if (
        "Compile MO: disabled"
        not in typed_context.shell.project_detail_state.configuration_summary
    ):
        raise AssertionError


@then("reopening the persisted site editor shows MO compilation disabled")
def step_assert_persisted_compile_mo_disabled(context: object) -> None:
    """Run the BDD step for assert persisted compile mo disabled.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1219")
    if typed_context.shell.project_editor_state.editor.compile_mo is not False:
        raise AssertionError


@then("the project detail shows the external translator disabled")
def step_assert_project_detail_external_translator_disabled(context: object) -> None:
    """Run the BDD step for assert project detail external translator disabled.

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
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1241")
    if (
        "External translator: disabled"
        not in typed_context.shell.project_detail_state.configuration_summary
    ):
        raise AssertionError


@then("the project detail shows the translation cache disabled")
def step_assert_project_detail_translation_cache_disabled(context: object) -> None:
    """Run the BDD step for assert project detail translation cache disabled.

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
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1266")
    if (
        "Translation cache: disabled"
        not in typed_context.shell.project_detail_state.configuration_summary
    ):
        raise AssertionError


@then("the project detail shows only-fuzzy mode enabled")
def step_assert_project_detail_only_fuzzy_enabled(context: object) -> None:
    """Run the BDD step for assert project detail only fuzzy enabled.

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
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1291")
    if (
        "Only fuzzy: enabled"
        not in typed_context.shell.project_detail_state.configuration_summary
    ):
        raise AssertionError


@then("the project detail shows dry-run mode enabled")
def step_assert_project_detail_dry_run_enabled(context: object) -> None:
    """Run the BDD step for assert project detail dry run enabled.

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
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1316")
    if (
        "Dry-run: enabled"
        not in typed_context.shell.project_detail_state.configuration_summary
    ):
        raise AssertionError


@then("the project detail shows stats-only mode enabled")
def step_assert_project_detail_stats_only_enabled(context: object) -> None:
    """Run the BDD step for assert project detail stats only enabled.

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
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1341")
    if (
        "Stats only: enabled"
        not in typed_context.shell.project_detail_state.configuration_summary
    ):
        raise AssertionError


@then("the project detail shows inconsistency reporting enabled")
def step_assert_project_detail_inconsistency_reporting_enabled(context: object) -> None:
    """Run the BDD step for assert project detail inconsistency reporting enabled.

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
    if typed_context.shell.project_detail_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1366")
    if "Report inconsistencies: enabled" not in (
        typed_context.shell.project_detail_state.configuration_summary
    ):
        raise AssertionError


@then("reopening the persisted site editor shows the external translator disabled")
def step_assert_persisted_external_translator_disabled(context: object) -> None:
    """Run the BDD step for assert persisted external translator disabled.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1391")
    if (
        typed_context.shell.project_editor_state.editor.use_external_translator
        is not False
    ):
        raise AssertionError


@then("reopening the persisted site editor shows the translation cache disabled")
def step_assert_persisted_translation_cache_disabled(context: object) -> None:
    """Run the BDD step for assert persisted translation cache disabled.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1417")
    if (
        typed_context.shell.project_editor_state.editor.use_translation_cache
        is not False
    ):
        raise AssertionError


@then("reopening the persisted site editor shows only-fuzzy mode enabled")
def step_assert_persisted_only_fuzzy_enabled(context: object) -> None:
    """Run the BDD step for assert persisted only fuzzy enabled.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1443")
    if typed_context.shell.project_editor_state.editor.only_fuzzy is not True:
        raise AssertionError


@then("reopening the persisted site editor shows dry-run mode enabled")
def step_assert_persisted_dry_run_enabled(context: object) -> None:
    """Run the BDD step for assert persisted dry run enabled.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1466")
    if typed_context.shell.project_editor_state.editor.dry_run is not True:
        raise AssertionError


@then("reopening the persisted site editor shows stats-only mode enabled")
def step_assert_persisted_stats_only_enabled(context: object) -> None:
    """Run the BDD step for assert persisted stats only enabled.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1489")
    if typed_context.shell.project_editor_state.editor.stats_only is not True:
        raise AssertionError


@then("reopening the persisted site editor shows inconsistency reporting enabled")
def step_assert_persisted_inconsistency_reporting_enabled(context: object) -> None:
    """Run the BDD step for assert persisted inconsistency reporting enabled.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1512")
    if (
        typed_context.shell.project_editor_state.editor.report_inconsistencies
        is not True
    ):
        raise AssertionError


@then(
    'reopening the persisted site editor shows the custom sync rule "{relative_path}"'
)
def step_assert_persisted_custom_sync_rule(context: object, relative_path: str) -> None:
    """Run the BDD step for assert persisted custom sync rule.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1542")
    if relative_path not in [
        item.relative_path
        for item in typed_context.shell.project_editor_state.editor.sync_rule_items
    ]:
        raise AssertionError


@then(
    "reopening the persisted site editor shows the adapter rule "
    '"{relative_path}" disabled'
)
def step_assert_persisted_disabled_adapter_rule(
    context: object, relative_path: str
) -> None:
    """Run the BDD step for assert persisted disabled adapter rule.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1575")
    matching_rules = [
        item
        for item in typed_context.shell.project_editor_state.editor.sync_rule_items
        if item.relative_path == relative_path
    ]
    if not (matching_rules and matching_rules[0].is_enabled is False):
        raise AssertionError


@then("the settings draft shows the configured database directory")
def step_assert_database_directory(context: object) -> None:
    """Run the BDD step for assert database directory.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1598")
    if (
        typed_context.shell.settings_state.app_settings.database_directory
        != typed_context.configured_database_directory
    ):
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1599")


@then("the settings draft shows the configured database filename")
def step_assert_database_filename(context: object) -> None:
    """Run the BDD step for assert database filename.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.settings_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1617")
    if (
        typed_context.shell.settings_state.app_settings.database_filename
        != "registry.sqlite3"
    ):
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1618")


@then("the frontend shell shows the controlled site registry error message")
def step_assert_registry_error(context: object) -> None:
    """Run the BDD step for assert registry error.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context_with_shell(context)
    if typed_context.shell.latest_error is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1637")


@then(
    "reopening the persisted site editor shows that no remote connection is configured"
)
def step_assert_reopened_editor_without_remote_connection(context: object) -> None:
    """Run the BDD step for assert reopened editor without remote connection.

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
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1660")
    editor = typed_context.shell.project_editor_state.editor
    if editor.connection_type != "none":
        raise AssertionError
    if editor.remote_host != "":
        raise AssertionError
    if editor.remote_port != "":
        raise AssertionError
    if editor.remote_username != "":
        raise AssertionError
    if editor.remote_password != "":
        raise AssertionError
    if editor.remote_path != "":
        raise AssertionError


@then("the project editor shows the duplicate site-name validation error")
def step_assert_duplicate_site_name_validation_error(context: object) -> None:
    """Run the BDD step for assert duplicate site name validation error.

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
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1693")
    if typed_context.shell.project_editor_state.status != "failed":
        raise AssertionError
    if typed_context.shell.project_editor_state.status_message is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1696")
    if "already exists" not in typed_context.shell.project_editor_state.status_message:
        raise AssertionError
    if typed_context.shell.latest_error == "":
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1699")


@then("the project editor shows the default locale validation error")
def step_assert_default_locale_validation_error(context: object) -> None:
    """Run the BDD step for assert default locale validation error.

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
    if typed_context.shell.project_editor_state is None:
        _raise_bdd_expectation_failure("features/steps/site_registry_steps.py:1719")
    if typed_context.shell.project_editor_state.status != "failed":
        raise AssertionError
    if typed_context.shell.project_editor_state.status_message != (
        "Default locale must be a valid locale or a comma-separated list of valid "
        "locales. Invalid values: asad@."
    ):
        raise AssertionError
