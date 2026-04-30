"""Settings screen."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from functools import partial
from pathlib import Path

from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScopeSettings,
    ConfiguredSyncRule,
    FrameworkSyncRuleSet,
    SyncFilterType,
    SyncRuleBehavior,
)
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.settings_layout import (
    build_settings_layout_spec,
)
from polyglot_site_translator.presentation.kivy.site_editor_form import (
    find_option_label,
    find_option_value,
)
from polyglot_site_translator.presentation.kivy.theme import get_active_theme
from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
)
from polyglot_site_translator.presentation.kivy.widgets.path_picker import (
    PathFieldPicker,
    build_path_input_row,
)
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    SettingsOptionViewModel,
    SettingsStateViewModel,
    build_framework_type_options_from_descriptors,
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
        self._default_project_locale_input: TextInput | None = None
        self._default_compile_mo_switch: Switch | None = None
        self._default_use_external_translator_switch: Switch | None = None
        self._database_directory_input: TextInput | None = None
        self._database_filename_input: TextInput | None = None
        self._sync_progress_log_limit_input: TextInput | None = None
        self._global_rule_path_input: TextInput | None = None
        self._global_rule_description_input: TextInput | None = None
        self._framework_rule_type_spinner: Spinner | None = None
        self._framework_rule_path_input: TextInput | None = None
        self._framework_rule_description_input: TextInput | None = None
        self._global_rule_filter_type_spinner: Spinner | None = None
        self._global_rule_behavior_spinner: Spinner | None = None
        self._framework_rule_filter_type_spinner: Spinner | None = None
        self._framework_rule_behavior_spinner: Spinner | None = None
        self._framework_type_options: list[SettingsOptionViewModel] = (
            self._build_framework_type_options()
        )
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

        if self._draft_settings is None:
            self._draft_settings = state.app_settings
        self._default_project_locale_input = None
        self._default_compile_mo_switch = None
        self._default_use_external_translator_switch = None
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
        layout.add_widget(self._build_sections_column())
        layout.add_widget(self._build_section_content())
        return layout

    def _build_sections_column(self) -> BoxLayout:
        column = BoxLayout(
            orientation="vertical",
            spacing=0,
            size_hint_y=1,
        )
        if self._layout_spec.sections_width is not None:
            column.size_hint_x = None
            column.width = self._layout_spec.sections_width
        column.add_widget(self._build_sections_panel())
        column.add_widget(Widget())
        return column

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
            panel.add_widget(self._build_section_form())
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

    def _build_section_form(self) -> GridLayout:
        state = self._require_state()
        if state.selected_section_key == "frameworks":
            return self._build_framework_sync_rules_panel()
        if state.selected_section_key == "translation":
            return self._build_translation_settings_form_panel()
        return self._build_app_settings_form_panel()

    def _build_translation_settings_form_panel(self) -> GridLayout:
        draft = self._require_draft()
        form = GridLayout(cols=1, spacing=12, size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        form.add_widget(
            self._build_default_project_locale_field(
                value=draft.default_project_locale,
            )
        )
        form.add_widget(self._build_default_compile_mo_field(value=draft.default_compile_mo))
        form.add_widget(
            self._build_default_use_external_translator_field(
                value=draft.default_use_external_translator
            )
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

    def _build_app_settings_form_panel(self) -> GridLayout:
        state = self._require_state()
        draft = self._require_draft()
        form = GridLayout(cols=1, spacing=12, size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        form.add_widget(
            self._build_spinner_field(
                label=state.theme_mode_field.label,
                help_text=state.theme_mode_field.help_text,
                values=[option.label for option in state.theme_mode_field.options],
                current_label=find_option_label(
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
                current_label=find_option_label(
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

    def _build_framework_sync_rules_panel(self) -> GridLayout:
        draft = self._require_draft()
        sync_scope_settings = draft.sync_scope_settings
        form = GridLayout(cols=1, spacing=12, size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        form.add_widget(
            self._build_toggle_field(
                label="Use .gitignore Exclusions",
                help_text=(
                    "When enabled, supported .gitignore patterns are translated into "
                    "additional sync exclusions during filtered sync resolution."
                ),
                active=sync_scope_settings.use_gitignore_rules,
                on_toggle=self._toggle_use_gitignore_rules,
            )
        )
        form.add_widget(
            self._build_configured_rules_catalog(
                title="Global Sync Rules",
                help_text=(
                    "These rules apply to every project before framework-specific "
                    "and project-specific overrides are resolved."
                ),
                rules=sync_scope_settings.global_rules,
                scope_type="global",
                framework_type=None,
            )
        )
        for rule_set in sync_scope_settings.framework_rule_sets:
            form.add_widget(
                self._build_configured_rules_catalog(
                    title=f"Framework Rules: {rule_set.framework_type}",
                    help_text=("These rules apply to projects that declare this framework type."),
                    rules=rule_set.rules,
                    scope_type="framework",
                    framework_type=rule_set.framework_type,
                )
            )
        form.add_widget(self._build_add_global_rule_form())
        form.add_widget(self._build_add_framework_rule_form())
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

    def _build_default_project_locale_field(self, *, value: str) -> SurfaceBoxLayout:
        palette = get_active_theme()
        card = _build_field_card(
            title="Default Project Locale",
            help_text=(
                "Used as the initial default locale value when opening the create project "
                "workflow. Accepts a locale or a normalized comma-separated locale list."
            ),
        )
        self._default_project_locale_input = TextInput(
            text=value,
            multiline=False,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )
        card.add_widget(WrappedLabel(text="Default Project Locale", font_size=14, bold=True))
        card.add_widget(self._default_project_locale_input)
        return card

    def _build_default_compile_mo_field(self, *, value: bool) -> SurfaceBoxLayout:
        card = _build_field_card(
            title="Default MO Compilation",
            help_text=(
                "Controls whether new project drafts start with MO compilation enabled for "
                "translation workflows."
            ),
        )
        row = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=40)
        row.add_widget(WrappedLabel(text="Compile MO Files", font_size=14, bold=True))
        self._default_compile_mo_switch = Switch(
            active=value,
            size_hint=(None, None),
            size=(72, 36),
        )
        row.add_widget(self._default_compile_mo_switch)
        card.add_widget(row)
        return card

    def _build_default_use_external_translator_field(self, *, value: bool) -> SurfaceBoxLayout:
        card = _build_field_card(
            title="Default External Translator",
            help_text=(
                "Controls whether new project drafts start with the external translator "
                "enabled for translation workflows."
            ),
        )
        row = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=40)
        row.add_widget(WrappedLabel(text="Use External Translator", font_size=14, bold=True))
        self._default_use_external_translator_switch = Switch(
            active=value,
            size_hint=(None, None),
            size=(72, 36),
        )
        row.add_widget(self._default_use_external_translator_switch)
        card.add_widget(row)
        return card

    def _database_file_browse_hint(self) -> str:
        """Return a path hint for opening the SQLite file picker."""
        if self._database_directory_input is None or self._database_filename_input is None:
            return ""
        directory = str(self._database_directory_input.text).strip()
        filename = str(self._database_filename_input.text).strip()
        if directory != "" and filename != "":
            return str(Path(directory) / filename)
        if directory != "":
            return directory
        return filename

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
        column.add_widget(
            build_path_input_row(
                self._database_directory_input,
                PathFieldPicker(
                    pick_mode="directory",
                    title="Choose SQLite directory",
                    path_hint=lambda: (
                        self._database_directory_input.text
                        if self._database_directory_input is not None
                        else ""
                    ),
                ),
            ),
        )
        column.add_widget(WrappedLabel(text="Database Filename", font_size=14, bold=True))
        column.add_widget(
            build_path_input_row(
                self._database_filename_input,
                PathFieldPicker(
                    pick_mode="file",
                    title="Choose SQLite database file",
                    path_hint=self._database_file_browse_hint,
                    use_basename_only=True,
                ),
            ),
        )
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

    def _build_configured_rules_catalog(
        self,
        *,
        title: str,
        help_text: str,
        rules: tuple[ConfiguredSyncRule, ...],
        scope_type: str,
        framework_type: str | None,
    ) -> SurfaceBoxLayout:
        card = _build_field_card(title=title, help_text=help_text)
        if rules == ():
            card.add_widget(
                WrappedLabel(
                    text="No configured rules.",
                    font_size=14,
                    color_role="text_muted",
                )
            )
            return card
        for rule in rules:
            row = BoxLayout(
                orientation=self._layout_spec.field_row_orientation,
                spacing=12,
                size_hint_y=None,
            )
            row.bind(minimum_height=row.setter("height"))
            row.add_widget(
                WrappedLabel(
                    text=(
                        f"[{rule.behavior.value}] {rule.relative_path} ({rule.filter_type.value})"
                    ),
                    font_size=14,
                )
            )
            toggle_button = AppButton(
                text="Disable" if rule.is_enabled else "Enable",
                primary=False,
                height=40,
            )
            toggle_button.bind(
                on_release=partial(
                    self._handle_toggle_configured_rule,
                    relative_path=rule.relative_path,
                    filter_type=rule.filter_type,
                    behavior=rule.behavior,
                    is_enabled=rule.is_enabled,
                    scope_type=scope_type,
                    framework_type=framework_type,
                )
            )
            row.add_widget(toggle_button)
            remove_button = AppButton(text="Remove", primary=False, height=40)
            remove_button.bind(
                on_release=partial(
                    self._handle_remove_configured_rule,
                    relative_path=rule.relative_path,
                    filter_type=rule.filter_type,
                    behavior=rule.behavior,
                    scope_type=scope_type,
                    framework_type=framework_type,
                )
            )
            row.add_widget(remove_button)
            card.add_widget(row)
            if rule.description.strip():
                card.add_widget(
                    WrappedLabel(
                        text=rule.description,
                        font_size=12,
                        color_role="text_muted",
                    )
                )
        return card

    def _build_add_global_rule_form(self) -> SurfaceBoxLayout:
        palette = get_active_theme()
        card = _build_field_card(
            title="Add Global Sync Rule",
            help_text="Create a rule applied to every project sync scope.",
        )
        column = BoxLayout(orientation="vertical", spacing=12, size_hint_y=None)
        column.bind(minimum_height=column.setter("height"))
        self._global_rule_path_input = TextInput(
            text="",
            multiline=False,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )
        self._global_rule_description_input = TextInput(
            text="",
            multiline=False,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )
        self._global_rule_filter_type_spinner = Spinner(
            text="Directory",
            values=["Directory", "File", "Glob"],
            size_hint_y=None,
            height=44,
            background_normal="",
            background_color=palette.card_subtle_background,
            color=palette.text_primary,
        )
        self._global_rule_behavior_spinner = Spinner(
            text="Exclude",
            values=["Include", "Exclude"],
            size_hint_y=None,
            height=44,
            background_normal="",
            background_color=palette.card_subtle_background,
            color=palette.text_primary,
        )
        column.add_widget(WrappedLabel(text="Relative Path or Pattern", font_size=14, bold=True))
        column.add_widget(self._global_rule_path_input)
        column.add_widget(WrappedLabel(text="Description", font_size=14, bold=True))
        column.add_widget(self._global_rule_description_input)
        column.add_widget(self._global_rule_filter_type_spinner)
        column.add_widget(self._global_rule_behavior_spinner)
        add_button = AppButton(text="Add Global Rule", primary=False)
        add_button.bind(on_release=self._add_global_rule)
        column.add_widget(add_button)
        card.add_widget(column)
        return card

    def _build_add_framework_rule_form(self) -> SurfaceBoxLayout:
        palette = get_active_theme()
        card = _build_field_card(
            title="Add Framework Sync Rule",
            help_text="Create a rule applied to projects of a specific framework type.",
        )
        column = BoxLayout(orientation="vertical", spacing=12, size_hint_y=None)
        column.bind(minimum_height=column.setter("height"))
        self._framework_rule_type_spinner = Spinner(
            text=self._framework_type_options[0].label,
            values=[option.label for option in self._framework_type_options],
            size_hint_y=None,
            height=44,
            background_normal="",
            background_color=palette.card_subtle_background,
            color=palette.text_primary,
        )
        self._framework_rule_path_input = TextInput(
            text="",
            multiline=False,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )
        self._framework_rule_description_input = TextInput(
            text="",
            multiline=False,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )
        self._framework_rule_filter_type_spinner = Spinner(
            text="Directory",
            values=["Directory", "File", "Glob"],
            size_hint_y=None,
            height=44,
            background_normal="",
            background_color=palette.card_subtle_background,
            color=palette.text_primary,
        )
        self._framework_rule_behavior_spinner = Spinner(
            text="Exclude",
            values=["Include", "Exclude"],
            size_hint_y=None,
            height=44,
            background_normal="",
            background_color=palette.card_subtle_background,
            color=palette.text_primary,
        )
        column.add_widget(WrappedLabel(text="Framework Type", font_size=14, bold=True))
        column.add_widget(self._framework_rule_type_spinner)
        column.add_widget(WrappedLabel(text="Relative Path or Pattern", font_size=14, bold=True))
        column.add_widget(self._framework_rule_path_input)
        column.add_widget(WrappedLabel(text="Description", font_size=14, bold=True))
        column.add_widget(self._framework_rule_description_input)
        column.add_widget(self._framework_rule_filter_type_spinner)
        column.add_widget(self._framework_rule_behavior_spinner)
        add_button = AppButton(text="Add Framework Rule", primary=False)
        add_button.bind(on_release=self._add_framework_rule)
        column.add_widget(add_button)
        card.add_widget(column)
        return card

    def _back_to_dashboard(self, *_args: object) -> None:
        self._shell.open_dashboard()
        self.show_route("dashboard")

    def _apply_settings(self, *_args: object) -> None:
        self._clear_form_error()
        draft = self._require_draft()
        try:
            if self._width_input is not None and self._height_input is not None:
                width_text = self._width_input.text.strip()
                height_text = self._height_input.text.strip()
                if width_text and height_text:
                    draft = replace(
                        draft,
                        window_width=int(width_text),
                        window_height=int(height_text),
                    )
            if (
                self._database_directory_input is not None
                and self._database_filename_input is not None
            ):
                draft = replace(
                    draft,
                    database_directory=self._database_directory_input.text.strip(),
                    database_filename=self._database_filename_input.text.strip(),
                )
            if self._default_project_locale_input is not None:
                draft = replace(
                    draft,
                    default_project_locale=self._default_project_locale_input.text.strip(),
                )
            if self._default_compile_mo_switch is not None:
                draft = replace(
                    draft,
                    default_compile_mo=self._default_compile_mo_switch.active,
                )
            if self._default_use_external_translator_switch is not None:
                draft = replace(
                    draft,
                    default_use_external_translator=(
                        self._default_use_external_translator_switch.active
                    ),
                )
            if self._sync_progress_log_limit_input is not None:
                limit_text = self._sync_progress_log_limit_input.text.strip()
                if limit_text:
                    draft = replace(draft, sync_progress_log_limit=int(limit_text))
        except ValueError:
            self._show_form_error(ValueError("Numeric settings must be whole numbers."))
            return

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

    def _toggle_use_gitignore_rules(
        self,
        _widget: object,
        value: bool,
        state_label: WrappedLabel,
    ) -> None:
        draft = self._require_draft()
        self._draft_settings = replace(
            draft,
            sync_scope_settings=replace(
                draft.sync_scope_settings,
                use_gitignore_rules=value,
            ),
        )
        state_label.text = "Enabled" if value else "Disabled"

    def _on_theme_mode_selected(self, _widget: object, text: str) -> None:
        try:
            value = find_option_value(self._require_state().theme_mode_field.options, text)
        except LookupError as error:
            self._show_form_error(error)
            return
        draft = self._require_draft()
        self._draft_settings = replace(draft, theme_mode=value)

    def _on_ui_language_selected(self, _widget: object, text: str) -> None:
        try:
            value = find_option_value(self._require_state().ui_language_field.options, text)
        except LookupError as error:
            self._show_form_error(error)
            return
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

    def _add_global_rule(self, *_args: object) -> None:
        self._clear_form_error()
        draft = self._require_draft()
        try:
            new_rule = _build_configured_rule(
                relative_path=self._require_text_input(self._global_rule_path_input).text.strip(),
                description=(
                    self._require_text_input(self._global_rule_description_input).text.strip()
                ),
                filter_type_label=self._require_spinner(self._global_rule_filter_type_spinner).text,
                behavior_label=self._require_spinner(self._global_rule_behavior_spinner).text,
            )
        except (ValueError, LookupError) as error:
            self._show_form_error(error)
            return
        self._draft_settings = replace(
            draft,
            sync_scope_settings=replace(
                draft.sync_scope_settings,
                global_rules=(*draft.sync_scope_settings.global_rules, new_rule),
            ),
        )
        self.refresh()

    def _add_framework_rule(self, *_args: object) -> None:
        self._clear_form_error()
        draft = self._require_draft()
        try:
            framework_type = find_option_value(
                self._framework_type_options,
                self._require_spinner(self._framework_rule_type_spinner).text,
            )
            new_rule = _build_configured_rule(
                relative_path=self._require_text_input(
                    self._framework_rule_path_input
                ).text.strip(),
                description=(
                    self._require_text_input(self._framework_rule_description_input).text.strip()
                ),
                filter_type_label=self._require_spinner(
                    self._framework_rule_filter_type_spinner
                ).text,
                behavior_label=self._require_spinner(self._framework_rule_behavior_spinner).text,
            )
        except (ValueError, LookupError) as error:
            self._show_form_error(error)
            return
        self._draft_settings = replace(
            draft,
            sync_scope_settings=_append_framework_rule(
                draft.sync_scope_settings,
                framework_type=framework_type,
                rule=new_rule,
            ),
        )
        self.refresh()

    def _clear_form_error(self) -> None:
        self._shell.latest_error = None
        self.update_error_label()

    def _show_form_error(self, error: Exception) -> None:
        self._shell.latest_error = str(error)
        self.update_error_label()

    def _handle_toggle_configured_rule(  # noqa: PLR0913
        self,
        _widget: object,
        *,
        relative_path: str,
        filter_type: SyncFilterType,
        behavior: SyncRuleBehavior,
        is_enabled: bool,
        scope_type: str,
        framework_type: str | None,
    ) -> None:
        self._toggle_configured_rule(
            relative_path=relative_path,
            filter_type=filter_type,
            behavior=behavior,
            is_enabled=is_enabled,
            scope_type=scope_type,
            framework_type=framework_type,
        )

    def _handle_remove_configured_rule(
        self,
        _widget: object,
        *,
        relative_path: str,
        filter_type: SyncFilterType,
        behavior: SyncRuleBehavior,
        scope_type: str,
        framework_type: str | None,
    ) -> None:
        self._remove_configured_rule(
            relative_path=relative_path,
            filter_type=filter_type,
            behavior=behavior,
            scope_type=scope_type,
            framework_type=framework_type,
        )

    def _toggle_configured_rule(  # noqa: PLR0913
        self,
        *,
        relative_path: str,
        filter_type: SyncFilterType,
        behavior: SyncRuleBehavior,
        is_enabled: bool,
        scope_type: str,
        framework_type: str | None,
    ) -> None:
        self._draft_settings = replace(
            self._require_draft(),
            sync_scope_settings=_toggle_configured_rule(
                self._require_draft().sync_scope_settings,
                relative_path=relative_path,
                filter_type=filter_type,
                behavior=behavior,
                new_enabled=not is_enabled,
                scope_type=scope_type,
                framework_type=framework_type,
            ),
        )
        self.refresh()

    def _remove_configured_rule(
        self,
        *,
        relative_path: str,
        filter_type: SyncFilterType,
        behavior: SyncRuleBehavior,
        scope_type: str,
        framework_type: str | None,
    ) -> None:
        self._draft_settings = replace(
            self._require_draft(),
            sync_scope_settings=_remove_configured_rule(
                self._require_draft().sync_scope_settings,
                relative_path=relative_path,
                filter_type=filter_type,
                behavior=behavior,
                scope_type=scope_type,
                framework_type=framework_type,
            ),
        )
        self.refresh()

    def _require_text_input(self, widget: TextInput | None) -> TextInput:
        if widget is None:
            msg = "Text input must exist before using the settings form."
            raise ValueError(msg)
        return widget

    def _build_framework_type_options(self) -> list[SettingsOptionViewModel]:
        return build_framework_type_options_from_descriptors(
            FrameworkAdapterRegistry.discover_installed().list_framework_descriptors()
        )

    def _require_spinner(self, widget: Spinner | None) -> Spinner:
        if widget is None:
            msg = "Spinner must exist before using the settings form."
            raise ValueError(msg)
        return widget


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


def _build_configured_rule(
    *,
    relative_path: str,
    description: str,
    filter_type_label: str,
    behavior_label: str,
) -> ConfiguredSyncRule:
    normalized_relative_path = relative_path.strip().strip("/")
    if normalized_relative_path == "":
        msg = "Sync rules require a non-empty relative path or pattern."
        raise ValueError(msg)
    return ConfiguredSyncRule(
        relative_path=normalized_relative_path,
        filter_type=_map_filter_type_label(filter_type_label),
        behavior=_map_behavior_label(behavior_label),
        description=description.strip() or normalized_relative_path,
        is_enabled=True,
    )


def _append_framework_rule(
    sync_scope_settings: AdapterSyncScopeSettings,
    *,
    framework_type: str,
    rule: ConfiguredSyncRule,
) -> AdapterSyncScopeSettings:
    normalized_framework_type = framework_type.strip().lower()
    if normalized_framework_type == "":
        msg = "Framework sync rules require a non-empty framework type."
        raise ValueError(msg)
    updated_rule_sets: list[FrameworkSyncRuleSet] = []
    framework_rule_added = False
    for rule_set in sync_scope_settings.framework_rule_sets:
        if rule_set.normalized_framework_type() == normalized_framework_type:
            updated_rule_sets.append(
                FrameworkSyncRuleSet(
                    framework_type=normalized_framework_type,
                    rules=(*rule_set.rules, rule),
                )
            )
            framework_rule_added = True
            continue
        updated_rule_sets.append(rule_set)
    if not framework_rule_added:
        updated_rule_sets.append(
            FrameworkSyncRuleSet(
                framework_type=normalized_framework_type,
                rules=(rule,),
            )
        )
    return replace(
        sync_scope_settings,
        framework_rule_sets=tuple(updated_rule_sets),
    )


def _toggle_configured_rule(  # noqa: PLR0913
    sync_scope_settings: AdapterSyncScopeSettings,
    *,
    relative_path: str,
    filter_type: SyncFilterType,
    behavior: SyncRuleBehavior,
    new_enabled: bool,
    scope_type: str,
    framework_type: str | None,
) -> AdapterSyncScopeSettings:
    if scope_type == "global":
        return replace(
            sync_scope_settings,
            global_rules=tuple(
                replace(rule, is_enabled=new_enabled)
                if _matches_configured_rule(
                    rule,
                    relative_path=relative_path,
                    filter_type=filter_type,
                    behavior=behavior,
                )
                else rule
                for rule in sync_scope_settings.global_rules
            ),
        )
    if framework_type is None:
        msg = "Framework sync rules require a framework type."
        raise ValueError(msg)
    return replace(
        sync_scope_settings,
        framework_rule_sets=tuple(
            FrameworkSyncRuleSet(
                framework_type=rule_set.framework_type,
                rules=tuple(
                    replace(rule, is_enabled=new_enabled)
                    if _matches_configured_rule(
                        rule,
                        relative_path=relative_path,
                        filter_type=filter_type,
                        behavior=behavior,
                    )
                    and rule_set.normalized_framework_type() == framework_type.strip().lower()
                    else rule
                    for rule in rule_set.rules
                ),
            )
            for rule_set in sync_scope_settings.framework_rule_sets
        ),
    )


def _remove_configured_rule(  # noqa: PLR0913
    sync_scope_settings: AdapterSyncScopeSettings,
    *,
    relative_path: str,
    filter_type: SyncFilterType,
    behavior: SyncRuleBehavior,
    scope_type: str,
    framework_type: str | None,
) -> AdapterSyncScopeSettings:
    if scope_type == "global":
        return replace(
            sync_scope_settings,
            global_rules=tuple(
                rule
                for rule in sync_scope_settings.global_rules
                if not _matches_configured_rule(
                    rule,
                    relative_path=relative_path,
                    filter_type=filter_type,
                    behavior=behavior,
                )
            ),
        )
    if framework_type is None:
        msg = "Framework sync rules require a framework type."
        raise ValueError(msg)
    normalized_framework_type = framework_type.strip().lower()
    updated_rule_sets: list[FrameworkSyncRuleSet] = []
    for rule_set in sync_scope_settings.framework_rule_sets:
        if rule_set.normalized_framework_type() != normalized_framework_type:
            updated_rule_sets.append(rule_set)
            continue
        next_rules = tuple(
            rule
            for rule in rule_set.rules
            if not _matches_configured_rule(
                rule,
                relative_path=relative_path,
                filter_type=filter_type,
                behavior=behavior,
            )
        )
        if next_rules != ():
            updated_rule_sets.append(
                FrameworkSyncRuleSet(
                    framework_type=rule_set.framework_type,
                    rules=next_rules,
                )
            )
    return replace(sync_scope_settings, framework_rule_sets=tuple(updated_rule_sets))


def _matches_configured_rule(
    rule: ConfiguredSyncRule,
    *,
    relative_path: str,
    filter_type: SyncFilterType,
    behavior: SyncRuleBehavior,
) -> bool:
    return (
        rule.relative_path == relative_path
        and rule.filter_type is filter_type
        and rule.behavior is behavior
    )


def _map_filter_type_label(label: str) -> SyncFilterType:
    normalized_label = label.strip().lower()
    label_mapping = {
        "directory": SyncFilterType.DIRECTORY,
        "file": SyncFilterType.FILE,
        "glob": SyncFilterType.GLOB,
    }
    value = label_mapping.get(normalized_label)
    if value is None:
        msg = f"Unsupported filter type label: {label}"
        raise ValueError(msg)
    return value


def _map_behavior_label(label: str) -> SyncRuleBehavior:
    normalized_label = label.strip().lower()
    label_mapping = {
        "include": SyncRuleBehavior.INCLUDE,
        "exclude": SyncRuleBehavior.EXCLUDE,
    }
    value = label_mapping.get(normalized_label)
    if value is None:
        msg = f"Unsupported behavior label: {label}"
        raise ValueError(msg)
    return value
