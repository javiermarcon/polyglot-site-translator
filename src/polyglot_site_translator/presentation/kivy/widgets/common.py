"""Reusable styled Kivy widgets for the frontend shell."""

from __future__ import annotations

from typing import cast

from kivy.graphics import Color, Line, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from polyglot_site_translator.presentation.kivy.theme import (
    ColorTuple,
    get_active_theme,
)


def apply_theme_to_widget_tree(root_widget: Widget) -> None:
    """Apply the current theme palette to all theme-aware widgets in a tree."""
    if hasattr(root_widget, "apply_theme"):
        root_widget.apply_theme()
    for child in root_widget.children:
        apply_theme_to_widget_tree(child)


def _resolve_color(
    explicit_color: ColorTuple | None,
    color_role: str | None,
    fallback_role: str,
) -> ColorTuple:
    if explicit_color is not None:
        return explicit_color
    palette = get_active_theme()
    role_name = color_role or fallback_role
    return cast(ColorTuple, getattr(palette, role_name))


class SurfaceBoxLayout(BoxLayout):  # type: ignore[misc]
    """BoxLayout with a simple surface background and border."""

    def __init__(
        self,
        *,
        background_color: ColorTuple | None = None,
        background_role: str | None = None,
        border_color: ColorTuple | None = None,
        border_role: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._background_role = background_role
        self._border_role = border_role
        self._background_color = background_color
        self._border_color = border_color
        resolved_background_color = _resolve_color(
            background_color,
            background_role,
            "card_background",
        )
        resolved_border_color = _resolve_color(
            border_color,
            border_role,
            "border_color",
        )
        with self.canvas.before:
            self._background_instruction = Color(*resolved_background_color)
            self._background_rect = Rectangle(pos=self.pos, size=self.size)
            self._border_instruction = Color(*resolved_border_color)
            self._border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=1)
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_args: object) -> None:
        self._background_rect.pos = self.pos
        self._background_rect.size = self.size
        self._border_line.rectangle = (self.x, self.y, self.width, self.height)

    def apply_theme(self) -> None:
        """Re-apply the current palette to this surface."""
        self._background_instruction.rgba = _resolve_color(
            self._background_color,
            self._background_role,
            "card_background",
        )
        self._border_instruction.rgba = _resolve_color(
            self._border_color,
            self._border_role,
            "border_color",
        )


class WrappedLabel(Label):  # type: ignore[misc]
    """Label that wraps text and grows vertically with its content."""

    def __init__(
        self,
        *,
        font_size: int = 16,
        bold: bool = False,
        color: ColorTuple | None = None,
        color_role: str | None = None,
        **kwargs: object,
    ) -> None:
        self._color = color
        self._color_role = color_role
        super().__init__(
            halign="left",
            valign="middle",
            size_hint_y=None,
            color=_resolve_color(color, color_role, "text_primary"),
            font_size=font_size,
            bold=bold,
            **kwargs,
        )
        self.bind(width=self._sync_text_size, texture_size=self._sync_height)
        self._sync_text_size()

    def _sync_text_size(self, *_args: object) -> None:
        self.text_size = (self.width, None)

    def _sync_height(self, *_args: object) -> None:
        self.height = max(self.texture_size[1] + 8, self.font_size + 12)

    def apply_theme(self) -> None:
        """Re-apply the current palette to the label text color."""
        self.color = _resolve_color(self._color, self._color_role, "text_primary")


class AppButton(Button):  # type: ignore[misc]
    """Button with a consistent application style."""

    def __init__(
        self,
        *,
        primary: bool = True,
        **kwargs: object,
    ) -> None:
        resolved_kwargs = dict(kwargs)
        self._primary = primary
        self._uses_theme_background = "background_color" not in resolved_kwargs
        self._uses_theme_text = "color" not in resolved_kwargs
        palette = get_active_theme()
        resolved_kwargs.setdefault(
            "background_color",
            (palette.primary_button_background if primary else palette.secondary_button_background),
        )
        resolved_kwargs.setdefault(
            "color",
            palette.primary_button_text if primary else palette.secondary_button_text,
        )
        resolved_kwargs.setdefault("size_hint_y", None)
        resolved_kwargs.setdefault("height", 44)
        resolved_kwargs.setdefault("background_normal", "")
        resolved_kwargs.setdefault("background_down", "")
        resolved_kwargs.setdefault("halign", "center")
        resolved_kwargs.setdefault("valign", "middle")
        super().__init__(
            **resolved_kwargs,
        )
        self.bind(size=self._sync_text_size)
        self._sync_text_size()

    def apply_theme(self) -> None:
        """Re-apply the current palette to the button colors."""
        palette = get_active_theme()
        if self._uses_theme_background:
            self.background_color = (
                palette.primary_button_background
                if self._primary
                else palette.secondary_button_background
            )
        if self._uses_theme_text:
            self.color = (
                palette.primary_button_text if self._primary else palette.secondary_button_text
            )

    def _sync_text_size(self, *_args: object) -> None:
        self.text_size = (max(self.width - 16, 0), None)
