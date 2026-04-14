"""Unit tests for settings-screen sync rule helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
import pytest

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScopeSettings,
    ConfiguredSyncRule,
    FrameworkSyncRuleSet,
    SyncFilterType,
    SyncRuleBehavior,
)
from polyglot_site_translator.presentation.kivy.screens.settings import (
    _append_framework_rule,
    _build_configured_rule,
    _map_behavior_label,
    _map_filter_type_label,
    _remove_configured_rule,
    _toggle_configured_rule,
)


def test_build_configured_rule_normalizes_values_and_rejects_empty_paths() -> None:
    configured_rule = _build_configured_rule(
        relative_path=" /.cache/ ",
        description="",
        filter_type_label="Glob",
        behavior_label="Exclude",
    )

    assert configured_rule.relative_path == ".cache"
    assert configured_rule.description == ".cache"
    assert configured_rule.filter_type is SyncFilterType.GLOB
    assert configured_rule.behavior is SyncRuleBehavior.EXCLUDE

    with pytest.raises(ValueError, match="Sync rules require a non-empty relative path"):
        _build_configured_rule(
            relative_path=" / ",
            description="ignored",
            filter_type_label="Directory",
            behavior_label="Include",
        )


def test_settings_screen_rule_label_helpers_validate_unknown_values() -> None:
    assert _map_filter_type_label("Directory") is SyncFilterType.DIRECTORY
    assert _map_behavior_label("Exclude") is SyncRuleBehavior.EXCLUDE

    with pytest.raises(ValueError, match="Unsupported filter type label"):
        _map_filter_type_label("Broken")

    with pytest.raises(ValueError, match="Unsupported behavior label"):
        _map_behavior_label("Broken")


def test_append_toggle_and_remove_framework_sync_rules() -> None:
    sync_scope_settings = AdapterSyncScopeSettings()
    framework_rule = ConfiguredSyncRule(
        relative_path=".venv",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.EXCLUDE,
        description="Ignore virtualenv.",
        is_enabled=True,
    )
    sync_scope_settings = _append_framework_rule(
        sync_scope_settings,
        framework_type="django",
        rule=framework_rule,
    )
    toggled_settings = _toggle_configured_rule(
        sync_scope_settings,
        relative_path=".venv",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.EXCLUDE,
        new_enabled=False,
        scope_type="framework",
        framework_type="django",
    )
    removed_settings = _remove_configured_rule(
        toggled_settings,
        relative_path=".venv",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.EXCLUDE,
        scope_type="framework",
        framework_type="django",
    )

    assert toggled_settings.framework_rule_sets[0].rules[0].is_enabled is False
    assert removed_settings.framework_rule_sets == ()

    with pytest.raises(ValueError, match="Framework sync rules require a non-empty framework type"):
        _append_framework_rule(
            AdapterSyncScopeSettings(),
            framework_type=" ",
            rule=framework_rule,
        )


def test_toggle_and_remove_global_sync_rules() -> None:
    sync_scope_settings = AdapterSyncScopeSettings(
        global_rules=(
            ConfiguredSyncRule(
                relative_path=".git",
                filter_type=SyncFilterType.DIRECTORY,
                behavior=SyncRuleBehavior.EXCLUDE,
                description="Ignore Git.",
                is_enabled=True,
            ),
        )
    )

    toggled_settings = _toggle_configured_rule(
        sync_scope_settings,
        relative_path=".git",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.EXCLUDE,
        new_enabled=False,
        scope_type="global",
        framework_type=None,
    )
    removed_settings = _remove_configured_rule(
        toggled_settings,
        relative_path=".git",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.EXCLUDE,
        scope_type="global",
        framework_type=None,
    )

    assert toggled_settings.global_rules[0].is_enabled is False
    assert removed_settings.global_rules == ()


def test_toggle_and_remove_framework_rules_require_framework_type() -> None:
    with pytest.raises(ValueError, match="Framework sync rules require a framework type"):
        _toggle_configured_rule(
            AdapterSyncScopeSettings(
                framework_rule_sets=(
                    FrameworkSyncRuleSet(
                        framework_type="django",
                        rules=(),
                    ),
                )
            ),
            relative_path=".venv",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.EXCLUDE,
            new_enabled=False,
            scope_type="framework",
            framework_type=None,
        )

    with pytest.raises(ValueError, match="Framework sync rules require a framework type"):
        _remove_configured_rule(
            AdapterSyncScopeSettings(
                framework_rule_sets=(
                    FrameworkSyncRuleSet(
                        framework_type="django",
                        rules=(),
                    ),
                )
            ),
            relative_path=".venv",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.EXCLUDE,
            scope_type="framework",
            framework_type=None,
        )


def test_settings_screen_requires_existing_inputs_for_helper_access() -> None:
    app = cast(Any, create_kivy_app())
    root = app.build()
    settings_screen = root.get_screen("settings")

    with pytest.raises(ValueError, match="Text input must exist"):
        settings_screen._require_text_input(None)

    with pytest.raises(ValueError, match="Spinner must exist"):
        settings_screen._require_spinner(None)

    assert isinstance(settings_screen._require_text_input(TextInput()), TextInput)
    assert isinstance(settings_screen._require_spinner(Spinner()), Spinner)


def test_settings_screen_toggle_and_remove_helpers_update_the_local_draft() -> None:
    app = cast(Any, create_kivy_app())
    root = app.build()
    settings_screen = root.get_screen("settings")
    settings_screen._shell.open_settings()
    settings_screen._select_settings_section("frameworks")
    draft = settings_screen._require_draft()
    settings_screen._draft_settings = replace(
        draft,
        sync_scope_settings=replace(
            draft.sync_scope_settings,
            framework_rule_sets=(
                FrameworkSyncRuleSet(
                    framework_type="django",
                    rules=(
                        ConfiguredSyncRule(
                            relative_path=".venv",
                            filter_type=SyncFilterType.DIRECTORY,
                            behavior=SyncRuleBehavior.EXCLUDE,
                            description="Ignore virtualenv.",
                            is_enabled=True,
                        ),
                    ),
                ),
            ),
        ),
    )
    settings_screen._toggle_use_gitignore_rules(
        _widget=object(),
        value=True,
        state_label=cast(Any, type("Label", (), {"text": ""})()),
    )
    settings_screen._toggle_configured_rule(
        relative_path=".venv",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.EXCLUDE,
        is_enabled=True,
        scope_type="framework",
        framework_type="django",
    )
    settings_screen._remove_configured_rule(
        relative_path=".venv",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.EXCLUDE,
        scope_type="framework",
        framework_type="django",
    )

    updated_draft = settings_screen._require_draft()

    assert updated_draft.sync_scope_settings.use_gitignore_rules is True
    assert updated_draft.sync_scope_settings.framework_rule_sets == ()
