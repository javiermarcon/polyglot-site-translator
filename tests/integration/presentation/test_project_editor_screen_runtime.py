"""Integration tests for the project editor and detail screen runtime behavior."""

from __future__ import annotations

from typing import Any, cast

from kivy.uix.spinner import Spinner
import pytest

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.presentation.kivy.screens.project_editor import (
    _find_option_label,
    _find_option_value,
)
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel
from tests.support.frontend_doubles import build_seeded_services


def test_project_editor_screen_renders_empty_state_and_requires_loaded_state() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    editor_screen = root.get_screen("project_editor")

    editor_screen._shell.project_editor_state = None
    editor_screen.refresh()

    label_texts = [
        widget.text
        for widget in editor_screen._content.children[0].children
        if hasattr(widget, "text")
    ]
    assert "Open the register or edit workflow to load a project editor draft." in label_texts
    with pytest.raises(
        ValueError,
        match=r"Project editor state must be loaded before rendering the screen\.",
    ):
        editor_screen._require_state()

    with pytest.raises(
        ValueError,
        match=r"Project editor input field is not available\.",
    ):
        editor_screen._require_text(None)

    with pytest.raises(
        ValueError,
        match=r"Project editor input field is not available\.",
    ):
        editor_screen._require_framework_value([], None)

    with pytest.raises(LookupError, match="Unknown option value: tornado"):
        _find_option_label([], "tornado")

    with pytest.raises(LookupError, match="Unknown option label: Tornado"):
        _find_option_value([], "Tornado")


def test_project_editor_screen_saves_new_projects_and_can_return_to_projects() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    editor_screen = root.get_screen("project_editor")
    shell = editor_screen._shell

    shell.open_project_editor_create()
    root.current = "project_editor"
    editor_screen.refresh()
    editor_screen._name_input.text = "New Project"
    editor_screen._framework_spinner.text = "Django"
    editor_screen._local_path_input.text = "/workspace/new-project"
    editor_screen._default_locale_input.text = "en_US"
    editor_screen._connection_type_spinner.text = "FTP"
    editor_screen._remote_host_input.text = "ftp.example.com"
    editor_screen._remote_port_input.text = "21"
    editor_screen._remote_username_input.text = "deploy"
    editor_screen._remote_password_input.text = "super-secret"
    editor_screen._remote_path_input.text = "/srv/new-project"
    editor_screen._is_active_switch.active = False

    editor_screen._save_editor()

    assert root.current == "project_detail"
    assert shell.project_detail_state is not None
    assert shell.project_detail_state.project.name == "New Project"
    assert shell.project_detail_state.project.status == "Inactive"

    editor_screen._back_to_projects()
    assert root.current == "projects"


def test_project_editor_screen_exposes_dynamic_framework_options() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    editor_screen = root.get_screen("project_editor")
    shell = editor_screen._shell

    shell.open_project_editor_create()
    root.current = "project_editor"
    editor_screen.refresh()

    assert editor_screen._framework_spinner is not None
    assert isinstance(editor_screen._framework_spinner, Spinner)
    assert editor_screen._framework_spinner.text == "Unknown"
    assert tuple(editor_screen._framework_spinner.values) == (
        "Unknown",
        "Django",
        "Flask",
        "WordPress",
    )
    assert (
        _find_option_label(shell.project_editor_state.framework_options, "wordpress") == "WordPress"
    )
    assert _find_option_value(shell.project_editor_state.framework_options, "Flask") == "flask"
    assert tuple(editor_screen._connection_type_spinner.values) == (
        "No Remote Connection",
        "FTP",
        "FTPS Explicit",
        "FTPS Implicit",
        "SCP",
        "SFTP",
    )


def test_project_editor_screen_saves_edits_and_refreshes_when_not_routed_to_detail() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    detail_screen = root.get_screen("project_detail")
    editor_screen = root.get_screen("project_editor")
    shell = editor_screen._shell

    shell.open_projects()
    shell.select_project("wp-site")
    detail_screen._edit_project()
    editor_screen.refresh()
    assert root.current == "project_editor"

    editor_screen._local_path_input.text = "/workspace/marketing-site-v2"
    editor_screen._connection_type_spinner.text = "FTP"
    editor_screen._remote_host_input.text = "ftp-v2.example.com"
    editor_screen._remote_port_input.text = "21"
    editor_screen._remote_username_input.text = "deploy"
    editor_screen._remote_password_input.text = "super-secret"
    editor_screen._remote_path_input.text = "/public_html"
    editor_screen._save_editor()

    assert root.current == "project_detail"
    assert shell.project_detail_state is not None
    assert shell.project_detail_state.project.local_path == "/workspace/marketing-site-v2"

    refresh_calls: list[str] = []

    def record_refresh() -> None:
        refresh_calls.append("refresh")

    def keep_editor_route(_editor: SiteEditorViewModel) -> None:
        shell.router.go_to(shell.router.current.name)

    shell.open_project_editor_create()
    root.current = "project_editor"
    editor_screen.refresh()
    editor_screen.refresh = record_refresh
    shell.save_new_project = keep_editor_route
    editor_screen._save_editor()

    assert root.current == "project_editor"
    assert refresh_calls == ["refresh"]


def test_project_detail_screen_edit_button_ignores_missing_detail_and_opens_editor() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    detail_screen = root.get_screen("project_detail")
    editor_screen = root.get_screen("project_editor")
    shell = detail_screen._shell

    shell.project_detail_state = None
    detail_screen._edit_project()
    assert root.current == "dashboard"

    shell.open_projects()
    shell.select_project("wp-site")
    detail_screen._edit_project()

    assert root.current == "project_editor"
    assert editor_screen._shell.project_editor_state is not None


def test_project_editor_screen_uses_save_new_project_when_site_id_is_missing_in_edit_mode() -> None:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    editor_screen = root.get_screen("project_editor")
    shell = editor_screen._shell
    calls: list[tuple[str, SiteEditorViewModel]] = []

    def record_create(editor: SiteEditorViewModel) -> None:
        calls.append(("create", editor))

    shell.open_project_editor_create()
    shell.project_editor_state = shell.project_editor_state.__class__(
        mode="edit",
        title="Edit Project",
        submit_label="Save Changes",
        editor=SiteEditorViewModel(
            **{**shell.project_editor_state.editor.__dict__, "site_id": None}
        ),
        framework_options=shell.project_editor_state.framework_options,
        connection_type_options=shell.project_editor_state.connection_type_options,
        connection_test_enabled=shell.project_editor_state.connection_test_enabled,
        connection_test_result=shell.project_editor_state.connection_test_result,
        status="editing",
        status_message="Update the persisted site registry record.",
    )
    editor_screen.refresh()
    shell.save_new_project = record_create

    editor_screen._save_editor()

    assert calls and calls[0][0] == "create"
