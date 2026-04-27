"""Unit tests for the project editor screen helpers and branch behavior."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

import pytest

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.presentation.kivy.screens.project_editor import (
    _build_information_card,
    _with_rule_enabled,
)
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
