"""Additional tests for presentation view model builders."""

from __future__ import annotations

import pytest

from polyglot_site_translator.domain.remote_connections.models import RemoteConnectionTypeDescriptor
from polyglot_site_translator.presentation.view_models import (
    build_connection_type_options,
    build_default_app_settings,
    build_default_site_editor,
    build_project_editor_state,
    build_settings_sections,
    build_settings_state,
    build_sync_rule_behavior_options,
    build_sync_rule_filter_type_options,
    select_project_editor_section,
)


def test_build_settings_state_rejects_unknown_section_keys() -> None:
    with pytest.raises(LookupError, match="Unknown settings section: unsupported"):
        build_settings_state(
            app_settings=build_default_app_settings(),
            status="loaded",
            status_message=None,
            selected_section_key="unsupported",
        )


def test_build_settings_sections_exposes_translation_settings_as_available() -> None:
    sections = {section.key: section for section in build_settings_sections()}

    assert sections["translation"].is_available is True


def test_build_project_editor_state_defaults_to_general_section() -> None:
    state = build_project_editor_state(
        mode="create",
        editor=build_default_site_editor(),
        framework_options=[],
        connection_type_options=build_connection_type_options(
            descriptors=(
                RemoteConnectionTypeDescriptor(
                    connection_type="none",
                    display_name="No Remote Connection",
                    default_port=0,
                ),
            )
        ),
        sync_rule_filter_type_options=build_sync_rule_filter_type_options(),
        sync_rule_behavior_options=build_sync_rule_behavior_options(),
        connection_test_enabled=False,
        connection_test_result=None,
        sync_scope_status="unavailable",
        sync_scope_message="Sync scope unavailable.",
        status="editing",
        status_message="Draft ready.",
    )

    assert state.selected_section_key == "general"


def test_select_project_editor_section_updates_only_the_selected_tab() -> None:
    state = build_project_editor_state(
        mode="create",
        editor=build_default_site_editor(default_locale="es_ES"),
        framework_options=[],
        connection_type_options=build_connection_type_options(
            descriptors=(
                RemoteConnectionTypeDescriptor(
                    connection_type="none",
                    display_name="No Remote Connection",
                    default_port=0,
                ),
            )
        ),
        sync_rule_filter_type_options=build_sync_rule_filter_type_options(),
        sync_rule_behavior_options=build_sync_rule_behavior_options(),
        connection_test_enabled=False,
        connection_test_result=None,
        sync_scope_status="unavailable",
        sync_scope_message="Sync scope unavailable.",
        status="editing",
        status_message="Draft ready.",
    )

    translation_state = select_project_editor_section(state, section_key="translation")

    assert translation_state.selected_section_key == "translation"
    assert translation_state.selected_section_title == "Translation Settings"
    assert translation_state.editor.default_locale == "es_ES"
    assert translation_state.editor is state.editor


def test_select_project_editor_section_rejects_unknown_section_keys() -> None:
    state = build_project_editor_state(
        mode="create",
        editor=build_default_site_editor(),
        framework_options=[],
        connection_type_options=build_connection_type_options(
            descriptors=(
                RemoteConnectionTypeDescriptor(
                    connection_type="none",
                    display_name="No Remote Connection",
                    default_port=0,
                ),
            )
        ),
        sync_rule_filter_type_options=build_sync_rule_filter_type_options(),
        sync_rule_behavior_options=build_sync_rule_behavior_options(),
        connection_test_enabled=False,
        connection_test_result=None,
        sync_scope_status="unavailable",
        sync_scope_message="Sync scope unavailable.",
        status="editing",
        status_message="Draft ready.",
    )

    with pytest.raises(LookupError, match="Unknown project editor section: advanced"):
        select_project_editor_section(state, section_key="advanced")
