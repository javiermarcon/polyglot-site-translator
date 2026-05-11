"""Project editor screen."""

from __future__ import annotations

from dataclasses import replace

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.site_editor_form import (
    build_remote_password_field_card,
    build_site_editor_field_card,
    build_site_editor_spinner,
    build_site_editor_text_input,
    find_option_label,
    find_option_value,
)
from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
)
from polyglot_site_translator.presentation.kivy.widgets.path_picker import (
    PathFieldPicker,
    build_labeled_path_field,
)
from polyglot_site_translator.presentation.view_models import (
    ProjectEditorStateViewModel,
    SettingsOptionViewModel,
    SiteEditorViewModel,
    SyncRuleEditorItemViewModel,
)

from ..widgets.ssh_host_key_trust_dialog import (
    open_ssh_host_key_trust_confirmation,
)


class ProjectEditorScreen(BaseShellScreen):
    """Screen for creating and editing site registry records.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        """Build the editable project form and cache widget references for refreshes.

        Args:
            self:
                Value supplied to this callable.
            shell:
                Value supplied to this callable.
            manager_ref:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(
            screen_name="project_editor",
            title="Register Project",
            subtitle=(
                "Create or update site registry records without exposing SQL in the UI."
            ),
            shell=shell,
            manager_ref=manager_ref,
        )
        self.add_nav_button("Back to Projects", self._back_to_projects, primary=False)
        self._draft_editor: SiteEditorViewModel | None = None
        self._name_input: TextInput | None = None
        self._framework_spinner: Spinner | None = None
        self._local_path_input: TextInput | None = None
        self._default_locale_input: TextInput | None = None
        self._compile_mo_switch: Switch | None = None
        self._use_external_translator_switch: Switch | None = None
        self._use_translation_cache_switch: Switch | None = None
        self._only_fuzzy_switch: Switch | None = None
        self._dry_run_switch: Switch | None = None
        self._stats_only_switch: Switch | None = None
        self._report_inconsistencies_switch: Switch | None = None
        self._connection_type_spinner: Spinner | None = None
        self._remote_host_input: TextInput | None = None
        self._remote_port_input: TextInput | None = None
        self._remote_username_input: TextInput | None = None
        self._remote_password_input: TextInput | None = None
        self._remote_path_input: TextInput | None = None
        self._is_active_switch: Switch | None = None
        self._use_adapter_sync_filters_switch: Switch | None = None
        self._sync_rule_path_input: TextInput | None = None
        self._sync_rule_description_input: TextInput | None = None
        self._sync_rule_filter_type_spinner: Spinner | None = None
        self._sync_rule_behavior_spinner: Spinner | None = None
        self._test_connection_button: AppButton | None = None
        self.refresh()

    def refresh(self) -> None:
        """Rebuild the editor UI from the current draft state.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.clear_content()
        state = self._shell.project_editor_state
        if state is None:
            self._content.add_widget(
                _build_information_card(
                    title="Project Editor",
                    body=(
                        "Open the register or edit workflow to load a project "
                        "editor draft."
                    ),
                )
            )
            self.update_error_label()
            return
        self._reset_form_refs()
        self.set_screen_copy(
            title=state.title,
            subtitle="Persisted through the site registry service.",
        )
        self._draft_editor = state.editor
        self._content.add_widget(self._build_form_panel(state))
        self.update_error_label()

    def _build_form_panel(self, state: ProjectEditorStateViewModel) -> SurfaceBoxLayout:
        """Build form panel.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        panel = SurfaceBoxLayout(
            orientation="vertical",
            spacing=12,
            padding=0,
            size_hint_y=None,
            background_role="app_background",
        )
        panel.bind(minimum_height=panel.setter("height"))
        layout = GridLayout(cols=2, spacing=16, size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))
        layout.add_widget(self._build_sections_column(state))
        layout.add_widget(self._build_section_content(state))
        panel.add_widget(layout)
        return panel

    def _build_sections_column(self, state: ProjectEditorStateViewModel) -> BoxLayout:
        """Build sections column.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        column = BoxLayout(
            orientation="vertical",
            spacing=0,
            size_hint_x=None,
            size_hint_y=1,
            width=300,
        )
        column.add_widget(self._build_sections_panel(state))
        column.add_widget(Widget())
        return column

    def _build_sections_panel(
        self, state: ProjectEditorStateViewModel
    ) -> SurfaceBoxLayout:
        """Build sections panel.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        panel = SurfaceBoxLayout(
            orientation="vertical",
            spacing=10,
            padding=16,
            size_hint=(None, None),
            width=300,
            background_role="card_background",
        )
        panel.bind(minimum_height=panel.setter("height"))
        panel.add_widget(
            WrappedLabel(text="Project Settings Sections", font_size=18, bold=True)
        )
        panel.add_widget(
            WrappedLabel(
                text=(
                    "Navigate the project configuration by domain instead of "
                    "editing one flat form."
                ),
                font_size=14,
                color_role="text_muted",
            )
        )
        for section in state.sections:
            button = AppButton(
                text=f"{section.title}\n{section.description}",
                primary=section.key == state.selected_section_key,
                height=72,
            )
            button.disabled = section.key == state.selected_section_key
            button.bind(
                on_release=lambda _widget, key=section.key: (
                    self._select_project_editor_section(key)
                )
            )
            panel.add_widget(button)
        return panel

    def _build_section_content(
        self, state: ProjectEditorStateViewModel
    ) -> SurfaceBoxLayout:
        """Build section content.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        panel = SurfaceBoxLayout(
            orientation="vertical",
            spacing=12,
            padding=20,
            size_hint_y=None,
            background_role="card_background",
        )
        panel.bind(minimum_height=panel.setter("height"))
        panel.add_widget(
            WrappedLabel(text=state.selected_section_title, font_size=22, bold=True)
        )
        panel.add_widget(
            WrappedLabel(
                text=state.selected_section_description,
                font_size=14,
                color_role="text_muted",
            )
        )
        panel.add_widget(
            WrappedLabel(
                text=state.status_message or "",
                font_size=14,
                color_role="text_muted",
            )
        )
        if state.selected_section_key == "translation":
            panel.add_widget(self._build_translation_fields(state))
        elif state.selected_section_key == "remote":
            panel.add_widget(self._build_remote_fields(state))
            if state.connection_test_result is not None:
                panel.add_widget(self._build_remote_connection_test_card(state))
        elif state.selected_section_key == "sync":
            panel.add_widget(
                self._build_adapter_sync_filters_toggle(
                    state.editor.use_adapter_sync_filters
                )
            )
            panel.add_widget(self._build_sync_scope_panel(state))
        else:
            panel.add_widget(self._build_general_fields(state))
            panel.add_widget(self._build_active_toggle(state.editor.is_active))
        panel.add_widget(self._build_editor_actions(state))
        return panel

    def _build_general_fields(
        self, state: ProjectEditorStateViewModel
    ) -> SurfaceBoxLayout:
        """Build general fields.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=12,
            padding=0,
            size_hint_y=None,
            background_role="card_background",
        )
        card.bind(minimum_height=card.setter("height"))
        self._name_input = build_site_editor_text_input(state.editor.name)
        card.add_widget(build_site_editor_field_card("Name", self._name_input))
        self._framework_spinner = build_site_editor_spinner(
            values=[option.label for option in state.framework_options],
            current_label=find_option_label(
                state.framework_options,
                state.editor.framework_type,
            ),
        )
        card.add_widget(
            build_site_editor_field_card("Framework Type", self._framework_spinner)
        )
        self._local_path_input = build_site_editor_text_input(state.editor.local_path)
        card.add_widget(
            build_labeled_path_field(
                "Local Path",
                self._local_path_input,
                PathFieldPicker(
                    pick_mode="directory",
                    title="Choose project directory",
                    path_hint=lambda: (
                        self._local_path_input.text
                        if self._local_path_input is not None
                        else ""
                    ),
                ),
            ),
        )
        return card

    def _build_translation_fields(
        self,
        state: ProjectEditorStateViewModel,
    ) -> SurfaceBoxLayout:
        """Build translation fields.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=12,
            padding=0,
            size_hint_y=None,
            background_role="card_background",
        )
        card.bind(minimum_height=card.setter("height"))
        self._default_locale_input = build_site_editor_text_input(
            state.editor.default_locale
        )
        card.add_widget(
            build_site_editor_field_card("Default Locale", self._default_locale_input)
        )
        card.add_widget(self._build_compile_mo_toggle(state.editor.compile_mo))
        card.add_widget(
            self._build_use_external_translator_toggle(
                state.editor.use_external_translator
            )
        )
        card.add_widget(
            self._build_use_translation_cache_toggle(state.editor.use_translation_cache)
        )
        card.add_widget(self._build_only_fuzzy_toggle(state.editor.only_fuzzy))
        card.add_widget(self._build_dry_run_toggle(state.editor.dry_run))
        card.add_widget(self._build_stats_only_toggle(state.editor.stats_only))
        card.add_widget(
            self._build_report_inconsistencies_toggle(
                state.editor.report_inconsistencies
            )
        )
        return card

    def _build_remote_fields(
        self, state: ProjectEditorStateViewModel
    ) -> SurfaceBoxLayout:
        """Build remote fields.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=12,
            padding=0,
            size_hint_y=None,
            background_role="card_background",
        )
        card.bind(minimum_height=card.setter("height"))
        self._connection_type_spinner = build_site_editor_spinner(
            values=[option.label for option in state.connection_type_options],
            current_label=find_option_label(
                state.connection_type_options,
                state.editor.connection_type,
            ),
        )
        card.add_widget(
            build_site_editor_field_card(
                "Remote Connection Type", self._connection_type_spinner
            )
        )
        self._remote_host_input = build_site_editor_text_input(state.editor.remote_host)
        card.add_widget(
            build_site_editor_field_card("Remote Host", self._remote_host_input)
        )
        self._remote_port_input = build_site_editor_text_input(state.editor.remote_port)
        card.add_widget(
            build_site_editor_field_card("Remote Port", self._remote_port_input)
        )
        self._remote_username_input = build_site_editor_text_input(
            state.editor.remote_username
        )
        card.add_widget(
            build_site_editor_field_card(
                "Remote Username", self._remote_username_input
            ),
        )
        self._remote_password_input, remote_password_card = (
            build_remote_password_field_card(
                state.editor.remote_password,
            )
        )
        card.add_widget(remote_password_card)
        self._remote_path_input = build_site_editor_text_input(state.editor.remote_path)
        card.add_widget(
            build_site_editor_field_card("Remote Path", self._remote_path_input)
        )
        return card

    def _build_editor_actions(self, state: ProjectEditorStateViewModel) -> BoxLayout:
        """Build editor actions.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        actions = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=48
        )
        save_button = AppButton(text=state.submit_label, primary=True)
        save_button.bind(on_release=self._save_editor)
        self._test_connection_button = AppButton(
            text="Test Connection",
            primary=False,
            disabled=not state.connection_test_enabled,
        )
        self._test_connection_button.bind(on_release=self._test_connection)
        cancel_button = AppButton(text="Cancel", primary=False)
        cancel_button.bind(on_release=self._back_to_projects)
        actions.add_widget(save_button)
        actions.add_widget(self._test_connection_button)
        actions.add_widget(cancel_button)
        self._bind_connection_test_state_updates(state)
        self._refresh_test_connection_button_state(state)
        return actions

    def _reset_form_refs(self) -> None:
        """Reset form refs.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._name_input = None
        self._framework_spinner = None
        self._local_path_input = None
        self._default_locale_input = None
        self._compile_mo_switch = None
        self._use_external_translator_switch = None
        self._use_translation_cache_switch = None
        self._only_fuzzy_switch = None
        self._dry_run_switch = None
        self._stats_only_switch = None
        self._report_inconsistencies_switch = None
        self._connection_type_spinner = None
        self._remote_host_input = None
        self._remote_port_input = None
        self._remote_username_input = None
        self._remote_password_input = None
        self._remote_path_input = None
        self._is_active_switch = None
        self._use_adapter_sync_filters_switch = None
        self._sync_rule_path_input = None
        self._sync_rule_description_input = None
        self._sync_rule_filter_type_spinner = None
        self._sync_rule_behavior_spinner = None
        self._test_connection_button = None

    def _build_active_toggle(self, is_active: bool) -> SurfaceBoxLayout:
        """Build active toggle.

        Args:
            self:
                Value supplied to this callable.
            is_active:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(WrappedLabel(text="Is Active", font_size=16, bold=True))
        row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=40
        )
        row.add_widget(
            WrappedLabel(text="Enable this site in the primary registry listing.")
        )
        self._is_active_switch = Switch(
            active=is_active, size_hint=(None, None), size=(72, 36)
        )
        row.add_widget(self._is_active_switch)
        card.add_widget(row)
        return card

    def _build_compile_mo_toggle(self, is_enabled: bool) -> SurfaceBoxLayout:
        """Build compile mo toggle.

        Args:
            self:
                Value supplied to this callable.
            is_enabled:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(WrappedLabel(text="Compile MO Files", font_size=16, bold=True))
        row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=40
        )
        row.add_widget(
            WrappedLabel(
                text=(
                    "Enable MO compilation after the translation workflow "
                    "saves updated PO files."
                )
            )
        )
        self._compile_mo_switch = Switch(
            active=is_enabled,
            size_hint=(None, None),
            size=(72, 36),
        )
        row.add_widget(self._compile_mo_switch)
        card.add_widget(row)
        return card

    def _build_use_external_translator_toggle(
        self, is_enabled: bool
    ) -> SurfaceBoxLayout:
        """Build use external translator toggle.

        Args:
            self:
                Value supplied to this callable.
            is_enabled:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(
            WrappedLabel(text="Use External Translator", font_size=16, bold=True)
        )
        row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=40
        )
        row.add_widget(
            WrappedLabel(
                text=(
                    "Enable the external translator for untranslated entries "
                    "that cannot be resolved from other PO files in the same "
                    "family."
                )
            )
        )
        self._use_external_translator_switch = Switch(
            active=is_enabled,
            size_hint=(None, None),
            size=(72, 36),
        )
        row.add_widget(self._use_external_translator_switch)
        card.add_widget(row)
        return card

    def _build_dry_run_toggle(self, is_enabled: bool) -> SurfaceBoxLayout:
        """Build dry run toggle.

        Args:
            self:
                Value supplied to this callable.
            is_enabled:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(WrappedLabel(text="Dry-run", font_size=16, bold=True))
        row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=40
        )
        row.add_widget(
            WrappedLabel(
                text="Compute translation changes without writing PO or MO files."
            )
        )
        self._dry_run_switch = Switch(
            active=is_enabled, size_hint=(None, None), size=(72, 36)
        )
        row.add_widget(self._dry_run_switch)
        card.add_widget(row)
        return card

    def _build_only_fuzzy_toggle(self, is_enabled: bool) -> SurfaceBoxLayout:
        """Build only fuzzy toggle.

        Args:
            self:
                Value supplied to this callable.
            is_enabled:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(
            WrappedLabel(text="Only Fuzzy Entries", font_size=16, bold=True)
        )
        row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=40
        )
        row.add_widget(
            WrappedLabel(
                text=(
                    "Restrict external translation to gettext entries flagged as fuzzy."
                )
            )
        )
        self._only_fuzzy_switch = Switch(
            active=is_enabled, size_hint=(None, None), size=(72, 36)
        )
        row.add_widget(self._only_fuzzy_switch)
        card.add_widget(row)
        return card

    def _build_use_translation_cache_toggle(self, is_enabled: bool) -> SurfaceBoxLayout:
        """Build use translation cache toggle.

        Args:
            self:
                Value supplied to this callable.
            is_enabled:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(
            WrappedLabel(text="Use Translation Cache", font_size=16, bold=True)
        )
        row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=40
        )
        row.add_widget(
            WrappedLabel(
                text=(
                    "Reuse cached external-translation results before calling "
                    "the provider again for the same base-language text."
                )
            )
        )
        self._use_translation_cache_switch = Switch(
            active=is_enabled,
            size_hint=(None, None),
            size=(72, 36),
        )
        row.add_widget(self._use_translation_cache_switch)
        card.add_widget(row)
        return card

    def _build_stats_only_toggle(self, is_enabled: bool) -> SurfaceBoxLayout:
        """Build stats only toggle.

        Args:
            self:
                Value supplied to this callable.
            is_enabled:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(WrappedLabel(text="Stats Only", font_size=16, bold=True))
        row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=40
        )
        row.add_widget(
            WrappedLabel(
                text="Collect translation workflow statistics without writing files."
            )
        )
        self._stats_only_switch = Switch(
            active=is_enabled,
            size_hint=(None, None),
            size=(72, 36),
        )
        row.add_widget(self._stats_only_switch)
        card.add_widget(row)
        return card

    def _build_report_inconsistencies_toggle(
        self, is_enabled: bool
    ) -> SurfaceBoxLayout:
        """Build report inconsistencies toggle.

        Args:
            self:
                Value supplied to this callable.
            is_enabled:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(
            WrappedLabel(text="Report Inconsistencies", font_size=16, bold=True)
        )
        row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=40
        )
        row.add_widget(
            WrappedLabel(
                text="Report differing translated values across locale variants."
            )
        )
        self._report_inconsistencies_switch = Switch(
            active=is_enabled,
            size_hint=(None, None),
            size=(72, 36),
        )
        row.add_widget(self._report_inconsistencies_switch)
        card.add_widget(row)
        return card

    def _build_remote_connection_test_card(
        self,
        state: ProjectEditorStateViewModel,
    ) -> SurfaceBoxLayout:
        """Show connection test output and optional SSH host-key trust flow.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ValueError:
                Raised when this callable hits the corresponding error path.
        """
        result = state.connection_test_result
        if result is None:
            msg = "Connection test result is required to build the test card."
            raise ValueError(msg)
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=16,
            size_hint_y=None,
            background_role="card_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(
            WrappedLabel(text="Remote Connection Test", font_size=18, bold=True)
        )
        card.add_widget(
            WrappedLabel(
                text=result.message,
                font_size=14,
                color_role="text_muted",
            )
        )
        if not result.success and result.error_code == "unknown_ssh_host_key":
            trust_button = AppButton(
                text="Trust SSH Host Key and Retry",
                primary=True,
                size_hint_y=None,
                height=48,
            )
            trust_button.bind(
                on_release=lambda *_args: open_ssh_host_key_trust_confirmation(
                    on_trust=self._retest_connection_with_trusted_host_key,
                    purpose="connection_test",
                ),
            )
            card.add_widget(trust_button)
        return card

    def _retest_connection_with_trusted_host_key(self) -> None:
        """Handle retest connection with trusted host key.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        state = self._require_state()
        editor = self._collect_editor_from_form(state)
        self._draft_editor = editor
        self._shell.trust_project_editor_remote_host_key(editor)
        self.refresh()

    def _build_sync_scope_panel(
        self, state: ProjectEditorStateViewModel
    ) -> SurfaceBoxLayout:
        """Build sync scope panel.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=10,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(
            WrappedLabel(text="Resolved Sync Scope", font_size=16, bold=True)
        )
        card.add_widget(
            WrappedLabel(
                text=f"Status: {state.sync_scope_status}",
                font_size=14,
                color_role="text_muted",
            )
        )
        card.add_widget(
            WrappedLabel(
                text=state.sync_scope_message,
                font_size=14,
                color_role="text_muted",
            )
        )
        refresh_button = AppButton(text="Refresh Sync Scope", primary=False)
        refresh_button.bind(on_release=self._refresh_sync_scope)
        card.add_widget(refresh_button)
        if state.editor.sync_rule_items == ():
            card.add_widget(
                WrappedLabel(
                    text="No adapter or project sync rules are currently available.",
                    font_size=14,
                    color_role="text_muted",
                )
            )
        else:
            for item in state.editor.sync_rule_items:
                card.add_widget(self._build_sync_rule_item(state, item))
        card.add_widget(self._build_custom_sync_rule_form(state))
        return card

    def _build_sync_rule_item(
        self,
        state: ProjectEditorStateViewModel,
        item: SyncRuleEditorItemViewModel,
    ) -> SurfaceBoxLayout:
        """Build sync rule item.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.
            item:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=12,
            size_hint_y=None,
            background_role="card_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(WrappedLabel(text=item.relative_path, font_size=15, bold=True))
        card.add_widget(
            WrappedLabel(
                text=(
                    f"{item.behavior.title()} {item.filter_type} rule from "
                    f"{item.source}."
                ),
                font_size=13,
                color_role="text_muted",
            )
        )
        if item.description != "":
            card.add_widget(
                WrappedLabel(
                    text=item.description,
                    font_size=13,
                    color_role="text_muted",
                )
            )
        row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=40
        )
        row.add_widget(WrappedLabel(text="Enabled"))
        item_switch = Switch(
            active=item.is_enabled, size_hint=(None, None), size=(72, 36)
        )
        item_switch.bind(
            active=lambda _instance, value, rule_key=item.rule_key: (
                self._toggle_sync_rule(state, rule_key, value)
            )
        )
        row.add_widget(item_switch)
        if item.is_removable:
            remove_button = AppButton(text="Remove", primary=False)
            remove_button.bind(
                on_release=lambda *_args, rule_key=item.rule_key: (
                    self._remove_sync_rule(state, rule_key)
                )
            )
            row.add_widget(remove_button)
        card.add_widget(row)
        return card

    def _build_custom_sync_rule_form(
        self,
        state: ProjectEditorStateViewModel,
    ) -> SurfaceBoxLayout:
        """Build custom sync rule form.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=12,
            size_hint_y=None,
            background_role="card_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(
            WrappedLabel(text="Project Sync Rule Overrides", font_size=15, bold=True)
        )
        self._sync_rule_path_input = build_site_editor_text_input("")
        card.add_widget(
            build_site_editor_field_card("Relative Path", self._sync_rule_path_input)
        )
        self._sync_rule_description_input = build_site_editor_text_input("")
        card.add_widget(
            build_site_editor_field_card(
                "Description", self._sync_rule_description_input
            )
        )
        self._sync_rule_filter_type_spinner = build_site_editor_spinner(
            values=[option.label for option in state.sync_rule_filter_type_options],
            current_label=state.sync_rule_filter_type_options[0].label,
        )
        card.add_widget(
            build_site_editor_field_card(
                "Filter Type", self._sync_rule_filter_type_spinner
            )
        )
        self._sync_rule_behavior_spinner = build_site_editor_spinner(
            values=[option.label for option in state.sync_rule_behavior_options],
            current_label=state.sync_rule_behavior_options[0].label,
        )
        card.add_widget(
            build_site_editor_field_card("Behavior", self._sync_rule_behavior_spinner)
        )
        add_button = AppButton(text="Add Project Rule", primary=False)
        add_button.bind(on_release=lambda *_args: self._add_sync_rule(state))
        card.add_widget(add_button)
        return card

    def _build_adapter_sync_filters_toggle(self, is_enabled: bool) -> SurfaceBoxLayout:
        """Build adapter sync filters toggle.

        Args:
            self:
                Value supplied to this callable.
            is_enabled:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(
            WrappedLabel(text="Use Adapter Sync Filters", font_size=16, bold=True)
        )
        row = BoxLayout(
            orientation="horizontal", spacing=12, size_hint_y=None, height=40
        )
        row.add_widget(
            WrappedLabel(
                text=(
                    "When enabled, sync uses the current framework adapter "
                    "scope instead of transferring the full remote/local tree."
                )
            )
        )
        self._use_adapter_sync_filters_switch = Switch(
            active=is_enabled,
            size_hint=(None, None),
            size=(72, 36),
        )
        row.add_widget(self._use_adapter_sync_filters_switch)
        card.add_widget(row)
        return card

    def _save_editor(self, *_args: object) -> None:
        """Save editor.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        state = self._require_state()
        editor = self._collect_editor_from_form(state)
        self._draft_editor = editor
        if state.mode == "edit" and editor.site_id is not None:
            self._shell.save_project_edits(editor.site_id, editor)
        else:
            self._shell.save_new_project(editor)
        if self._shell.router.current.name.value == "project-detail":
            self.show_route("project_detail")
            return
        self.refresh()

    def _test_connection(self, *_args: object) -> None:
        """Handle test connection.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        state = self._require_state()
        editor = self._collect_editor_from_form(state)
        self._draft_editor = editor
        self._shell.test_project_connection(editor)
        self.refresh()

    def _refresh_sync_scope(self, *_args: object) -> None:
        """Refresh sync scope.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        state = self._require_state()
        editor = self._collect_editor_from_form(state)
        self._draft_editor = editor
        self._shell.preview_project_editor(editor)
        self.refresh()

    def _toggle_sync_rule(
        self,
        state: ProjectEditorStateViewModel,
        rule_key: str,
        is_enabled: bool,
    ) -> None:
        """Handle toggle sync rule.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.
            rule_key:
                Value supplied to this callable.
            is_enabled:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        current_items = self._current_sync_rule_items(state)
        next_items = tuple(
            item if item.rule_key != rule_key else _with_rule_enabled(item, is_enabled)
            for item in current_items
        )
        editor = self._collect_editor_from_form(state, sync_rule_items=next_items)
        self._draft_editor = editor
        self._shell.preview_project_editor(editor)
        self.refresh()

    def _remove_sync_rule(
        self,
        state: ProjectEditorStateViewModel,
        rule_key: str,
    ) -> None:
        """Handle remove sync rule.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.
            rule_key:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        next_items = tuple(
            item
            for item in self._current_sync_rule_items(state)
            if item.rule_key != rule_key
        )
        editor = self._collect_editor_from_form(state, sync_rule_items=next_items)
        self._draft_editor = editor
        self._shell.preview_project_editor(editor)
        self.refresh()

    def _add_sync_rule(self, state: ProjectEditorStateViewModel) -> None:
        """Handle add sync rule.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        relative_path = self._optional_text(self._sync_rule_path_input)
        filter_type = self._require_framework_value(
            state.sync_rule_filter_type_options,
            self._sync_rule_filter_type_spinner,
        )
        behavior = self._require_framework_value(
            state.sync_rule_behavior_options,
            self._sync_rule_behavior_spinner,
        )
        next_items = (
            *self._current_sync_rule_items(state),
            SyncRuleEditorItemViewModel(
                rule_key="",
                target_rule_key=None,
                relative_path=relative_path,
                filter_type=filter_type,
                behavior=behavior,
                description=self._optional_text(self._sync_rule_description_input),
                source="project",
                is_enabled=True,
                is_removable=True,
            ),
        )
        editor = self._collect_editor_from_form(
            state, sync_rule_items=tuple(next_items)
        )
        self._draft_editor = editor
        self._shell.preview_project_editor(editor)
        self.refresh()

    def _back_to_projects(self, *_args: object) -> None:
        """Handle back to projects.

        Args:
            self:
                Value supplied to this callable.
            *_args:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._shell.open_projects()
        self.show_route("projects")

    def _select_project_editor_section(self, section_key: str) -> None:
        """Select project editor section.

        Args:
            self:
                Value supplied to this callable.
            section_key:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        state = self._require_state()
        editor = self._collect_editor_from_form(state)
        self._draft_editor = editor
        self._shell.project_editor_state = replace(state, editor=editor)
        self._shell.select_project_editor_section(section_key)
        self._draft_editor = self._require_state().editor
        self.refresh()

    def _require_state(self) -> ProjectEditorStateViewModel:
        """Validate and return state.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ValueError:
                Raised when this callable hits the corresponding error path.
        """
        state = self._shell.project_editor_state
        if state is None:
            msg = "Project editor state must be loaded before rendering the screen."
            raise ValueError(msg)
        return state

    def _require_text(self, field: TextInput | None) -> str:
        """Validate and return text.

        Args:
            self:
                Value supplied to this callable.
            field:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ValueError:
                Raised when this callable hits the corresponding error path.
        """
        if field is None:
            msg = "Project editor input field is not available."
            raise ValueError(msg)
        return str(field.text).strip()

    def _optional_text(self, field: TextInput | None) -> str:
        """Handle optional text.

        Args:
            self:
                Value supplied to this callable.
            field:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ValueError:
                Raised when this callable hits the corresponding error path.
        """
        if field is None:
            msg = "Project editor input field is not available."
            raise ValueError(msg)
        return str(field.text).strip()

    def _current_sync_rule_items(
        self,
        state: ProjectEditorStateViewModel,
    ) -> tuple[SyncRuleEditorItemViewModel, ...]:
        """Handle current sync rule items.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if self._draft_editor is None:
            return state.editor.sync_rule_items
        return self._draft_editor.sync_rule_items

    def _collect_editor_from_form(
        self,
        state: ProjectEditorStateViewModel,
        *,
        sync_rule_items: tuple[SyncRuleEditorItemViewModel, ...] | None = None,
    ) -> SiteEditorViewModel:
        """Collect editor from form.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.
            sync_rule_items:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return SiteEditorViewModel(
            site_id=state.editor.site_id,
            name=self._text_or_fallback(self._name_input, state.editor.name),
            framework_type=self._spinner_value_or_fallback(
                options=state.framework_options,
                field=self._framework_spinner,
                fallback=state.editor.framework_type,
            ),
            local_path=self._text_or_fallback(
                self._local_path_input, state.editor.local_path
            ),
            default_locale=self._text_or_fallback(
                self._default_locale_input,
                state.editor.default_locale,
            ),
            compile_mo=(
                self._compile_mo_switch.active
                if self._compile_mo_switch is not None
                else state.editor.compile_mo
            ),
            use_external_translator=(
                self._use_external_translator_switch.active
                if self._use_external_translator_switch is not None
                else state.editor.use_external_translator
            ),
            use_translation_cache=(
                self._use_translation_cache_switch.active
                if self._use_translation_cache_switch is not None
                else state.editor.use_translation_cache
            ),
            only_fuzzy=(
                self._only_fuzzy_switch.active
                if self._only_fuzzy_switch is not None
                else state.editor.only_fuzzy
            ),
            dry_run=(
                self._dry_run_switch.active
                if self._dry_run_switch is not None
                else state.editor.dry_run
            ),
            stats_only=(
                self._stats_only_switch.active
                if self._stats_only_switch is not None
                else state.editor.stats_only
            ),
            report_inconsistencies=(
                self._report_inconsistencies_switch.active
                if self._report_inconsistencies_switch is not None
                else state.editor.report_inconsistencies
            ),
            connection_type=self._spinner_value_or_fallback(
                options=state.connection_type_options,
                field=self._connection_type_spinner,
                fallback=state.editor.connection_type,
            ),
            remote_host=self._text_or_fallback(
                self._remote_host_input, state.editor.remote_host
            ),
            remote_port=self._text_or_fallback(
                self._remote_port_input, state.editor.remote_port
            ),
            remote_username=self._text_or_fallback(
                self._remote_username_input,
                state.editor.remote_username,
            ),
            remote_password=self._text_or_fallback(
                self._remote_password_input,
                state.editor.remote_password,
            ),
            remote_path=self._text_or_fallback(
                self._remote_path_input, state.editor.remote_path
            ),
            is_active=(
                self._is_active_switch.active
                if self._is_active_switch is not None
                else state.editor.is_active
            ),
            remote_verify_host=True,
            use_adapter_sync_filters=(
                self._use_adapter_sync_filters_switch.active
                if self._use_adapter_sync_filters_switch is not None
                else state.editor.use_adapter_sync_filters
            ),
            sync_rule_items=(
                self._current_sync_rule_items(state)
                if sync_rule_items is None
                else sync_rule_items
            ),
        )

    def _bind_connection_test_state_updates(
        self, state: ProjectEditorStateViewModel
    ) -> None:
        """Handle bind connection test state updates.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        bindable_fields = [
            self._connection_type_spinner,
            self._remote_host_input,
            self._remote_port_input,
            self._remote_username_input,
            self._remote_password_input,
            self._remote_path_input,
        ]
        for field in bindable_fields:
            if field is not None:
                field.bind(
                    text=lambda *_args, editor_state=state: (
                        self._refresh_test_connection_button_state(editor_state)
                    )
                )

    def _refresh_test_connection_button_state(
        self, state: ProjectEditorStateViewModel
    ) -> None:
        """Refresh test connection button state.

        Args:
            self:
                Value supplied to this callable.
            state:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if self._test_connection_button is None:
            return
        connection_type = self._spinner_value_or_fallback(
            options=state.connection_type_options,
            field=self._connection_type_spinner,
            fallback=state.editor.connection_type,
        )
        remote_port = self._text_or_fallback(
            self._remote_port_input, state.editor.remote_port
        )
        self._test_connection_button.disabled = not (
            connection_type != "none"
            and self._text_or_fallback(
                self._remote_host_input, state.editor.remote_host
            )
            != ""
            and remote_port.isdigit()
            and int(remote_port) > 0
            and self._text_or_fallback(
                self._remote_username_input, state.editor.remote_username
            )
            != ""
            and self._text_or_fallback(
                self._remote_password_input, state.editor.remote_password
            )
            != ""
            and self._text_or_fallback(
                self._remote_path_input, state.editor.remote_path
            )
            != ""
        )

    def _require_framework_value(
        self,
        options: list[SettingsOptionViewModel],
        field: Spinner | None,
    ) -> str:
        """Validate and return framework value.

        Args:
            self:
                Value supplied to this callable.
            options:
                Value supplied to this callable.
            field:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ValueError:
                Raised when this callable hits the corresponding error path.
        """
        if field is None:
            msg = "Project editor input field is not available."
            raise ValueError(msg)
        return find_option_value(options, str(field.text).strip())

    @staticmethod
    def _text_or_fallback(field: TextInput | None, fallback: str) -> str:
        """Handle text or fallback.

        Args:
            field:
                Value supplied to this callable.
            fallback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if field is None:
            return fallback
        return str(field.text).strip()

    @staticmethod
    def _spinner_value_or_fallback(
        *,
        options: list[SettingsOptionViewModel],
        field: Spinner | None,
        fallback: str,
    ) -> str:
        """Handle spinner value or fallback.

        Args:
            options:
                Value supplied to this callable.
            field:
                Value supplied to this callable.
            fallback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if field is None:
            return fallback
        return find_option_value(options, str(field.text).strip())


def _build_information_card(*, title: str, body: str) -> SurfaceBoxLayout:
    """Build information card.

    Args:
        title:
            Value supplied to this callable.
        body:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
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


def _with_rule_enabled(
    item: SyncRuleEditorItemViewModel,
    is_enabled: bool,
) -> SyncRuleEditorItemViewModel:
    """Return rule enabled.

    Args:
        item:
            Value supplied to this callable.
        is_enabled:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return SyncRuleEditorItemViewModel(
        rule_key=item.rule_key,
        target_rule_key=item.target_rule_key,
        relative_path=item.relative_path,
        filter_type=item.filter_type,
        behavior=item.behavior,
        description=item.description,
        source=item.source,
        is_enabled=is_enabled,
        is_removable=item.is_removable,
    )
