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
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel
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
