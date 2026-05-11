"""Unit tests for runtime theme resolution."""

from __future__ import annotations

import pytest

from polyglot_site_translator.presentation.kivy.theme import (
    get_active_theme_mode,
    normalize_theme_mode,
    resolve_theme_palette,
    set_active_theme_mode,
)


def test_system_theme_mode_normalizes_to_light() -> None:
    """Verify system theme mode normalizes to light.

    Returns:
        None: This callable does not return a value.
    """
    assert normalize_theme_mode("system") == "light"
    assert resolve_theme_palette("system") == resolve_theme_palette("light")


def test_setting_active_theme_mode_updates_runtime_theme_state() -> None:
    """Verify setting active theme mode updates runtime theme state.

    Returns:
        None: This callable does not return a value.
    """
    set_active_theme_mode("dark")

    assert get_active_theme_mode() == "dark"

    set_active_theme_mode("light")


def test_invalid_theme_mode_raises_value_error() -> None:
    """Verify invalid theme mode raises value error.

    Returns:
        None: This callable does not return a value.
    """
    with pytest.raises(ValueError, match="Unsupported theme mode: neon"):
        normalize_theme_mode("neon")
