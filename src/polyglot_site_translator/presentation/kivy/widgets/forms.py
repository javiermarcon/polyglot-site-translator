"""Reusable form presentation helpers for Kivy screens.

The functions and widgets in this module centralize label, help-text, and
control grouping for forms without owning validation or persistence logic.
"""

from __future__ import annotations

from kivy.uix.widget import Widget

from polyglot_site_translator.presentation.kivy.design_tokens import (
    SPACING,
    TYPOGRAPHY,
)
from polyglot_site_translator.presentation.kivy.widgets.common import WrappedLabel
from polyglot_site_translator.presentation.kivy.widgets.surfaces import AppCard


class LabeledFieldCard(AppCard):
    """Card containing one field label, optional help text, and one control.

    Attributes:
        label_widget:
            Label rendering the field title.
        help_widget:
            Optional label rendering supporting field guidance.
    """

    def __init__(
        self,
        *,
        label: str,
        field: Widget,
        help_text: str = "",
    ) -> None:
        """Create a labeled field card.

        Args:
            self:
                Current field-card instance.
            label:
                Field label shown above the control.
            field:
                Kivy control owned by the calling screen.
            help_text:
                Optional supporting text for the field.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(
            spacing=SPACING.sm,
            padding=SPACING.lg,
            background_role="card_subtle_background",
        )
        self.label_widget = WrappedLabel(
            text=label,
            font_size=TYPOGRAPHY.label,
            bold=True,
        )
        self.help_widget: WrappedLabel | None = None
        self.add_widget(self.label_widget)
        if help_text:
            self.help_widget = WrappedLabel(
                text=help_text,
                font_size=TYPOGRAPHY.caption,
                color_role="text_muted",
            )
            self.add_widget(self.help_widget)
        self.add_widget(field)
