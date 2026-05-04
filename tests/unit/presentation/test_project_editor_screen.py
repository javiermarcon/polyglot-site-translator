"""Unit tests for the project editor screen helpers and branch behavior."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from kivy.uix.textinput import TextInput
import pytest

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.presentation.kivy.screens.project_editor import (
    _build_information_card,
    _with_rule_enabled,
)
from polyglot_site_translator.presentation.router import RouteName
from polyglot_site_translator.presentation.view_models import (
    RemoteConnectionTestResultViewModel,
    SiteEditorViewModel,
    SyncRuleEditorItemViewModel,
)
from tests.support.frontend_doubles import build_seeded_services


def _build_screen() -> tuple[Any, Any, Any]:
    app = cast(Any, create_kivy_app(services=build_seeded_services()))
    root = app.build()
    screen = root.get_screen("project_editor")
    shell = screen._shell
    shell.open_project_editor_create()
    root.current = "project_editor"
    screen.refresh()
    return app, root, screen


def test_project_editor_screen_renders_remote_error_card_and_retry_button() -> None:
    _app, _root, screen = _build_screen()
    shell = screen._shell

    screen._select_project_editor_section("remote")
    assert shell.project_editor_state is not None
    shell.project_editor_state = replace(
        shell.project_editor_state,
        connection_test_result=RemoteConnectionTestResultViewModel(
            success=False,
            message="Trust the SSH host key before retrying.",
            error_code="unknown_ssh_host_key",
        ),
    )

    screen.refresh()

    label_texts = [widget.text for widget in screen.walk(restrict=True) if hasattr(widget, "text")]
    assert "Remote Connection Test" in label_texts
    assert "Trust SSH Host Key and Retry" in label_texts

    with pytest.raises(
        ValueError,
        match=r"Connection test result is required to build the test card\.",
    ):
        screen._build_remote_connection_test_card(
            replace(shell.project_editor_state, connection_test_result=None)
        )


def test_project_editor_screen_retests_trusted_hosts_and_tracks_test_button_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, _root, screen = _build_screen()
    shell = screen._shell
    screen._select_project_editor_section("remote")
    assert shell.project_editor_state is not None
    screen._connection_type_spinner.text = "FTP"
    screen._remote_host_input.text = "ftp.example.com"
    screen._remote_port_input.text = "21"
    screen._remote_username_input.text = "deploy"
    screen._remote_password_input.text = "secret"
    screen._remote_path_input.text = "/srv/site"

    state = screen._require_state()
    screen._refresh_test_connection_button_state(state)

    test_button = screen._test_connection_button
    if test_button is None:
        msg = "The remote section must expose the connection test button."
        raise AssertionError(msg)
    assert test_button.disabled is False

    screen._remote_port_input.text = "broken"
    screen._refresh_test_connection_button_state(state)
    updated_button = screen._test_connection_button
    if updated_button is None:
        msg = "The remote section must keep the connection test button available."
        raise AssertionError(msg)
    assert updated_button.disabled is True

    captured: list[SiteEditorViewModel] = []
    monkeypatch.setattr(shell, "test_project_connection", captured.append)
    screen._remote_port_input.text = "21"

    screen._retest_connection_with_trusted_host_key()

    assert captured
    assert captured[0].remote_verify_host is False


def test_project_editor_screen_ignores_test_button_refresh_when_button_is_missing() -> None:
    _app, _root, screen = _build_screen()

    screen._select_project_editor_section("remote")
    screen._test_connection_button = None

    screen._refresh_test_connection_button_state(screen._require_state())


def test_project_editor_screen_sync_panels_cover_empty_and_custom_rule_branches() -> None:
    _app, _root, screen = _build_screen()
    shell = screen._shell

    screen._select_project_editor_section("sync")
    empty_texts = [widget.text for widget in screen.walk(restrict=True) if hasattr(widget, "text")]
    assert "No adapter or project sync rules are currently available." in empty_texts

    assert shell.project_editor_state is not None
    shell.project_editor_state = replace(
        shell.project_editor_state,
        editor=replace(
            shell.project_editor_state.editor,
            sync_rule_items=(
                SyncRuleEditorItemViewModel(
                    rule_key="include:file:locale",
                    target_rule_key=None,
                    relative_path="locale",
                    filter_type="file",
                    behavior="include",
                    description="Project locale rule.",
                    source="project",
                    is_enabled=True,
                    is_removable=True,
                ),
                SyncRuleEditorItemViewModel(
                    rule_key="exclude:directory:cache",
                    target_rule_key=None,
                    relative_path="cache",
                    filter_type="directory",
                    behavior="exclude",
                    description="",
                    source="adapter",
                    is_enabled=False,
                    is_removable=False,
                ),
            ),
        ),
    )

    screen.refresh()

    populated_texts = [
        widget.text for widget in screen.walk(restrict=True) if hasattr(widget, "text")
    ]
    assert "Project locale rule." in populated_texts
    assert "Remove" in populated_texts


def test_project_editor_screen_test_connection_helpers_and_back_navigation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, root, screen = _build_screen()
    shell = screen._shell
    screen._select_project_editor_section("remote")
    assert shell.project_editor_state is not None

    screen._connection_type_spinner.text = "FTP"
    screen._remote_host_input.text = "ftp.example.com"
    screen._remote_port_input.text = "21"
    screen._remote_username_input.text = "deploy"
    screen._remote_password_input.text = "secret"
    screen._remote_path_input.text = "/srv/site"

    captured: list[SiteEditorViewModel] = []
    monkeypatch.setattr(shell, "test_project_connection", captured.append)

    screen._test_connection()

    assert captured and captured[0].remote_host == "ftp.example.com"
    assert screen._current_sync_rule_items(screen._require_state()) == ()

    with pytest.raises(ValueError, match=r"Project editor input field is not available\."):
        screen._optional_text(None)
    with pytest.raises(ValueError, match=r"Project editor input field is not available\."):
        screen._require_framework_value(shell.project_editor_state.framework_options, None)

    screen._back_to_projects()

    assert root.current == "projects"


def test_project_editor_helper_functions_cover_information_and_rule_updates() -> None:
    card = _build_information_card(title="Project Editor", body="Nothing loaded yet.")
    item = SyncRuleEditorItemViewModel(
        rule_key="include:directory:locale",
        target_rule_key=None,
        relative_path="locale",
        filter_type="directory",
        behavior="include",
        description="Locale sync rule",
        source="project",
        is_enabled=True,
        is_removable=True,
    )
    updated_item = _with_rule_enabled(item, is_enabled=False)

    card_texts = [widget.text for widget in card.children if hasattr(widget, "text")]
    assert "Project Editor" in card_texts
    assert "Nothing loaded yet." in card_texts
    assert updated_item.is_enabled is False
    assert updated_item.relative_path == item.relative_path


def test_project_editor_screen_covers_sync_rule_mutations_and_refresh_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, _root, screen = _build_screen()
    shell = screen._shell
    screen._select_project_editor_section("sync")
    state = screen._require_state()

    previewed: list[SiteEditorViewModel] = []
    monkeypatch.setattr(shell, "preview_project_editor", previewed.append)
    refresh_calls: list[str] = []
    monkeypatch.setattr(screen, "refresh", lambda: refresh_calls.append("refresh"))

    screen._sync_rule_path_input.text = "locale_custom"
    screen._sync_rule_description_input.text = "Custom locale rule"
    screen._sync_rule_filter_type_spinner.text = "Directory"
    screen._sync_rule_behavior_spinner.text = "Include"
    screen._add_sync_rule(state)

    assert previewed[-1].sync_rule_items[-1].relative_path == "locale_custom"

    shell.project_editor_state = replace(
        shell.project_editor_state,
        editor=replace(
            shell.project_editor_state.editor,
            sync_rule_items=(
                SyncRuleEditorItemViewModel(
                    rule_key="project:locale_custom",
                    target_rule_key=None,
                    relative_path="locale_custom",
                    filter_type="directory",
                    behavior="include",
                    description="Custom locale rule",
                    source="project",
                    is_enabled=True,
                    is_removable=True,
                ),
            ),
        ),
    )
    state = screen._require_state()
    screen._toggle_sync_rule(state, "project:locale_custom", False)
    screen._remove_sync_rule(state, "project:locale_custom")
    screen._refresh_sync_scope()

    assert len(previewed) == 4
    assert refresh_calls == ["refresh", "refresh", "refresh", "refresh"]


def test_project_editor_screen_covers_save_branches_and_section_switch_draft_preservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, _root, screen = _build_screen()
    shell = screen._shell

    created: list[SiteEditorViewModel] = []
    monkeypatch.setattr(shell, "save_new_project", created.append)
    screen._name_input.text = "Draft Site"
    screen._select_project_editor_section("translation")
    assert screen._draft_editor is not None
    assert screen._draft_editor.name == "Draft Site"

    refresh_calls: list[str] = []
    monkeypatch.setattr(screen, "refresh", lambda: refresh_calls.append("refresh"))
    shell.router.go_to(RouteName.PROJECT_EDITOR)
    screen._save_editor()
    assert created and created[0].name == "Draft Site"
    assert refresh_calls == ["refresh"]

    shell.open_project_editor_edit("wp-site")
    screen.refresh()
    edited: list[tuple[str, SiteEditorViewModel]] = []
    monkeypatch.setattr(
        shell,
        "save_project_edits",
        lambda site_id, editor: edited.append((site_id, editor)),
    )
    shell.router.go_to(RouteName.PROJECT_DETAIL, project_id="wp-site")
    screen._save_editor()
    assert edited and edited[0][0] == "wp-site"


def test_project_editor_screen_collect_and_helper_fallback_branches() -> None:
    _app, _root, screen = _build_screen()
    state = screen._require_state()

    screen._use_external_translator_switch = None
    screen._use_adapter_sync_filters_switch = None
    screen._is_active_switch = None
    screen._compile_mo_switch = None
    screen._draft_editor = replace(state.editor, sync_rule_items=())

    collected = screen._collect_editor_from_form(state)

    assert collected.use_external_translator is state.editor.use_external_translator
    assert collected.use_adapter_sync_filters is state.editor.use_adapter_sync_filters
    assert collected.is_active is state.editor.is_active
    assert screen._current_sync_rule_items(state) == ()


def test_project_editor_screen_covers_non_trust_connection_card_and_text_helpers() -> None:
    _app, _root, screen = _build_screen()
    shell = screen._shell

    screen._select_project_editor_section("remote")
    assert shell.project_editor_state is not None
    shell.project_editor_state = replace(
        shell.project_editor_state,
        connection_test_result=RemoteConnectionTestResultViewModel(
            success=False,
            message="Remote login failed.",
            error_code="authentication_failed",
        ),
    )

    card = screen._build_remote_connection_test_card(shell.project_editor_state)
    card_texts = [widget.text for widget in card.walk(restrict=True) if hasattr(widget, "text")]
    assert "Remote Connection Test" in card_texts
    assert "Trust SSH Host Key and Retry" not in card_texts

    text_input = TextInput(text="  project-name  ")
    assert screen._require_text(text_input) == "project-name"

    screen._draft_editor = None
    assert screen._current_sync_rule_items(shell.project_editor_state) == (
        shell.project_editor_state.editor.sync_rule_items
    )
