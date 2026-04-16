"""Reusable local filesystem path picking for Kivy text fields."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy_garden.filebrowser import FileBrowser

from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    SurfaceBoxLayout,
    WrappedLabel,
)


def directory_only_listing_filter(_current_dir: str, entry_path: str) -> bool:
    """Return True for directory entries only (Kivy ``FileChooser`` filter callback).

    Used with ``filter_dirs=True`` so the listing excludes regular files while
    still allowing directory navigation and selection.
    """
    try:
        return Path(entry_path).is_dir()
    except OSError:
        return False


def initial_browse_directory(path_hint: str) -> str:
    """Return an existing directory path to seed ``FileChooser.path``.

    Walks upward from the hint when the path does not exist yet so parents such as
    the configured database directory can still open the chooser in a sensible place.
    """
    stripped = path_hint.strip()
    if stripped == "":
        return str(Path.home())
    expanded = Path(stripped).expanduser()
    if expanded.is_dir():
        return str(expanded.resolve())
    if expanded.is_file():
        parent = expanded.parent
        if str(parent) != str(expanded) and parent.is_dir():
            return str(parent.resolve())
        return str(Path.home())
    candidate = expanded.resolve()
    current = candidate
    while True:
        if current.is_dir():
            return str(current)
        parent = current.parent
        if parent == current:
            break
        current = parent
    return str(Path.home())


@dataclass(frozen=True, slots=True)
class PathFieldPicker:
    """Configuration for binding a ``TextInput`` to the local filesystem picker."""

    pick_mode: Literal["directory", "file"]
    title: str
    path_hint: Callable[[], str]
    use_basename_only: bool = False


def show_path_picker_popup(
    *,
    target: TextInput,
    mode: Literal["directory", "file"],
    title: str,
    path_hint: Callable[[], str],
    use_basename_only: bool = False,
) -> None:
    """Open :class:`~kivy_garden.filebrowser.FileBrowser` and write the result into ``target``."""
    initial = initial_browse_directory(path_hint())
    dirselect = mode == "directory"

    browser = FileBrowser(
        path=initial,
        dirselect=dirselect,
        select_string="Select",
        cancel_string="Cancel",
    )
    if dirselect:
        browser.filter_dirs = True
        browser.filters = [directory_only_listing_filter]
        Clock.schedule_once(
            lambda _dt: _disable_directory_mode_aux_fields(browser),
            0,
        )

    if mode == "file":
        browser.filters = []
        browser.filter_dirs = False

    popup = Popup(
        title=title,
        content=browser,
        size_hint=(0.94, 0.9),
        auto_dismiss=False,
    )

    def on_success(instance: FileBrowser) -> None:
        chosen = _resolve_file_browser_selection(instance, mode=mode)
        if chosen is not None:
            if use_basename_only and mode == "file":
                target.text = Path(chosen).name
            else:
                target.text = chosen
        popup.dismiss()

    def on_canceled(_instance: FileBrowser) -> None:
        popup.dismiss()

    browser.bind(on_success=on_success, on_canceled=on_canceled)
    popup.open()


def _disable_directory_mode_aux_fields(browser: FileBrowser) -> None:
    """Hide manual filename/filter edits that would break directory-only listings."""
    file_text = getattr(browser.ids, "file_text", None)
    if file_text is not None:
        file_text.disabled = True
    filt_text = getattr(browser.ids, "filt_text", None)
    if filt_text is not None:
        filt_text.disabled = True


def _resolve_file_browser_selection(
    browser: FileBrowser,
    *,
    mode: Literal["directory", "file"],
) -> str | None:
    if browser.selection:
        chosen = str(browser.selection[0])
        if mode == "directory":
            if Path(chosen).is_dir():
                return chosen
            return None
        if Path(chosen).is_file():
            return chosen
        return None
    if mode == "directory":
        return str(browser.path)
    return None


def build_path_input_row(text_input: TextInput, picker: PathFieldPicker) -> BoxLayout:
    """Horizontal row with a text input and a browse button that opens the picker."""
    row = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=44)
    text_input.size_hint_x = 0.72
    browse = AppButton(text="Browse…", primary=False, size_hint_x=0.28)
    browse.bind(
        on_release=lambda *_args: show_path_picker_popup(
            target=text_input,
            mode=picker.pick_mode,
            title=picker.title,
            path_hint=picker.path_hint,
            use_basename_only=picker.use_basename_only,
        ),
    )
    row.add_widget(text_input)
    row.add_widget(browse)
    return row


def build_labeled_path_field(
    label: str,
    text_input: TextInput,
    picker: PathFieldPicker,
) -> SurfaceBoxLayout:
    """Stack a field label, a text input, and a browse button that opens the picker."""
    card = SurfaceBoxLayout(
        orientation="vertical",
        spacing=8,
        padding=14,
        size_hint_y=None,
        background_role="card_subtle_background",
    )
    card.bind(minimum_height=card.setter("height"))
    card.add_widget(WrappedLabel(text=label, font_size=16, bold=True))
    card.add_widget(build_path_input_row(text_input, picker))
    return card
