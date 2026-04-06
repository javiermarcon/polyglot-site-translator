"""Responsive layout helpers for the settings screen."""

from __future__ import annotations

from dataclasses import dataclass

COMPACT_LAYOUT_MAX_WIDTH = 900


@dataclass(frozen=True)
class SettingsLayoutSpec:
    """Layout choices for the settings screen at a given window width."""

    mode: str
    main_columns: int
    sections_width: int | None
    action_orientation: str
    field_row_orientation: str
    toggle_row_orientation: str
    section_button_height: int


def build_settings_layout_spec(window_width: int) -> SettingsLayoutSpec:
    """Return the responsive settings layout for the current window width."""
    if window_width < COMPACT_LAYOUT_MAX_WIDTH:
        return SettingsLayoutSpec(
            mode="compact",
            main_columns=1,
            sections_width=None,
            action_orientation="vertical",
            field_row_orientation="vertical",
            toggle_row_orientation="vertical",
            section_button_height=96,
        )
    return SettingsLayoutSpec(
        mode="wide",
        main_columns=2,
        sections_width=280,
        action_orientation="horizontal",
        field_row_orientation="horizontal",
        toggle_row_orientation="horizontal",
        section_button_height=84,
    )
