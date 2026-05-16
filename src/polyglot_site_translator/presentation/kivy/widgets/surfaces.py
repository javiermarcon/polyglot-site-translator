"""Reusable card, section, and status surfaces for Kivy screens.

These widgets provide visual grouping and state communication while keeping
screens focused on routing and view-model rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from kivy.uix.boxlayout import BoxLayout

from polyglot_site_translator.presentation.kivy.design_tokens import (
    RADIUS,
    SPACING,
    TYPOGRAPHY,
)
from polyglot_site_translator.presentation.kivy.widgets.common import (
    SurfaceBoxLayout,
    WrappedLabel,
)


class StatusTone(StrEnum):
    """Semantic tone for status and empty-state panels.

    Attributes:
        EMPTY:
            Neutral empty state or not-started workflow state.
        LOADING:
            In-progress state.
        SUCCESS:
            Completed state.
        WARNING:
            Degraded state that still allows interaction.
        ERROR:
            Controlled failure state.
        INFO:
            Informational state.
    """

    EMPTY = "empty"
    LOADING = "loading"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


@dataclass(frozen=True)
class StatusSurfaceRoles:
    """Palette roles used by a status surface.

    Attributes:
        background_role:
            Palette role for the status background.
        border_role:
            Palette role for the status border.
        text_role:
            Palette role for the main status text.
        accent_role:
            Palette role for emphasized status text.
    """

    background_role: str
    border_role: str
    text_role: str
    accent_role: str


def resolve_status_surface_roles(tone: StatusTone) -> StatusSurfaceRoles:
    """Resolve palette roles for a visible status tone.

    Args:
        tone:
            Semantic status tone requested by a screen or widget.

    Returns:
        value:
            Palette roles used to render the status surface.
    """
    if tone == StatusTone.ERROR:
        return StatusSurfaceRoles(
            background_role="error_background",
            border_role="error_background",
            text_role="error_text",
            accent_role="error_text",
        )
    if tone == StatusTone.SUCCESS:
        return StatusSurfaceRoles(
            background_role="success_background",
            border_role="success_background",
            text_role="success_text",
            accent_role="success_text",
        )
    if tone == StatusTone.WARNING:
        return StatusSurfaceRoles(
            background_role="warning_background",
            border_role="warning_background",
            text_role="warning_text",
            accent_role="warning_text",
        )
    if tone == StatusTone.LOADING:
        return StatusSurfaceRoles(
            background_role="info_background",
            border_role="info_background",
            text_role="info_text",
            accent_role="info_text",
        )
    if tone == StatusTone.INFO:
        return StatusSurfaceRoles(
            background_role="info_background",
            border_role="info_background",
            text_role="info_text",
            accent_role="info_text",
        )
    return StatusSurfaceRoles(
        background_role="card_subtle_background",
        border_role="border_color",
        text_role="text_muted",
        accent_role="text_primary",
    )


def status_tone_from_workflow_status(status: str) -> StatusTone:
    """Map a workflow status string to a reusable visual tone.

    Args:
        status:
            Presentation workflow status such as ``"running"`` or
            ``"completed"``.

    Returns:
        value:
            Semantic status tone for reusable status surfaces.
    """
    if status == "failed":
        return StatusTone.ERROR
    if status == "running":
        return StatusTone.LOADING
    if status == "completed":
        return StatusTone.SUCCESS
    return StatusTone.INFO


class AppCard(SurfaceBoxLayout):
    """Grouped card surface with consistent spacing and padding.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, **kwargs: object) -> None:
        """Create a reusable card container.

        Args:
            self:
                Current card instance.
            **kwargs:
                Additional Kivy layout keyword arguments.

        Returns:
            value:
                Structured value returned by this callable.
        """
        resolved_kwargs = dict(kwargs)
        resolved_kwargs.setdefault("orientation", "vertical")
        resolved_kwargs.setdefault("spacing", SPACING.md)
        resolved_kwargs.setdefault("padding", SPACING.lg)
        resolved_kwargs.setdefault("size_hint_y", None)
        resolved_kwargs.setdefault("radius", RADIUS.card)
        super().__init__(**resolved_kwargs)  # type: ignore[arg-type]
        self.bind(minimum_height=self.setter("height"))


class SectionHeader(BoxLayout):  # type: ignore[misc]
    """Compact title and description block for a screen section.

    Attributes:
        title_label:
            Label rendering the section title.
        description_label:
            Label rendering optional supporting copy.
    """

    def __init__(self, *, title: str, description: str = "") -> None:
        """Create a reusable section header.

        Args:
            self:
                Current header instance.
            title:
                Section title text.
            description:
                Optional supporting text rendered below the title.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(
            orientation="vertical",
            spacing=SPACING.xs,
            size_hint_y=None,
        )
        self.title_label = WrappedLabel(
            text=title,
            font_size=TYPOGRAPHY.section_title,
            bold=True,
        )
        self.description_label = WrappedLabel(
            text=description,
            font_size=TYPOGRAPHY.caption,
            color_role="text_muted",
        )
        self.add_widget(self.title_label)
        if description:
            self.add_widget(self.description_label)
        self.bind(minimum_height=self.setter("height"))


class StatusBanner(AppCard):
    """Status card that communicates empty, loading, success, or error states.

    Attributes:
        title_label:
            Label rendering the status title.
        body_label:
            Label rendering status details.
    """

    def __init__(
        self,
        *,
        title: str,
        body: str,
        tone: StatusTone = StatusTone.INFO,
    ) -> None:
        """Create a status banner.

        Args:
            self:
                Current banner instance.
            title:
                Short state title.
            body:
                Detailed status body.
            tone:
                Semantic tone used for palette role resolution.

        Returns:
            value:
                Structured value returned by this callable.
        """
        roles = resolve_status_surface_roles(tone)
        super().__init__(
            background_role=roles.background_role,
            border_role=roles.border_role,
        )
        self.title_label = WrappedLabel(
            text=title,
            font_size=TYPOGRAPHY.label,
            bold=True,
            color_role=roles.accent_role,
        )
        self.body_label = WrappedLabel(
            text=body,
            font_size=TYPOGRAPHY.body,
            color_role=roles.text_role,
        )
        self.add_widget(self.title_label)
        self.add_widget(self.body_label)


class EmptyStatePanel(StatusBanner):
    """Neutral empty-state panel for screens without active content.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, *, title: str, body: str) -> None:
        """Create an empty-state panel.

        Args:
            self:
                Current empty-state panel.
            title:
                Short empty-state title.
            body:
                Supporting empty-state message.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(title=title, body=body, tone=StatusTone.EMPTY)
