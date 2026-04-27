"""BDD steps for the SQLite-backed site registry flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
import tempfile
from typing import Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.view_models import (
    SiteEditorViewModel,
    SyncRuleEditorItemViewModel,
)
from tests.support.frontend_doubles import FailingSiteRegistryCatalogService

StepFunction = TypeVar("StepFunction", bound=Callable[..., object])

given = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.given)
when = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.when)
then = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.then)


class BehaveSiteRegistryContext(Protocol):
    """Typed subset of behave context used by the site registry feature."""

    shell: FrontendShell
    settings_temp_dir: tempfile.TemporaryDirectory[str]
    created_site_id: str


def _context_with_shell(context: object) -> BehaveSiteRegistryContext:
    return cast(BehaveSiteRegistryContext, context)


@given("the frontend shell is wired with SQLite-backed site registry services")
def step_sqlite_site_registry_shell(context: object) -> None:
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
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_create()
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
            default_locale="en_US",
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    assert typed_context.shell.project_detail_state is not None
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@given("the frontend shell is wired with SQLite-backed services and invalid database settings")
def step_invalid_database_settings(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.settings_temp_dir = tempfile.TemporaryDirectory()
    settings_service = build_default_settings_service(
        config_dir=Path(typed_context.settings_temp_dir.name)
    )
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
            'database_directory = "/tmp/polyglot-db"\n'
            'database_filename = ""\n'
        ),
        encoding="utf-8",
    )
    typed_context.shell = create_frontend_shell(
        build_default_frontend_services(settings_service=settings_service)
    )


@given("the frontend shell is wired with a failing SQLite-backed site registry service")
def step_failing_sqlite_service(context: object) -> None:
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
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_create()


@when("the operator submits a new site registry entry")
def step_submit_new_site(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
            default_locale="en_US",
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    assert typed_context.shell.project_detail_state is not None
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when("the operator submits a new site registry entry with adapter sync filters enabled")
def step_submit_new_site_with_adapter_sync_filters(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Filtered Site",
            framework_type="wordpress",
            local_path="/workspace/filtered-site",
            default_locale="en_US",
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
    assert typed_context.shell.project_detail_state is not None
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when("the operator submits a new site registry entry with a spaced default locale list")
def step_submit_new_site_with_spaced_default_locale_list(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
            default_locale="es_ES, es_AR",
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )
    assert typed_context.shell.project_detail_state is not None
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when("the operator submits a new site registry entry with an invalid default locale")
def step_submit_new_site_with_invalid_default_locale(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
            default_locale="asad@",
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )


@when("the operator submits a new Django site registry entry with custom sync rule overrides")
def step_submit_django_site_with_custom_sync_rule_overrides(context: object) -> None:
    typed_context = _context_with_shell(context)
    draft = SiteEditorViewModel(
        site_id=None,
        name="Django Filtered Site",
        framework_type="django",
        local_path="/workspace/django-filtered-site",
        default_locale="en_US",
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
    assert typed_context.shell.project_editor_state is not None
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
    assert typed_context.shell.project_detail_state is not None
    typed_context.created_site_id = typed_context.shell.project_detail_state.project.id


@when("the operator restarts the SQLite-backed frontend shell")
def step_restart_sqlite_shell(context: object) -> None:
    typed_context = _context_with_shell(context)
    settings_service = build_default_settings_service(
        config_dir=Path(typed_context.settings_temp_dir.name)
    )
    typed_context.shell = create_frontend_shell(
        build_default_frontend_services(settings_service=settings_service)
    )


@when('the operator sets the database directory to "{directory}"')
def step_set_database_directory(context: object, directory: str) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_database_directory(directory)


@when('the operator sets the database filename to "{filename}"')
def step_set_database_filename(context: object, filename: str) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.set_settings_database_filename(filename)


@when("the operator opens the edit project workflow for the persisted site")
def step_open_edit_project(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)


@when("the operator updates the local path and remote connection data")
def step_update_site(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.save_project_edits(
        typed_context.created_site_id,
        SiteEditorViewModel(
            site_id=typed_context.created_site_id,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site-v2",
            default_locale="en_US",
            connection_type="ftp",
            remote_host="ftp-v2.example.com",
            remote_port="21",
            remote_username="deployer",
            remote_password="super-secret-v2",
            remote_path="/public_html/v2",
            is_active=True,
        ),
    )


@then("the project detail route is active for the created site")
def step_assert_created_project_route(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.router.current.project_id == typed_context.created_site_id


@then("the project detail shows the persisted site registry values")
def step_assert_site_detail(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_detail_state is not None
    assert typed_context.shell.project_detail_state.project.name == "Marketing Site"


@then('the project detail shows the persisted default locale "{default_locale}"')
def step_assert_persisted_default_locale(context: object, default_locale: str) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_detail_state is not None
    assert (
        f"Locale: {default_locale}"
        in typed_context.shell.project_detail_state.configuration_summary
    )


@then("the projects list shows the persisted SQLite site")
def step_assert_persisted_site_list(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert [project.name for project in typed_context.shell.projects_state.projects] == [
        "Marketing Site"
    ]


@then("the project detail shows the updated persisted site registry values")
def step_assert_updated_site_detail(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_detail_state is not None
    assert typed_context.shell.project_detail_state.project.local_path == (
        "/workspace/marketing-site-v2"
    )


@then("reopening the persisted site editor shows the updated remote connection values")
def step_assert_updated_remote_connection(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    assert typed_context.shell.project_editor_state is not None
    assert typed_context.shell.project_editor_state.editor.connection_type == "ftp"
    assert typed_context.shell.project_editor_state.editor.remote_host == "ftp-v2.example.com"
    assert typed_context.shell.project_editor_state.editor.remote_port == "21"
    assert typed_context.shell.project_editor_state.editor.remote_username == "deployer"
    assert typed_context.shell.project_editor_state.editor.remote_password == "super-secret-v2"
    assert typed_context.shell.project_editor_state.editor.remote_path == "/public_html/v2"


@then('reopening the persisted site editor shows the persisted default locale "{default_locale}"')
def step_assert_reopened_default_locale(context: object, default_locale: str) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    assert typed_context.shell.project_editor_state is not None
    assert typed_context.shell.project_editor_state.editor.default_locale == default_locale


@then('the project editor uses the default locale "{default_locale}"')
def step_assert_create_editor_default_locale(context: object, default_locale: str) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_editor_state is not None
    assert typed_context.shell.project_editor_state.editor.default_locale == default_locale


@then('the project detail shows the persisted sync mode "{mode}"')
def step_assert_persisted_sync_mode(context: object, mode: str) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_detail_state is not None
    assert f"Sync mode: {mode}" in typed_context.shell.project_detail_state.configuration_summary


@then("reopening the persisted site editor shows adapter sync filters enabled")
def step_assert_persisted_adapter_sync_filters(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    assert typed_context.shell.project_editor_state is not None
    assert typed_context.shell.project_editor_state.editor.use_adapter_sync_filters is True


@then('reopening the persisted site editor shows the custom sync rule "{relative_path}"')
def step_assert_persisted_custom_sync_rule(context: object, relative_path: str) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    assert typed_context.shell.project_editor_state is not None
    assert relative_path in [
        item.relative_path
        for item in typed_context.shell.project_editor_state.editor.sync_rule_items
    ]


@then('reopening the persisted site editor shows the adapter rule "{relative_path}" disabled')
def step_assert_persisted_disabled_adapter_rule(context: object, relative_path: str) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_edit(typed_context.created_site_id)
    assert typed_context.shell.project_editor_state is not None
    matching_rules = [
        item
        for item in typed_context.shell.project_editor_state.editor.sync_rule_items
        if item.relative_path == relative_path
    ]
    assert matching_rules and matching_rules[0].is_enabled is False


@then("the settings draft shows the configured database directory")
def step_assert_database_directory(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.app_settings.database_directory == (
        "/tmp/polyglot-db"
    )


@then("the settings draft shows the configured database filename")
def step_assert_database_filename(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.settings_state is not None
    assert typed_context.shell.settings_state.app_settings.database_filename == "registry.sqlite3"


@then("the frontend shell shows the controlled site registry error message")
def step_assert_registry_error(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.latest_error is not None
    assert typed_context.shell.latest_error != ""


@then("the project editor shows the default locale validation error")
def step_assert_default_locale_validation_error(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_editor_state is not None
    assert typed_context.shell.project_editor_state.status == "failed"
    assert typed_context.shell.project_editor_state.status_message == (
        "Default locale must be a valid locale or a comma-separated list of valid "
        "locales. Invalid values: asad@."
    )
