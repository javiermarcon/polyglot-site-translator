"""Popup that asks which locales should be used for PO processing."""

from __future__ import annotations

from collections.abc import Callable

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput

from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryValidationError,
)
from polyglot_site_translator.domain.site_registry.locales import normalize_default_locale
from polyglot_site_translator.presentation.kivy.site_editor_form import (
    build_site_editor_text_input,
)
from polyglot_site_translator.presentation.kivy.widgets.common import AppButton, WrappedLabel


class POLocaleSelectionPopup(Popup):  # type: ignore[misc]
    """Modal dialog for selecting the locales used by PO processing."""

    def __init__(
        self,
        *,
        default_locales: str,
        on_confirm: Callable[[str], None],
    ) -> None:
        super().__init__(
            title="Process PO",
            size_hint=(0.76, 0.42),
            auto_dismiss=False,
        )
        self._on_confirm = on_confirm
        self._locales_input: TextInput = build_site_editor_text_input(default_locales)
        self._error_label = WrappedLabel(text="", color_role="error_text", font_size=14)
        container = BoxLayout(orientation="vertical", spacing=12, padding=12)
        container.add_widget(
            WrappedLabel(
                text=(
                    "Choose the locales to use for PO synchronization. "
                    "Use a single locale or a comma-separated list."
                )
            )
        )
        container.add_widget(self._locales_input)
        container.add_widget(self._error_label)
        actions = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=48)
        cancel_button = AppButton(text="Cancel", primary=False)
        process_button = AppButton(text="Process", primary=True)
        cancel_button.bind(on_release=lambda *_args: self.dismiss())
        process_button.bind(on_release=lambda *_args: self._submit())
        actions.add_widget(cancel_button)
        actions.add_widget(process_button)
        container.add_widget(actions)
        self.content = container

    def _submit(self) -> None:
        try:
            normalized_locales = normalize_default_locale(
                self._locales_input.text,
                label="Selected locales",
            )
        except SiteRegistryValidationError as error:
            self._error_label.text = str(error)
            return
        self._error_label.text = ""
        self.dismiss()
        self._on_confirm(normalized_locales)
