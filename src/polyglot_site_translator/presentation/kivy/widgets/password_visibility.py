"""Password field with a visibility toggle (show/hide secret text)."""

from __future__ import annotations

from pathlib import Path

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput

from polyglot_site_translator.presentation.kivy.widgets.common import AppButton

# Material Icons (bundled TTF) codepoints — visibility / visibility_off
_MATERIAL_VISIBILITY: str = "\ue8f4"
_MATERIAL_VISIBILITY_OFF: str = "\ue8f5"


def _material_icons_font_path() -> Path:
    """Path to the packaged Material Icons font (Apache-2.0, see assets/fonts/NOTICE.txt)."""
    path = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "MaterialIcons-Regular.ttf"
    if not path.is_file():
        msg = f"Bundled Material Icons font not found: {path}"
        raise FileNotFoundError(msg)
    return path


def password_visibility_toggle_label(*, password_masked: bool) -> str:
    """Glyph text for the side button using the bundled Material Icons font.

    When the field is masked, the button shows the "visibility" (eye) glyph; when
    the secret is visible, it shows "visibility_off". Renders reliably because the
    font ships inside the package.
    """
    return _MATERIAL_VISIBILITY if password_masked else _MATERIAL_VISIBILITY_OFF


def build_password_row_with_visibility_toggle(text_input: TextInput) -> BoxLayout:
    """Arrange a password ``TextInput`` beside a toggle that masks or reveals the value.

    The toggle uses Material Icons from ``presentation/kivy/assets/fonts/``.
    """
    row = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=44)
    text_input.size_hint_x = 0.78

    font_path = _material_icons_font_path()
    toggle = AppButton(
        text=password_visibility_toggle_label(password_masked=bool(text_input.password)),
        primary=False,
        size_hint_x=0.22,
        font_name=str(font_path),
        font_size=22,
    )

    def on_toggle(_instance: object) -> None:
        text_input.password = not text_input.password
        toggle.text = password_visibility_toggle_label(password_masked=bool(text_input.password))

    toggle.bind(on_release=on_toggle)
    row.add_widget(text_input)
    row.add_widget(toggle)
    return row
