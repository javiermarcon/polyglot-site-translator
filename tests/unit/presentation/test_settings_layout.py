"""Unit tests for responsive settings layout decisions."""

from __future__ import annotations

from polyglot_site_translator.presentation.kivy.settings_layout import (
    build_settings_layout_spec,
)


def test_build_settings_layout_spec_uses_compact_mode_for_narrow_windows() -> None:
    layout_spec = build_settings_layout_spec(550)

    assert layout_spec.mode == "compact"
    assert layout_spec.main_columns == 1
    assert layout_spec.sections_width is None
    assert layout_spec.action_orientation == "vertical"
    assert layout_spec.field_row_orientation == "vertical"
    assert layout_spec.toggle_row_orientation == "vertical"


def test_build_settings_layout_spec_uses_wide_mode_for_desktop_windows() -> None:
    layout_spec = build_settings_layout_spec(1280)

    assert layout_spec.mode == "wide"
    assert layout_spec.main_columns == 2
    assert layout_spec.sections_width == 280
    assert layout_spec.action_orientation == "horizontal"
