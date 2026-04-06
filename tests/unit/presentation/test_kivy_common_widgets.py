"""Tests for reusable Kivy widgets used by the frontend shell."""

from __future__ import annotations

from polyglot_site_translator.presentation.kivy.widgets.common import AppButton


def test_app_button_allows_overriding_height_and_size_hint() -> None:
    button = AppButton(
        text="Settings Section",
        primary=False,
        height=76,
        size_hint_y=None,
    )

    assert button.height == 76
    assert button.size_hint_y is None
