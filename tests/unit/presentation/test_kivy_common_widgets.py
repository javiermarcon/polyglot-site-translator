"""Tests for reusable Kivy widgets used by the frontend shell."""

from __future__ import annotations

from kivy.uix.widget import Widget

from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
    apply_theme_to_widget_tree,
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


def test_app_button_apply_theme_covers_themed_and_explicit_color_branches() -> None:
    themed_button = AppButton(text="Themed")
    themed_button.apply_theme()

    explicit_button = AppButton(
        text="Explicit",
        background_color=(0.1, 0.2, 0.3, 1.0),
        color=(0.8, 0.7, 0.6, 1.0),
    )
    explicit_background = tuple(explicit_button.background_color)
    explicit_text = tuple(explicit_button.color)

    explicit_button.apply_theme()

    assert themed_button.text_size[0] >= 0
    assert tuple(explicit_button.background_color) == explicit_background
    assert tuple(explicit_button.color) == explicit_text


def test_apply_theme_to_widget_tree_calls_theme_aware_widgets_recursively() -> None:
    parent = SurfaceBoxLayout()
    child = WrappedLabel(text="Nested label")
    parent.add_widget(child)

    apply_theme_to_widget_tree(parent)

    assert tuple(parent._background_instruction.rgba) == tuple(parent._background_instruction.rgba)
    assert tuple(child.color) == tuple(child.color)


def test_apply_theme_to_widget_tree_skips_widgets_without_apply_theme() -> None:
    root = Widget()
    root.add_widget(WrappedLabel(text="Child"))

    apply_theme_to_widget_tree(root)

    assert len(root.children) == 1
