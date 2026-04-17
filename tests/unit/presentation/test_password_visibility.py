"""Tests for password visibility toggle helpers."""

from __future__ import annotations

from polyglot_site_translator.presentation.kivy.widgets import password_visibility
from polyglot_site_translator.presentation.kivy.widgets.password_visibility import (
    password_visibility_toggle_label,
)


def test_material_icons_font_is_bundled() -> None:
    path = password_visibility._material_icons_font_path()
    assert path.name == "MaterialIcons-Regular.ttf"
    assert path.is_file()


def test_password_visibility_toggle_label_matches_mask_state() -> None:
    # Material Icons: visibility (e8f4), visibility_off (e8f5)
    assert password_visibility_toggle_label(password_masked=True) == "\ue8f4"
    assert password_visibility_toggle_label(password_masked=False) == "\ue8f5"
