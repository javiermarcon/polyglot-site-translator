"""Project editor screen."""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.base import BaseShellScreen
from polyglot_site_translator.presentation.kivy.theme import get_active_theme
from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
)
from polyglot_site_translator.presentation.view_models import (
    ProjectEditorStateViewModel,
    SettingsOptionViewModel,
    SiteEditorViewModel,
    SyncRuleEditorItemViewModel,
)


class ProjectEditorScreen(BaseShellScreen):
    """Screen for creating and editing site registry records."""

    def __init__(self, *, shell: FrontendShell, manager_ref: ScreenManager) -> None:
        super().__init__(
            screen_name="project_editor",
            title="Register Project",
            subtitle="Create or update site registry records without exposing SQL in the UI.",
            shell=shell,
            manager_ref=manager_ref,
        )
        self.add_nav_button("Back to Projects", self._back_to_projects, primary=False)
        self._draft_editor: SiteEditorViewModel | None = None
        self._name_input: TextInput | None = None
        self._framework_spinner: Spinner | None = None
        self._local_path_input: TextInput | None = None
        self._default_locale_input: TextInput | None = None
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
        self.clear_content()
        state = self._shell.project_editor_state
        if state is None:
            self._content.add_widget(
                _build_information_card(
                    title="Project Editor",
                    body="Open the register or edit workflow to load a project editor draft.",
                )
            )
            self.update_error_label()
            return
        self.set_screen_copy(
            title=state.title,
            subtitle="Persisted through the site registry service.",
        )
        self._draft_editor = state.editor
        self._content.add_widget(self._build_form_panel(state))
        self.update_error_label()

    def _build_form_panel(self, state: ProjectEditorStateViewModel) -> SurfaceBoxLayout:
        panel = SurfaceBoxLayout(
            orientation="vertical",
            spacing=12,
            padding=20,
            size_hint_y=None,
            background_role="card_background",
        )
        panel.bind(minimum_height=panel.setter("height"))
        panel.add_widget(WrappedLabel(text=state.title, font_size=22, bold=True))
        panel.add_widget(
            WrappedLabel(
                text=state.status_message or "",
                font_size=14,
                color_role="text_muted",
            )
        )
        self._name_input = self._build_text_input(state.editor.name)
        panel.add_widget(_build_field("Name", self._name_input))
        self._framework_spinner = self._build_spinner(
            values=[option.label for option in state.framework_options],
            current_label=_find_option_label(
                state.framework_options,
                state.editor.framework_type,
            ),
        )
        panel.add_widget(_build_field("Framework Type", self._framework_spinner))
        self._local_path_input = self._build_text_input(state.editor.local_path)
        panel.add_widget(_build_field("Local Path", self._local_path_input))
        self._default_locale_input = self._build_text_input(state.editor.default_locale)
        panel.add_widget(_build_field("Default Locale", self._default_locale_input))
        self._connection_type_spinner = self._build_spinner(
            values=[option.label for option in state.connection_type_options],
            current_label=_find_option_label(
                state.connection_type_options,
                state.editor.connection_type,
            ),
        )
        panel.add_widget(_build_field("Remote Connection Type", self._connection_type_spinner))
        self._remote_host_input = self._build_text_input(state.editor.remote_host)
        panel.add_widget(_build_field("Remote Host", self._remote_host_input))
        self._remote_port_input = self._build_text_input(state.editor.remote_port)
        panel.add_widget(_build_field("Remote Port", self._remote_port_input))
        self._remote_username_input = self._build_text_input(state.editor.remote_username)
        panel.add_widget(_build_field("Remote Username", self._remote_username_input))
        self._remote_password_input = self._build_text_input(
            state.editor.remote_password,
            password=True,
        )
        panel.add_widget(_build_field("Remote Password", self._remote_password_input))
        self._remote_path_input = self._build_text_input(state.editor.remote_path)
        panel.add_widget(_build_field("Remote Path", self._remote_path_input))
        panel.add_widget(
            self._build_adapter_sync_filters_toggle(state.editor.use_adapter_sync_filters)
        )
        panel.add_widget(self._build_sync_scope_panel(state))
        if state.connection_test_result is not None:
            panel.add_widget(
                _build_information_card(
                    title="Remote Connection Test",
                    body=state.connection_test_result.message,
                )
            )
        panel.add_widget(self._build_active_toggle(state.editor.is_active))
        actions = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=48)
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
        panel.add_widget(actions)
        return panel

    def _build_text_input(self, value: str, *, password: bool = False) -> TextInput:
        palette = get_active_theme()
        return TextInput(
            text=value,
            multiline=False,
            password=password,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            foreground_color=palette.text_primary,
            cursor_color=palette.text_primary,
        )

    def _build_spinner(self, *, values: list[str], current_label: str) -> Spinner:
        palette = get_active_theme()
        return Spinner(
            text=current_label,
            values=values,
            size_hint_y=None,
            height=44,
            background_color=palette.card_subtle_background,
            color=palette.text_primary,
        )

    def _build_active_toggle(self, is_active: bool) -> SurfaceBoxLayout:
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(WrappedLabel(text="Is Active", font_size=16, bold=True))
        row = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=40)
        row.add_widget(WrappedLabel(text="Enable this site in the primary registry listing."))
        self._is_active_switch = Switch(active=is_active, size_hint=(None, None), size=(72, 36))
        row.add_widget(self._is_active_switch)
        card.add_widget(row)
        return card

    def _build_sync_scope_panel(self, state: ProjectEditorStateViewModel) -> SurfaceBoxLayout:
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=10,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(WrappedLabel(text="Resolved Sync Scope", font_size=16, bold=True))
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
                text=(f"{item.behavior.title()} {item.filter_type} rule from {item.source}."),
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
        row = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=40)
        row.add_widget(WrappedLabel(text="Enabled"))
        item_switch = Switch(active=item.is_enabled, size_hint=(None, None), size=(72, 36))
        item_switch.bind(
            active=lambda _instance, value, rule_key=item.rule_key: self._toggle_sync_rule(
                state, rule_key, value
            )
        )
        row.add_widget(item_switch)
        if item.is_removable:
            remove_button = AppButton(text="Remove", primary=False)
            remove_button.bind(
                on_release=lambda *_args, rule_key=item.rule_key: self._remove_sync_rule(
                    state, rule_key
                )
            )
            row.add_widget(remove_button)
        card.add_widget(row)
        return card

    def _build_custom_sync_rule_form(
        self,
        state: ProjectEditorStateViewModel,
    ) -> SurfaceBoxLayout:
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=12,
            size_hint_y=None,
            background_role="card_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(WrappedLabel(text="Project Sync Rule Overrides", font_size=15, bold=True))
        self._sync_rule_path_input = self._build_text_input("")
        card.add_widget(_build_field("Relative Path", self._sync_rule_path_input))
        self._sync_rule_description_input = self._build_text_input("")
        card.add_widget(_build_field("Description", self._sync_rule_description_input))
        self._sync_rule_filter_type_spinner = self._build_spinner(
            values=[option.label for option in state.sync_rule_filter_type_options],
            current_label=state.sync_rule_filter_type_options[0].label,
        )
        card.add_widget(_build_field("Filter Type", self._sync_rule_filter_type_spinner))
        self._sync_rule_behavior_spinner = self._build_spinner(
            values=[option.label for option in state.sync_rule_behavior_options],
            current_label=state.sync_rule_behavior_options[0].label,
        )
        card.add_widget(_build_field("Behavior", self._sync_rule_behavior_spinner))
        add_button = AppButton(text="Add Project Rule", primary=False)
        add_button.bind(on_release=lambda *_args: self._add_sync_rule(state))
        card.add_widget(add_button)
        return card

    def _build_adapter_sync_filters_toggle(self, is_enabled: bool) -> SurfaceBoxLayout:
        card = SurfaceBoxLayout(
            orientation="vertical",
            spacing=8,
            padding=14,
            size_hint_y=None,
            background_role="card_subtle_background",
        )
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(WrappedLabel(text="Use Adapter Sync Filters", font_size=16, bold=True))
        row = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=40)
        row.add_widget(
            WrappedLabel(
                text=(
                    "When enabled, sync uses the current framework adapter scope instead "
                    "of transferring the full remote/local tree."
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
        state = self._require_state()
        editor = self._collect_editor_from_form(state)
        self._draft_editor = editor
        self._shell.test_project_connection(editor)
        self.refresh()

    def _refresh_sync_scope(self, *_args: object) -> None:
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
        next_items = tuple(
            item for item in self._current_sync_rule_items(state) if item.rule_key != rule_key
        )
        editor = self._collect_editor_from_form(state, sync_rule_items=next_items)
        self._draft_editor = editor
        self._shell.preview_project_editor(editor)
        self.refresh()

    def _add_sync_rule(self, state: ProjectEditorStateViewModel) -> None:
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
        editor = self._collect_editor_from_form(state, sync_rule_items=tuple(next_items))
        self._draft_editor = editor
        self._shell.preview_project_editor(editor)
        self.refresh()

    def _back_to_projects(self, *_args: object) -> None:
        self._shell.open_projects()
        self.show_route("projects")

    def _require_state(self) -> ProjectEditorStateViewModel:
        state = self._shell.project_editor_state
        if state is None:
            msg = "Project editor state must be loaded before rendering the screen."
            raise ValueError(msg)
        return state

    def _require_text(self, field: TextInput | None) -> str:
        if field is None:
            msg = "Project editor input field is not available."
            raise ValueError(msg)
        return str(field.text).strip()

    def _optional_text(self, field: TextInput | None) -> str:
        if field is None:
            msg = "Project editor input field is not available."
            raise ValueError(msg)
        return str(field.text).strip()

    def _current_sync_rule_items(
        self,
        state: ProjectEditorStateViewModel,
    ) -> tuple[SyncRuleEditorItemViewModel, ...]:
        if self._draft_editor is None:
            return state.editor.sync_rule_items
        return self._draft_editor.sync_rule_items

    def _collect_editor_from_form(
        self,
        state: ProjectEditorStateViewModel,
        *,
        sync_rule_items: tuple[SyncRuleEditorItemViewModel, ...] | None = None,
    ) -> SiteEditorViewModel:
        return SiteEditorViewModel(
            site_id=state.editor.site_id,
            name=self._require_text(self._name_input),
            framework_type=self._require_framework_value(
                state.framework_options,
                self._framework_spinner,
            ),
            local_path=self._require_text(self._local_path_input),
            default_locale=self._require_text(self._default_locale_input),
            connection_type=self._require_framework_value(
                state.connection_type_options,
                self._connection_type_spinner,
            ),
            remote_host=self._optional_text(self._remote_host_input),
            remote_port=self._optional_text(self._remote_port_input),
            remote_username=self._optional_text(self._remote_username_input),
            remote_password=self._optional_text(self._remote_password_input),
            remote_path=self._optional_text(self._remote_path_input),
            is_active=self._is_active_switch.active if self._is_active_switch is not None else True,
            remote_verify_host=True,
            use_adapter_sync_filters=(
                self._use_adapter_sync_filters_switch.active
                if self._use_adapter_sync_filters_switch is not None
                else False
            ),
            sync_rule_items=(
                self._current_sync_rule_items(state) if sync_rule_items is None else sync_rule_items
            ),
        )

    def _bind_connection_test_state_updates(self, state: ProjectEditorStateViewModel) -> None:
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

    def _refresh_test_connection_button_state(self, state: ProjectEditorStateViewModel) -> None:
        if self._test_connection_button is None:
            return
        connection_type = self._require_framework_value(
            state.connection_type_options,
            self._connection_type_spinner,
        )
        remote_port = self._optional_text(self._remote_port_input)
        self._test_connection_button.disabled = not (
            connection_type != "none"
            and self._optional_text(self._remote_host_input) != ""
            and remote_port.isdigit()
            and int(remote_port) > 0
            and self._optional_text(self._remote_username_input) != ""
            and self._optional_text(self._remote_password_input) != ""
            and self._optional_text(self._remote_path_input) != ""
        )

    def _require_framework_value(
        self,
        options: list[SettingsOptionViewModel],
        field: Spinner | None,
    ) -> str:
        if field is None:
            msg = "Project editor input field is not available."
            raise ValueError(msg)
        return _find_option_value(options, str(field.text).strip())


def _build_field(label: str, field: Widget) -> SurfaceBoxLayout:
    card = SurfaceBoxLayout(
        orientation="vertical",
        spacing=8,
        padding=14,
        size_hint_y=None,
        background_role="card_subtle_background",
    )
    card.bind(minimum_height=card.setter("height"))
    card.add_widget(WrappedLabel(text=label, font_size=16, bold=True))
    card.add_widget(field)
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


def _with_rule_enabled(
    item: SyncRuleEditorItemViewModel,
    is_enabled: bool,
) -> SyncRuleEditorItemViewModel:
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
