"""Reusable styled Kivy widgets for the frontend shell.

This module contains the low-level theme-aware primitives used by the
higher-level design-system widgets under this package.
"""

from __future__ import annotations

from typing import cast

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from polyglot_site_translator.presentation.kivy.design_tokens import (
    COMPONENT_SIZES,
    ELEVATION,
    RADIUS,
    SPACING,
    TYPOGRAPHY,
)
from polyglot_site_translator.presentation.kivy.theme import (
    ColorTuple,
    get_active_theme,
)


def apply_theme_to_widget_tree(root_widget: Widget) -> None:
    """Apply the current theme palette to all theme-aware widgets in a tree.

    Args:
        root_widget:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if hasattr(root_widget, "apply_theme"):
        root_widget.apply_theme()
    for child in root_widget.children:
        apply_theme_to_widget_tree(child)


def _resolve_color(
    explicit_color: ColorTuple | None,
    color_role: str | None,
    fallback_role: str,
) -> ColorTuple:
    """Resolve color.

    Args:
        explicit_color:
            Value supplied to this callable.
        color_role:
            Value supplied to this callable.
        fallback_role:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if explicit_color is not None:
        return explicit_color
    palette = get_active_theme()
    role_name = color_role or fallback_role
    return cast(ColorTuple, getattr(palette, role_name))


class SurfaceBoxLayout(BoxLayout):  # type: ignore[misc]
    """BoxLayout with a simple surface background and border.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self,
        *,
        background_color: ColorTuple | None = None,
        background_role: str | None = None,
        border_color: ColorTuple | None = None,
        border_role: str | None = None,
        radius: int | None = None,
        **kwargs: object,
    ) -> None:
        """Create a theme-aware surface with optional explicit colors and roles.

        Args:
            self:
                Value supplied to this callable.
            background_color:
                Value supplied to this callable.
            background_role:
                Value supplied to this callable.
            border_color:
                Value supplied to this callable.
            border_role:
                Value supplied to this callable.
            radius:
                Corner radius for the rendered surface.
            **kwargs:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(**kwargs)
        self._background_role = background_role
        self._border_role = border_role
        self._background_color = background_color
        self._border_color = border_color
        self._radius = RADIUS.card if radius is None else radius
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
            self._background_rect = RoundedRectangle(
                pos=self.pos,
                radius=[self._radius],
                size=self.size,
            )
            self._border_instruction = Color(*resolved_border_color)
            self._border_line = Line(
                rounded_rectangle=(
                    self.x,
                    self.y,
                    self.width,
                    self.height,
                    self._radius,
                ),
                width=ELEVATION.card_border_width,
            )
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_args: object) -> None:
        """Update canvas.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._background_rect.pos = self.pos
        self._background_rect.size = self.size
        self._border_line.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            self._radius,
        )

    def apply_theme(self) -> None:
        """Re-apply the current palette to this surface.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
    """Label that wraps text and grows vertically with its content.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self,
        *,
        font_size: int = TYPOGRAPHY.label,
        bold: bool = False,
        color: ColorTuple | None = None,
        color_role: str | None = None,
        **kwargs: object,
    ) -> None:
        """Create a label that wraps text horizontally and auto-expands vertically.

        Args:
            self:
                Value supplied to this callable.
            font_size:
                Value supplied to this callable.
            bold:
                Value supplied to this callable.
            color:
                Value supplied to this callable.
            color_role:
                Value supplied to this callable.
            **kwargs:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
        """Synchronize text size.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.text_size = (self.width, None)

    def _sync_height(self, *_args: object) -> None:
        """Synchronize height.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.height = max(
            self.texture_size[1] + SPACING.sm,
            self.font_size + SPACING.md,
        )

    def apply_theme(self) -> None:
        """Re-apply the current palette to the label text color.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.color = _resolve_color(self._color, self._color_role, "text_primary")


class AppButton(Button):  # type: ignore[misc]
    """Button with a consistent application style.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self,
        *,
        primary: bool = True,
        **kwargs: object,
    ) -> None:
        """Create a theme-aware button using the primary or secondary palette roles.

        Args:
            self:
                Value supplied to this callable.
            primary:
                Value supplied to this callable.
            **kwargs:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        resolved_kwargs = dict(kwargs)
        self._primary = primary
        self._uses_theme_background = "background_color" not in resolved_kwargs
        self._uses_theme_text = "color" not in resolved_kwargs
        palette = get_active_theme()
        resolved_kwargs.setdefault(
            "background_color",
            (
                palette.primary_button_background
                if primary
                else palette.secondary_button_background
            ),
        )
        resolved_kwargs.setdefault(
            "color",
            palette.primary_button_text if primary else palette.secondary_button_text,
        )
        resolved_kwargs.setdefault("size_hint_y", None)
        resolved_kwargs.setdefault("height", COMPONENT_SIZES.button_height)
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
        """Re-apply the current palette to the button colors.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        palette = get_active_theme()
        if self._uses_theme_background:
            self.background_color = (
                palette.primary_button_background
                if self._primary
                else palette.secondary_button_background
            )
        if self._uses_theme_text:
            self.color = (
                palette.primary_button_text
                if self._primary
                else palette.secondary_button_text
            )

    def _sync_text_size(self, *_args: object) -> None:
        """Synchronize text size.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.text_size = (max(self.width - SPACING.lg, 0), None)
