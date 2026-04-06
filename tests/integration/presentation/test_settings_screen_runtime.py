"""Runtime-focused tests for the Kivy settings screen."""

from __future__ import annotations

from typing import Any, cast

from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
import pytest

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.presentation.kivy.screens.settings import (
    _find_option_label,
    _find_option_value,
)
from polyglot_site_translator.presentation.kivy.theme import (
    get_active_theme_mode,
    resolve_theme_palette,
    set_active_theme_mode,
)
from polyglot_site_translator.presentation.kivy.widgets.common import WrappedLabel
from polyglot_site_translator.presentation.view_models import SettingsOptionViewModel


@pytest.fixture(autouse=True)
def restore_runtime_settings() -> object:
    previous_size = tuple(Window.size)
    previous_theme_mode = get_active_theme_mode()
    yield
    Window.size = previous_size
    set_active_theme_mode(previous_theme_mode)


def test_settings_screen_can_refresh_without_button_keyword_conflicts() -> None:
    app = cast(Any, create_kivy_app())
    root = app.build()
    settings_screen = root.get_screen("settings")

    settings_screen._shell.open_settings()
    settings_screen.refresh()

    assert root.has_screen("settings")


def test_save_changes_button_refreshes_the_visible_status_message() -> None:
    app = cast(Any, create_kivy_app())
    root = app.build()
    settings_screen = root.get_screen("settings")

    settings_screen._shell.open_settings()
    root.current = "settings"
    settings_screen.refresh()
    settings_screen._shell.toggle_remember_last_screen()
    settings_screen.refresh()

    save_button = _find_button_by_text(settings_screen, "Save Changes")
    save_button.dispatch("on_release")

    assert settings_screen._shell.settings_state is not None
    assert settings_screen._shell.settings_state.status == "saved"
    assert "Settings saved." in _collect_label_texts(settings_screen)


def test_save_changes_persists_theme_and_resolution_from_the_screen_form() -> None:
    app = cast(Any, create_kivy_app())
    root = app.build()
    settings_screen = root.get_screen("settings")

    settings_screen._shell.open_settings()
    root.current = "settings"
    settings_screen.refresh()

    width_input, height_input = _find_window_inputs(settings_screen)
    width_input.text = "1440"
    height_input.text = "900"

    theme_spinner = _find_spinner_by_text(settings_screen, "System")
    theme_spinner.text = "Dark"

    save_button = _find_button_by_text(settings_screen, "Save Changes")
    save_button.dispatch("on_release")

    assert settings_screen._shell.settings_state is not None
    assert settings_screen._shell.settings_state.app_settings.theme_mode == "dark"
    assert settings_screen._shell.settings_state.app_settings.window_width == 1440
    assert settings_screen._shell.settings_state.app_settings.window_height == 900
    assert tuple(Window.size) == (1440, 900)
    assert get_active_theme_mode() == "dark"
    assert tuple(settings_screen._container._background_instruction.rgba) == (
        resolve_theme_palette("dark").app_background
    )

    reopened_width, reopened_height = _find_window_inputs(settings_screen)
    assert reopened_width.text == "1440"
    assert reopened_height.text == "900"


def test_settings_screen_switches_to_compact_layout_for_narrow_windows() -> None:
    app = cast(Any, create_kivy_app())
    root = app.build()
    settings_screen = root.get_screen("settings")

    settings_screen._shell.open_settings()
    root.current = "settings"
    settings_screen.refresh()

    width_input, height_input = _find_window_inputs(settings_screen)
    width_input.text = "550"
    height_input.text = "700"

    save_button = _find_button_by_text(settings_screen, "Save Changes")
    save_button.dispatch("on_release")

    assert settings_screen._layout_spec.mode == "compact"
    assert settings_screen._layout_spec.main_columns == 1
    assert settings_screen._layout_spec.action_orientation == "vertical"
    assert tuple(Window.size) == (550, 700)


def test_settings_screen_handles_section_selection_defaults_and_dashboard_navigation() -> None:
    app = cast(Any, create_kivy_app())
    root = app.build()
    settings_screen = root.get_screen("settings")

    settings_screen._shell.open_settings()
    root.current = "settings"
    settings_screen.refresh()

    settings_screen._select_settings_section("translation")
    assert settings_screen._shell.settings_state is not None
    assert settings_screen._shell.settings_state.selected_section_key == "translation"
    assert "Planned Section" in _collect_label_texts(settings_screen)

    settings_screen._select_settings_section("app-ui-kivy")
    remember_label = WrappedLabel(text="")
    developer_label = WrappedLabel(text="")
    settings_screen._toggle_remember_last_screen(None, True, remember_label)
    settings_screen._toggle_developer_mode(None, True, developer_label)
    settings_screen._on_theme_mode_selected(None, "Light")
    settings_screen._on_ui_language_selected(None, "Spanish")

    assert settings_screen._draft_settings is not None
    assert settings_screen._draft_settings.remember_last_screen is True
    assert settings_screen._draft_settings.developer_mode is True
    assert settings_screen._draft_settings.theme_mode == "light"
    assert settings_screen._draft_settings.ui_language == "es"
    assert remember_label.text == "Enabled"
    assert developer_label.text == "Enabled"

    settings_screen._restore_defaults()
    assert settings_screen._shell.settings_state is not None
    assert settings_screen._shell.settings_state.status == "defaults-restored"

    settings_screen._back_to_dashboard()
    assert root.current == "dashboard"


def test_settings_screen_raises_for_missing_state_or_draft_and_option_lookup_failures() -> None:
    app = cast(Any, create_kivy_app())
    root = app.build()
    settings_screen = root.get_screen("settings")

    with pytest.raises(
        ValueError,
        match=r"Settings must be loaded before rendering the settings screen\.",
    ):
        settings_screen._require_state()

    settings_screen._shell.open_settings()
    settings_screen.refresh()
    settings_screen._draft_settings = None

    with pytest.raises(
        ValueError,
        match=r"Settings draft must be initialized before editing\.",
    ):
        settings_screen._require_draft()

    options = [SettingsOptionViewModel(value="en", label="English")]

    with pytest.raises(LookupError, match="Unknown option value: es"):
        _find_option_label(options, "es")

    with pytest.raises(LookupError, match="Unknown option label: Spanish"):
        _find_option_value(options, "Spanish")


def _find_button_by_text(root_widget: object, text: str) -> Button:
    for widget in cast(Any, root_widget).walk():
        if isinstance(widget, Button) and widget.text == text:
            return widget
    msg = f"Button not found: {text}"
    raise LookupError(msg)


def _collect_label_texts(root_widget: object) -> list[str]:
    texts: list[str] = []
    for widget in cast(Any, root_widget).walk():
        if isinstance(widget, Label) and widget.text:
            texts.append(widget.text)
    return texts


def _find_spinner_by_text(root_widget: object, text: str) -> Spinner:
    for widget in cast(Any, root_widget).walk():
        if isinstance(widget, Spinner) and widget.text == text:
            return widget
    msg = f"Spinner not found: {text}"
    raise LookupError(msg)


def _find_window_inputs(root_widget: object) -> tuple[TextInput, TextInput]:
    inputs = [
        widget
        for widget in cast(Any, root_widget).walk()
        if isinstance(widget, TextInput) and widget.input_filter == "int"
    ]
    if len(inputs) < 2:
        msg = "Window inputs not found."
        raise LookupError(msg)
    return inputs[0], inputs[1]
