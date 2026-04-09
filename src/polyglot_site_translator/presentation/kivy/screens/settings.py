"""Settings screen."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.settings_layout import (
    build_settings_layout_spec,
)
from polyglot_site_translator.presentation.kivy.theme import get_active_theme
from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
)
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    SettingsOptionViewModel,
    SettingsStateViewModel,
)


class SettingsScreen(BaseShellScreen):
    """Screen showing the extensible frontend settings area."""

    def __init__(
        self,
        *,
        shell: FrontendShell,
        manager_ref: ScreenManager,
        apply_runtime_settings: Callable[[AppSettingsViewModel], None] | None = None,
    ) -> None:
        super().__init__(
            screen_name="settings",
            title="Settings",
            subtitle="Application behavior and future system configuration.",
            shell=shell,
            manager_ref=manager_ref,
        )
        self._apply_runtime_settings = apply_runtime_settings
        self._width_input: TextInput | None = None
        self._height_input: TextInput | None = None
        self._database_directory_input: TextInput | None = None
        self._database_filename_input: TextInput | None = None
        self._sync_progress_log_limit_input: TextInput | None = None
        self._draft_settings: AppSettingsViewModel | None = None
        self._layout_spec = build_settings_layout_spec(Window.width)
        self.refresh()

    def refresh(self) -> None:
        self.clear_content()
        state = self._shell.settings_state
        if state is None:
            self._content.add_widget(
                _build_information_card(
                    title="Settings",
                    body="Open the settings workflow to load the current configuration.",
                )
            )
            self.update_error_label()
            return

        self._draft_settings = state.app_settings
        self._layout_spec = build_settings_layout_spec(Window.width)
        self._content.add_widget(
            _build_information_card(
                title="Configuration Center",
                body=(
                    "Use the application menu to move between screen groups. "
                    "This settings area is organized by sections so future domains can be added "
                    "without replacing the current UI shell."
                ),
            )
        )
        self._content.add_widget(self._build_main_layout())
        self.update_error_label()

    def _build_main_layout(self) -> GridLayout:
        layout = GridLayout(
            cols=self._layout_spec.main_columns,
            spacing=16,
            size_hint_y=None,
        )
        layout.bind(minimum_height=layout.setter("height"))
        layout.add_widget(self._build_sections_panel())
        layout.add_widget(self._build_section_content())
        return layout

    def _build_sections_panel(self) -> SurfaceBoxLayout:
        state = self._require_state()
        panel = SurfaceBoxLayout(
            orientation="vertical",
            spacing=10,
            padding=16,
            size_hint_y=None,
            background_role="card_background",
        )
        panel.bind(minimum_height=panel.setter("height"))
        if self._layout_spec.sections_width is not None:
            panel.size_hint_x = None
            panel.width = self._layout_spec.sections_width
        panel.add_widget(WrappedLabel(text="Settings Sections", font_size=18, bold=True))
        panel.add_widget(
            WrappedLabel(
                text="Plan categories now and enable them later without changing the screen shell.",
                font_size=14,
                color_role="text_muted",
            )
        )
        for section in state.sections:
            button = AppButton(
                text=f"{section.title}\n{section.description}",
                primary=section.key == state.selected_section_key,
                height=self._layout_spec.section_button_height,
            )
            button.disabled = section.key == state.selected_section_key
            button.bind(
                on_release=lambda _widget, key=section.key: self._select_settings_section(key)
            )
            panel.add_widget(button)
        return panel

    def _build_section_content(self) -> SurfaceBoxLayout:
        state = self._require_state()
        panel = SurfaceBoxLayout(
            orientation="vertical",
            spacing=14,
            padding=20,
            size_hint_y=None,
            background_role="card_background",
        )
        panel.bind(minimum_height=panel.setter("height"))
        panel.add_widget(WrappedLabel(text=state.selected_section_title, font_size=22, bold=True))
        panel.add_widget(
            WrappedLabel(
                text=state.selected_section_description,
                font_size=15,
                color_role="text_muted",
            )
        )
        panel.add_widget(
            _build_information_card(
                title="Current Status",
                body=state.status_message or "No status message available.",
            )
        )
        if state.selected_section_is_available:
            panel.add_widget(self._build_form_panel())
        else:
            panel.add_widget(
                _build_information_card(
                    title="Planned Section",
                    body=(
                        "This category is already part of the navigation design, "
                        "but its concrete configuration workflow is intentionally postponed."
                    ),
                )
            )
        return panel

    def _build_form_panel(self) -> GridLayout:
        state = self._require_state()
        draft = self._require_draft()
        form = GridLayout(cols=1, spacing=12, size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        form.add_widget(
            self._build_spinner_field(
                label=state.theme_mode_field.label,
                help_text=state.theme_mode_field.help_text,
                values=[option.label for option in state.theme_mode_field.options],
                current_label=_find_option_label(
                    state.theme_mode_field.options,
                    draft.theme_mode,
                ),
                on_select=self._on_theme_mode_selected,
            )
        )
        form.add_widget(
            self._build_window_field(
                width_value=str(draft.window_width),
                height_value=str(draft.window_height),
            )
        )
        form.add_widget(
            self._build_toggle_field(
                label="Remember Last Screen",
                help_text=(
                    "Keep the most recent screen as the next application entry point "
                    "once a real startup flow is connected."
                ),
                active=draft.remember_last_screen,
                on_toggle=self._toggle_remember_last_screen,
            )
        )
        form.add_widget(
            self._build_toggle_field(
                label="Developer Mode",
                help_text=(
                    "Expose future debugging and diagnostics panels without making them visible "
                    "to regular operators by default."
                ),
                active=draft.developer_mode,
                on_toggle=self._toggle_developer_mode,
            )
        )
        form.add_widget(
            self._build_spinner_field(
                label=state.ui_language_field.label,
                help_text=state.ui_language_field.help_text,
                values=[option.label for option in state.ui_language_field.options],
                current_label=_find_option_label(
                    state.ui_language_field.options,
                    draft.ui_language,
                ),
                on_select=self._on_ui_language_selected,
            )
        )
        form.add_widget(
            self._build_database_field(
                directory_value=draft.database_directory,
                filename_value=draft.database_filename,
            )
        )
        form.add_widget(
            self._build_sync_progress_field(limit_value=str(draft.sync_progress_log_limit))
        )
        actions = BoxLayout(
            orientation=self._layout_spec.action_orientation,
            spacing=12,
            size_hint_y=None,
        )
        actions.bind(minimum_height=actions.setter("height"))
        save_button = AppButton(text="Save Changes", primary=True)
        save_button.bind(on_release=self._apply_settings)
        defaults_button = AppButton(text="Restore Defaults", primary=False)
        defaults_button.bind(on_release=self._restore_defaults)
        dashboard_button = AppButton(text="Back to Dashboard", primary=False)
        dashboard_button.bind(on_release=self._back_to_dashboard)
        actions.add_widget(save_button)
        actions.add_widget(defaults_button)
        actions.add_widget(dashboard_button)
        form.add_widget(actions)
        return form

    def _build_spinner_field(
        self,
        *,
        label: str,
        help_text: str,
        values: list[str],
        current_label: str,
        on_select: object,
    ) -> SurfaceBoxLayout:
        palette = get_active_theme()
        card = _build_field_card(title=label, help_text=help_text)
        spinner = Spinner(
            text=current_label,
            values=values,
            size_hint_y=None,
            height=44,
            background_normal="",
            background_color=palette.card_subtle_background,
            color=palette.text_primary,
        )
        spinner.bind(text=on_select)
        card.add_widget(spinner)
        return card

    def _build_window_field(self, *, width_value: str, height_value: str) -> SurfaceBoxLayout:
        palette = get_active_theme()
        card = _build_field_card(
            title="Default Window Size",
            help_text=(
                "Define the preferred desktop window size for the frontend shell. "
                "Values are stored through the settings service, not in the widget."
            ),
        )
        row = BoxLayout(
            orientation=self._layout_spec.field_row_orientation,
            spacing=12,
            size_hint_y=None,
        )
        row.bind(minimum_height=row.setter("height"))
        self._width_input = TextInput(
            text=width_value,
            multiline=False,
            input_filter="int",
            size_hint_x=0.5 if self._layout_spec.field_row_orientation == "horizontal" else 1.0,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )
        self._height_input = TextInput(
            text=height_value,
            multiline=False,
            input_filter="int",
            size_hint_x=0.5 if self._layout_spec.field_row_orientation == "horizontal" else 1.0,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )
        row.add_widget(self._width_input)
        row.add_widget(self._height_input)
        card.add_widget(row)
        return card

    def _build_database_field(
        self,
        *,
        directory_value: str,
        filename_value: str,
    ) -> SurfaceBoxLayout:
        palette = get_active_theme()
        card = _build_field_card(
            title="SQLite Site Registry",
            help_text=(
                "Configure the directory and filename used to resolve the SQLite site registry. "
                "The UI edits settings only; path resolution stays in infrastructure services."
            ),
        )
        column = BoxLayout(orientation="vertical", spacing=12, size_hint_y=None)
        column.bind(minimum_height=column.setter("height"))
        self._database_directory_input = TextInput(
            text=directory_value,
            multiline=False,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )
        self._database_filename_input = TextInput(
            text=filename_value,
            multiline=False,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )
        column.add_widget(WrappedLabel(text="Database Directory", font_size=14, bold=True))
        column.add_widget(self._database_directory_input)
        column.add_widget(WrappedLabel(text="Database Filename", font_size=14, bold=True))
        column.add_widget(self._database_filename_input)
        card.add_widget(column)
        return card

    def _build_toggle_field(
        self,
        *,
        label: str,
        help_text: str,
        active: bool,
        on_toggle: Callable[[object, bool, WrappedLabel], None],
    ) -> SurfaceBoxLayout:
        card = _build_field_card(title=label, help_text=help_text)
        row = BoxLayout(
            orientation=self._layout_spec.toggle_row_orientation,
            spacing=12,
            size_hint_y=None,
        )
        row.bind(minimum_height=row.setter("height"))
        state_label = WrappedLabel(
            text="Enabled" if active else "Disabled",
            font_size=15,
        )
        toggle = Switch(active=active, size_hint=(None, None), size=(72, 36))
        toggle.bind(active=lambda widget, value: on_toggle(widget, value, state_label))
        row.add_widget(state_label)
        row.add_widget(toggle)
        card.add_widget(row)
        return card

    def _build_sync_progress_field(self, *, limit_value: str) -> SurfaceBoxLayout:
        palette = get_active_theme()
        card = _build_field_card(
            title="Sync Progress Command Log",
            help_text=(
                "Keep only the latest N sync operations in the progress window. "
                "This limits in-memory command-log growth while large remote trees are listed."
            ),
        )
        column = BoxLayout(orientation="vertical", spacing=12, size_hint_y=None)
        column.bind(minimum_height=column.setter("height"))
        self._sync_progress_log_limit_input = TextInput(
            text=limit_value,
            multiline=False,
            input_filter="int",
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )
        column.add_widget(WrappedLabel(text="Maximum Stored Operations", font_size=14, bold=True))
        column.add_widget(self._sync_progress_log_limit_input)
        card.add_widget(column)
        return card

    def _back_to_dashboard(self, *_args: object) -> None:
        self._shell.open_dashboard()
        self.show_route("dashboard")

    def _apply_settings(self, *_args: object) -> None:
        draft = self._require_draft()
        if self._width_input is not None and self._height_input is not None:
            width_text = self._width_input.text.strip()
            height_text = self._height_input.text.strip()
            if width_text and height_text:
                draft = replace(
                    draft,
                    window_width=int(width_text),
                    window_height=int(height_text),
                )
        if self._database_directory_input is not None and self._database_filename_input is not None:
            draft = replace(
                draft,
                database_directory=self._database_directory_input.text.strip(),
                database_filename=self._database_filename_input.text.strip(),
            )
        if self._sync_progress_log_limit_input is not None:
            limit_text = self._sync_progress_log_limit_input.text.strip()
            if limit_text:
                draft = replace(draft, sync_progress_log_limit=int(limit_text))
        self._draft_settings = draft
        self._shell.update_settings_draft(draft)
        self._shell.save_settings()
        self._draft_settings = self._require_state().app_settings
        if self._apply_runtime_settings is not None and self._require_state().status != "failed":
            self._apply_runtime_settings(self._require_state().app_settings)
        self.show_route("settings")

    def _restore_defaults(self, *_args: object) -> None:
        self._shell.restore_default_settings()
        self._draft_settings = self._require_state().app_settings
        if self._apply_runtime_settings is not None and self._require_state().status != "failed":
            self._apply_runtime_settings(self._require_state().app_settings)
        self.show_route("settings")

    def _select_settings_section(self, section_key: str) -> None:
        self._shell.select_settings_section(section_key)
        self._draft_settings = self._require_state().app_settings
        self.refresh()

    def _toggle_remember_last_screen(
        self,
        _widget: object,
        value: bool,
        state_label: WrappedLabel,
    ) -> None:
        draft = self._require_draft()
        self._draft_settings = replace(draft, remember_last_screen=value)
        state_label.text = "Enabled" if value else "Disabled"

    def _toggle_developer_mode(
        self,
        _widget: object,
        value: bool,
        state_label: WrappedLabel,
    ) -> None:
        draft = self._require_draft()
        self._draft_settings = replace(draft, developer_mode=value)
        state_label.text = "Enabled" if value else "Disabled"

    def _on_theme_mode_selected(self, _widget: object, text: str) -> None:
        value = _find_option_value(self._require_state().theme_mode_field.options, text)
        draft = self._require_draft()
        self._draft_settings = replace(draft, theme_mode=value)

    def _on_ui_language_selected(self, _widget: object, text: str) -> None:
        value = _find_option_value(self._require_state().ui_language_field.options, text)
        draft = self._require_draft()
        self._draft_settings = replace(draft, ui_language=value)

    def _require_state(self) -> SettingsStateViewModel:
        state = self._shell.settings_state
        if state is None:
            msg = "Settings must be loaded before rendering the settings screen."
            raise ValueError(msg)
        return state

    def _require_draft(self) -> AppSettingsViewModel:
        draft = self._draft_settings
        if draft is None:
            msg = "Settings draft must be initialized before editing."
            raise ValueError(msg)
        return draft


def _build_information_card(*, title: str, body: str) -> SurfaceBoxLayout:
    card = SurfaceBoxLayout(
        orientation="vertical",
        spacing=6,
        padding=16,
        size_hint_y=None,
        background_role="card_background",
    )
    card.bind(minimum_height=card.setter("height"))
    card.add_widget(WrappedLabel(text=title, font_size=18, bold=True))
    card.add_widget(WrappedLabel(text=body, font_size=14, color_role="text_muted"))
    return card


def _build_field_card(*, title: str, help_text: str) -> SurfaceBoxLayout:
    card = SurfaceBoxLayout(
        orientation="vertical",
        spacing=8,
        padding=14,
        size_hint_y=None,
        background_role="card_subtle_background",
    )
    card.bind(minimum_height=card.setter("height"))
    card.add_widget(WrappedLabel(text=title, font_size=16, bold=True))
    card.add_widget(WrappedLabel(text=help_text, font_size=13, color_role="text_muted"))
    return card


def _find_option_label(options: list[SettingsOptionViewModel], value: str) -> str:
    for option in options:
        if option.value == value:
            return option.label
    msg = f"Unknown option value: {value}"
    raise LookupError(msg)


def _find_option_value(options: list[SettingsOptionViewModel], label: str) -> str:
    for option in options:
        if option.label == label:
            return option.value
    msg = f"Unknown option label: {label}"
    raise LookupError(msg)
