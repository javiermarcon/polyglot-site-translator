"""Tests for reusable Kivy widgets used by the frontend shell."""

from __future__ import annotations

from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
)


def test_app_button_allows_overriding_height_and_size_hint() -> None:
    button = AppButton(
        text="Settings Section",
        primary=False,
        height=76,
        size_hint_y=None,
    )

    assert button.height == 76
    assert button.size_hint_y is None


def test_wrapped_label_and_surface_layout_support_explicit_colors() -> None:
    surface = SurfaceBoxLayout(
        background_color=(0.1, 0.2, 0.3, 1.0),
        border_color=(0.9, 0.8, 0.7, 1.0),
    )
    label = WrappedLabel(text="Hello world", color=(0.3, 0.4, 0.5, 1.0))

    label.texture_update()
    label._sync_height()
    surface.apply_theme()
    label.apply_theme()

    assert tuple(surface._background_instruction.rgba) == (0.1, 0.2, 0.3, 1.0)
    assert tuple(surface._border_instruction.rgba) == (0.9, 0.8, 0.7, 1.0)
    assert tuple(label.color) == (0.3, 0.4, 0.5, 1.0)
    assert label.height >= label.font_size + 12
