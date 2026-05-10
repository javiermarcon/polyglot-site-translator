"""Popup that asks which locales should be used for PO processing."""

from __future__ import annotations

from collections.abc import Callable

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryValidationError,
)
from polyglot_site_translator.domain.site_registry.locales import normalize_default_locale
from polyglot_site_translator.presentation.kivy.site_editor_form import (
    build_site_editor_field_card,
    build_site_editor_text_input,
)
from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
)
from polyglot_site_translator.presentation.view_models import (
    TranslationOptionsViewModel,
    TranslationWorkflowRequestViewModel,
)


class POLocaleSelectionPopup(Popup):  # type: ignore[misc]
    """Modal dialog for selecting the locales used by PO processing."""

    def __init__(
        self,
        *,
        default_locales: str,
        default_options: TranslationOptionsViewModel,
        on_confirm: Callable[[TranslationWorkflowRequestViewModel], None],
    ) -> None:
        super().__init__(
            title="Translate Project",
            size_hint=(0.86, 0.9),
            auto_dismiss=False,
        )
        self._on_confirm = on_confirm
        self._locales_input: TextInput = build_site_editor_text_input(default_locales)
        self._compile_mo_switch = Switch(
            active=default_options.compile_mo,
            size_hint=(None, None),
            size=(72, 36),
        )
        self._use_external_translator_switch = Switch(
            active=default_options.use_external_translator,
            size_hint=(None, None),
            size=(72, 36),
        )
        self._use_translation_cache_switch = Switch(
            active=default_options.use_translation_cache,
            size_hint=(None, None),
            size=(72, 36),
        )
        self._only_fuzzy_switch = Switch(
            active=default_options.only_fuzzy,
            size_hint=(None, None),
            size=(72, 36),
        )
        self._dry_run_switch = Switch(
            active=default_options.dry_run,
            size_hint=(None, None),
            size=(72, 36),
        )
        self._stats_only_switch = Switch(
            active=default_options.stats_only,
            size_hint=(None, None),
            size=(72, 36),
        )
        self._report_inconsistencies_switch = Switch(
            active=default_options.report_inconsistencies,
            size_hint=(None, None),
            size=(72, 36),
        )
        self._error_label = WrappedLabel(text="", color_role="error_text", font_size=14)
        container = SurfaceBoxLayout(
            orientation="vertical",
            spacing=12,
            padding=16,
            background_role="card_background",
        )
        self._options_container = BoxLayout(
            orientation="vertical",
            spacing=8,
            size_hint_y=None,
            padding=(0, 0, 0, 4),
        )
        self._options_container.bind(minimum_height=self._options_container.setter("height"))
        self._options_container.add_widget(
            WrappedLabel(
                text=(
                    "Choose the locales to use for translation. "
                    "Use a single locale or a comma-separated list."
                ),
                color_role="text_muted",
            )
        )
        self._options_container.add_widget(
            build_site_editor_field_card("Locales", self._locales_input)
        )
        self._toggle_rows = (
            self._build_toggle_row(
                title="Compile MO Files",
                description="Compile gettext MO files after successful translation runs.",
                toggle=self._compile_mo_switch,
            ),
            self._build_toggle_row(
                title="Use External Translator",
                description="Call the configured external translator for missing strings.",
                toggle=self._use_external_translator_switch,
            ),
            self._build_toggle_row(
                title="Use Translation Cache",
                description="Reuse cached external translations before calling the provider.",
                toggle=self._use_translation_cache_switch,
            ),
            self._build_toggle_row(
                title="Only Fuzzy Entries",
                description="Restrict translation attempts to gettext entries flagged as fuzzy.",
                toggle=self._only_fuzzy_switch,
            ),
            self._build_toggle_row(
                title="Dry-run",
                description="Preview changes without writing PO or MO files.",
                toggle=self._dry_run_switch,
            ),
            self._build_toggle_row(
                title="Stats Only",
                description="Collect translation metrics without writing PO or MO files.",
                toggle=self._stats_only_switch,
            ),
            self._build_toggle_row(
                title="Report Inconsistencies",
                description="Report conflicting translations across locale variants.",
                toggle=self._report_inconsistencies_switch,
            ),
        )
        for row in self._toggle_rows:
            self._options_container.add_widget(row)
        container.add_widget(self._options_container)
        container.add_widget(self._error_label)
        actions = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=48)
        cancel_button = AppButton(text="Cancel", primary=False)
        process_button = AppButton(text="Translate", primary=True)
        cancel_button.bind(on_release=lambda *_args: self.dismiss())
        process_button.bind(on_release=lambda *_args: self._submit())
        actions.add_widget(cancel_button)
        actions.add_widget(process_button)
        container.add_widget(actions)
        self.content = container

    def _build_toggle_row(
        self,
        *,
        title: str,
        description: str,
        toggle: Switch,
    ) -> SurfaceBoxLayout:
        row = SurfaceBoxLayout(
            orientation="horizontal",
            spacing=12,
            padding=14,
            size_hint_y=None,
            height=58,
            background_role="card_subtle_background",
        )
        copy_column = BoxLayout(orientation="vertical", spacing=2)
        copy_column.add_widget(WrappedLabel(text=title, font_size=15, bold=True))
        copy_column.add_widget(
            WrappedLabel(text=description, font_size=13, color_role="text_muted")
        )
        row.add_widget(copy_column)
        row.add_widget(Widget(size_hint_x=None, width=8))
        row.add_widget(toggle)
        return row

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
        self._on_confirm(
            TranslationWorkflowRequestViewModel(
                locales=normalized_locales,
                options=TranslationOptionsViewModel(
                    compile_mo=self._compile_mo_switch.active,
                    use_external_translator=self._use_external_translator_switch.active,
                    use_translation_cache=self._use_translation_cache_switch.active,
                    only_fuzzy=self._only_fuzzy_switch.active,
                    dry_run=self._dry_run_switch.active,
                    stats_only=self._stats_only_switch.active,
                    report_inconsistencies=self._report_inconsistencies_switch.active,
                ),
            )
        )
