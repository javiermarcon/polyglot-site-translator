"""Reusable action styling helpers for Kivy screens.

The helpers centralize primary, secondary, and destructive action semantics so
screen modules only choose intent and do not duplicate button color roles.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from kivy.uix.boxlayout import BoxLayout

from polyglot_site_translator.presentation.kivy.design_tokens import SPACING
from polyglot_site_translator.presentation.kivy.theme import get_active_theme
from polyglot_site_translator.presentation.kivy.widgets.common import AppButton


class ActionIntent(StrEnum):
    """Semantic action intent for Kivy buttons.

    Attributes:
        PRIMARY:
            Main action for a workflow area.
        SECONDARY:
            Supporting or navigational action.
        DESTRUCTIVE:
            Action that removes or discards data.
    """

    PRIMARY = "primary"
    SECONDARY = "secondary"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class ButtonStyle:
    """Resolved theme roles for a semantic button intent.

    Attributes:
        background_role:
            Palette attribute used for the button background.
        text_role:
            Palette attribute used for button text.
        is_primary_shape:
            Whether the existing ``AppButton`` primary branch should be used.
    """

    background_role: str
    text_role: str
    is_primary_shape: bool


def resolve_button_style(intent: ActionIntent) -> ButtonStyle:
    """Resolve theme roles for a button intent.

    Args:
        intent:
            Semantic action intent selected by the caller.

    Returns:
        value:
            Palette role names and shape hint for the requested intent.
    """
    if intent == ActionIntent.PRIMARY:
        return ButtonStyle(
            background_role="primary_button_background",
            text_role="primary_button_text",
            is_primary_shape=True,
        )
    if intent == ActionIntent.DESTRUCTIVE:
        return ButtonStyle(
            background_role="destructive_button_background",
            text_role="destructive_button_text",
            is_primary_shape=False,
        )
    return ButtonStyle(
        background_role="secondary_button_background",
        text_role="secondary_button_text",
        is_primary_shape=False,
    )


class ActionRow(BoxLayout):  # type: ignore[misc]
    """Horizontal or vertical container for related workflow actions.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self,
        *,
        orientation: str = "horizontal",
        **kwargs: object,
    ) -> None:
        """Create a consistently spaced action row.

        Args:
            self:
                Current row instance.
            orientation:
                Kivy orientation for the row.
            **kwargs:
                Additional Kivy layout keyword arguments.

        Returns:
            value:
                Structured value returned by this callable.
        """
        resolved_kwargs = dict(kwargs)
        resolved_kwargs.setdefault("spacing", SPACING.md)
        resolved_kwargs.setdefault("size_hint_y", None)
        super().__init__(orientation=orientation, **resolved_kwargs)
        self.bind(minimum_height=self.setter("height"))


def build_action_button(
    *,
    text: str,
    intent: ActionIntent = ActionIntent.PRIMARY,
) -> AppButton:
    """Build an application button from a semantic action intent.

    Args:
        text:
            Label rendered inside the button.
        intent:
            Semantic action intent used to resolve palette roles.

    Returns:
        value:
            Theme-aware Kivy button.
    """
    style = resolve_button_style(intent)
    if intent == ActionIntent.DESTRUCTIVE:
        palette = get_active_theme()
        return AppButton(
            text=text,
            primary=False,
            background_color=getattr(palette, style.background_role),
            color=getattr(palette, style.text_role),
        )
    return AppButton(text=text, primary=style.is_primary_shape)
