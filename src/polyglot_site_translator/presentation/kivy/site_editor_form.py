"""Shared Kivy widgets for the site/project editor (create and edit)."""

from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from polyglot_site_translator.presentation.kivy.theme import get_active_theme
from polyglot_site_translator.presentation.kivy.widgets.common import (
    SurfaceBoxLayout,
    WrappedLabel,
)
from polyglot_site_translator.presentation.kivy.widgets.password_visibility import (
    build_password_row_with_visibility_toggle,
)
from polyglot_site_translator.presentation.view_models import SettingsOptionViewModel


def build_site_editor_text_input(value: str, *, password: bool = False) -> TextInput:
    """Styled single-line ``TextInput`` for site editor fields.

    Args:
        value:
            Value supplied to this callable.
        password:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
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


def build_site_editor_spinner(*, values: list[str], current_label: str) -> Spinner:
    """Styled ``Spinner`` for framework and connection-type options.

    Args:
        values:
            Value supplied to this callable.
        current_label:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    palette = get_active_theme()
    return Spinner(
        text=current_label,
        values=values,
        size_hint_y=None,
        height=44,
        background_color=palette.card_subtle_background,
        color=palette.text_primary,
    )


def build_site_editor_field_card(label: str, field: Widget) -> SurfaceBoxLayout:
    """Label plus control, matching other site editor sections.

    Args:
        label:
            Value supplied to this callable.
        field:
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
    card.add_widget(WrappedLabel(text=label, font_size=16, bold=True))
    card.add_widget(field)
    return card


def build_remote_password_field_card(
    initial_password: str,
) -> tuple[TextInput, SurfaceBoxLayout]:
    """Remote password ``TextInput`` with show/hide toggle inside a labeled card.

    Args:
        initial_password:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    text_input = build_site_editor_text_input(initial_password, password=True)
    row = build_password_row_with_visibility_toggle(text_input)
    return text_input, build_site_editor_field_card("Remote Password", row)


def find_option_label(options: list[SettingsOptionViewModel], value: str) -> str:
    """Resolve a stored option value to its display label.

    Args:
        options:
            Value supplied to this callable.
        value:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        LookupError:
            Raised when this callable hits the corresponding error path.
    """
    for option in options:
        if option.value == value:
            return option.label
    msg = f"Unknown option value: {value}"
    raise LookupError(msg)


def find_option_value(options: list[SettingsOptionViewModel], label: str) -> str:
    """Resolve a spinner label to its persisted option value.

    Args:
        options:
            Value supplied to this callable.
        label:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        LookupError:
            Raised when this callable hits the corresponding error path.
    """
    for option in options:
        if option.label == label:
            return option.value
    msg = f"Unknown option label: {label}"
    raise LookupError(msg)
