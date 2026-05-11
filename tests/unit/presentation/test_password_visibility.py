"""Tests for password visibility toggle helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from kivy.uix.textinput import TextInput
import pytest

from polyglot_site_translator.presentation.kivy.widgets import password_visibility
from polyglot_site_translator.presentation.kivy.widgets.password_visibility import (
    build_password_row_with_visibility_toggle,
    password_visibility_toggle_label,
)


def test_material_icons_font_is_bundled() -> None:
    """Verify material icons font is bundled.

    Returns:
        None: This callable does not return a value.
    """
    path = password_visibility._material_icons_font_path()
    assert path.name == "MaterialIcons-Regular.ttf"
    assert path.is_file()


def test_password_visibility_toggle_label_matches_mask_state() -> None:
    # Material Icons: visibility (e8f4), visibility_off (e8f5)
    """Verify password visibility toggle label matches mask state.

    Returns:
        None: This callable does not return a value.
    """
    assert password_visibility_toggle_label(password_masked=True) == "\ue8f4"
    assert password_visibility_toggle_label(password_masked=False) == "\ue8f5"


def test_material_icons_font_path_raises_when_font_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify material icons font path raises when font is missing.

    Args:
        monkeypatch (pytest.MonkeyPatch): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    monkeypatch.setattr(Path, "is_file", lambda self: False)

    with pytest.raises(FileNotFoundError, match="Bundled Material Icons font not found"):
        password_visibility._material_icons_font_path()


def test_build_password_row_with_visibility_toggle_toggles_mask_state() -> None:
    """Verify build password row with visibility toggle toggles mask state.

    Returns:
        None: This callable does not return a value.
    """
    text_input = TextInput(text="secret", password=True)

    row = build_password_row_with_visibility_toggle(text_input)
    toggle = row.children[0]

    assert cast(Any, text_input).size_hint_x == 0.78
    assert toggle.text == "\ue8f4"

    toggle.dispatch("on_release")
    assert text_input.password is False
    assert toggle.text == "\ue8f5"

    toggle.dispatch("on_release")
    assert bool(text_input.password) is True
    assert toggle.text == "\ue8f4"
