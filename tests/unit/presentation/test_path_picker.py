"""Tests for path hint helpers used by the Kivy file chooser."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar, cast

from kivy.uix.textinput import TextInput
import pytest

from polyglot_site_translator.presentation.kivy.widgets.path_picker import (
    PathFieldPicker,
    _disable_directory_mode_aux_fields,
    _resolve_file_browser_selection,
    build_labeled_path_field,
    build_path_input_row,
    directory_only_listing_filter,
    initial_browse_directory,
    show_path_picker_popup,
)


def test_initial_browse_directory_empty_uses_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = str(tmp_path)
    monkeypatch.setenv("HOME", home)
    assert initial_browse_directory("") == home


def test_initial_browse_directory_existing_dir(tmp_path: Path) -> None:
    assert initial_browse_directory(str(tmp_path)) == str(tmp_path.resolve())


def test_initial_browse_directory_file_returns_parent(tmp_path: Path) -> None:
    file_path = tmp_path / "data.sqlite"
    file_path.write_text("x", encoding="utf-8")
    assert initial_browse_directory(str(file_path)) == str(tmp_path.resolve())


def test_initial_browse_directory_walks_up_to_existing_parent(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "c"
    assert initial_browse_directory(str(nested)) == str(tmp_path.resolve())


def test_initial_browse_whitespace_only_uses_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = str(tmp_path)
    monkeypatch.setenv("HOME", home)
    assert initial_browse_directory("   ") == home


def test_initial_browse_directory_expands_user(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = str(tmp_path)
    monkeypatch.setenv("HOME", home)
    assert initial_browse_directory("~") == home


def test_initial_browse_directory_joined_missing_path(tmp_path: Path) -> None:
    base = tmp_path / "proj"
    base.mkdir()
    missing = base / "missing" / "nested"
    assert initial_browse_directory(str(missing)) == str(base.resolve())


def test_initial_browse_directory_handles_file_without_directory_parent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = str(tmp_path)
    monkeypatch.setenv("HOME", home)

    original_is_file = Path.is_file
    original_is_dir = Path.is_dir

    def _fake_is_file(self: Path) -> bool:
        return str(self) == "/virtual/file.txt" or original_is_file(self)

    def _fake_is_dir(self: Path) -> bool:
        if str(self) in {"/virtual", "/virtual/file.txt"}:
            return False
        return original_is_dir(self)

    monkeypatch.setattr(Path, "is_file", _fake_is_file)
    monkeypatch.setattr(Path, "is_dir", _fake_is_dir)

    assert initial_browse_directory("/virtual/file.txt") == home


def test_initial_browse_directory_falls_back_to_home_when_parent_chain_stops(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = str(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    class _FakeResolvedPath:
        parent: _FakeResolvedPath

        def __init__(self) -> None:
            self.parent = self

        def is_dir(self) -> bool:
            return False

    fake_resolved = _FakeResolvedPath()

    class _FakeExpandedPath:
        def is_dir(self) -> bool:
            return False

        def is_file(self) -> bool:
            return False

        def resolve(self) -> _FakeResolvedPath:
            return fake_resolved

    monkeypatch.setattr(Path, "expanduser", lambda self: _FakeExpandedPath())

    assert initial_browse_directory("/unresolvable") == home


def test_directory_only_listing_filter_accepts_directory(tmp_path: Path) -> None:
    sub = tmp_path / "d"
    sub.mkdir()
    assert directory_only_listing_filter(str(tmp_path), str(sub)) is True


def test_directory_only_listing_filter_rejects_file(tmp_path: Path) -> None:
    file_path = tmp_path / "f.txt"
    file_path.write_text("x", encoding="utf-8")
    assert directory_only_listing_filter(str(tmp_path), str(file_path)) is False


def test_directory_only_listing_filter_handles_os_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_os_error(self: Path) -> bool:
        del self
        msg = "broken filesystem"
        raise OSError(msg)

    monkeypatch.setattr(Path, "is_dir", _raise_os_error)

    assert directory_only_listing_filter("/tmp", "/broken") is False


def test_disable_directory_mode_aux_fields_handles_missing_and_present_widgets() -> None:
    file_text = SimpleNamespace(disabled=False)
    filt_text = SimpleNamespace(disabled=False)
    browser = SimpleNamespace(ids=SimpleNamespace(file_text=file_text, filt_text=filt_text))

    _disable_directory_mode_aux_fields(browser)

    assert file_text.disabled is True
    assert filt_text.disabled is True

    browser_without_fields = SimpleNamespace(ids=SimpleNamespace())
    _disable_directory_mode_aux_fields(browser_without_fields)


def test_resolve_file_browser_selection_covers_directory_and_file_modes(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "dir"
    directory.mkdir()
    file_path = tmp_path / "data.txt"
    file_path.write_text("ok", encoding="utf-8")

    directory_browser = SimpleNamespace(selection=[str(directory)], path=str(tmp_path))
    assert _resolve_file_browser_selection(directory_browser, mode="directory") == str(directory)

    file_browser = SimpleNamespace(selection=[str(file_path)], path=str(tmp_path))
    assert _resolve_file_browser_selection(file_browser, mode="file") == str(file_path)

    wrong_directory_browser = SimpleNamespace(selection=[str(file_path)], path=str(tmp_path))
    assert _resolve_file_browser_selection(wrong_directory_browser, mode="directory") is None

    wrong_file_browser = SimpleNamespace(selection=[str(directory)], path=str(tmp_path))
    assert _resolve_file_browser_selection(wrong_file_browser, mode="file") is None

    fallback_directory_browser = SimpleNamespace(selection=[], path=str(tmp_path))
    assert _resolve_file_browser_selection(fallback_directory_browser, mode="directory") == str(
        tmp_path
    )

    fallback_file_browser = SimpleNamespace(selection=[], path=str(tmp_path))
    assert _resolve_file_browser_selection(fallback_file_browser, mode="file") is None


class _FakeBrowser:
    def __init__(
        self,
        *,
        path: str,
        dirselect: bool,
        select_string: str,
        cancel_string: str,
    ) -> None:
        self.path = path
        self.dirselect = dirselect
        self.select_string = select_string
        self.cancel_string = cancel_string
        self.filter_dirs = False
        self.filters: list[object] = ["initial"]
        self.selection: list[str] = []
        self.ids = SimpleNamespace(
            file_text=SimpleNamespace(disabled=False),
            filt_text=SimpleNamespace(disabled=False),
        )
        self._bound: dict[str, Any] = {}

    def bind(self, **kwargs: Any) -> None:
        self._bound.update(kwargs)


class _FakePopup:
    instances: ClassVar[list[_FakePopup]] = []

    def __init__(
        self,
        *,
        title: str,
        content: object,
        size_hint: tuple[float, float],
        auto_dismiss: bool,
    ) -> None:
        self.title = title
        self.content = content
        self.size_hint = size_hint
        self.auto_dismiss = auto_dismiss
        self.opened = False
        self.dismissed = False
        self.__class__.instances.append(self)

    def open(self) -> None:
        self.opened = True

    def dismiss(self) -> None:
        self.dismissed = True


def test_show_path_picker_popup_directory_mode_updates_target_and_disables_aux_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _FakePopup.instances.clear()
    scheduled_callbacks: list[Any] = []

    def _schedule_once(callback: Any, _timeout: float = 0.0) -> None:
        scheduled_callbacks.append(callback)

    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.path_picker.FileBrowser",
        _FakeBrowser,
    )
    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.path_picker.Popup",
        _FakePopup,
    )
    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.path_picker.Clock.schedule_once",
        _schedule_once,
    )

    selected_directory = tmp_path / "selected-dir"
    selected_directory.mkdir()

    directory_target = TextInput(text="")
    show_path_picker_popup(
        target=directory_target,
        mode="directory",
        title="Choose Directory",
        path_hint=lambda: str(tmp_path),
    )
    directory_popup = _FakePopup.instances[-1]
    directory_browser = directory_popup.content
    assert isinstance(directory_browser, _FakeBrowser)
    assert directory_browser.filter_dirs is True
    assert directory_browser.filters == [directory_only_listing_filter]
    assert scheduled_callbacks
    scheduled_callbacks[-1](0)
    assert directory_browser.ids.file_text.disabled is True
    assert directory_browser.ids.filt_text.disabled is True
    directory_browser.selection = [str(selected_directory)]
    directory_browser._bound["on_success"](directory_browser)
    assert directory_target.text == str(selected_directory)
    assert directory_popup.dismissed is True


def test_show_path_picker_popup_file_mode_updates_target_and_handles_empty_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _FakePopup.instances.clear()
    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.path_picker.FileBrowser",
        _FakeBrowser,
    )
    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.path_picker.Popup",
        _FakePopup,
    )

    selected_file = tmp_path / "chosen.txt"
    selected_file.write_text("ok", encoding="utf-8")

    file_target = TextInput(text="")
    show_path_picker_popup(
        target=file_target,
        mode="file",
        title="Choose File",
        path_hint=lambda: str(tmp_path),
        use_basename_only=True,
    )
    file_popup = _FakePopup.instances[-1]
    file_browser = file_popup.content
    assert isinstance(file_browser, _FakeBrowser)
    assert file_browser.filter_dirs is False
    assert file_browser.filters == []
    file_browser.selection = [str(selected_file)]
    file_browser._bound["on_success"](file_browser)
    assert file_target.text == selected_file.name
    assert file_popup.dismissed is True

    unchanged_target = TextInput(text="keep")
    show_path_picker_popup(
        target=unchanged_target,
        mode="file",
        title="No Selection",
        path_hint=lambda: str(tmp_path),
    )
    unchanged_popup = _FakePopup.instances[-1]
    unchanged_browser = cast(_FakeBrowser, unchanged_popup.content)
    unchanged_browser.selection = []
    unchanged_browser._bound["on_success"](unchanged_browser)
    assert unchanged_target.text == "keep"
    assert unchanged_popup.dismissed is True


def test_show_path_picker_popup_cancel_keeps_existing_value(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _FakePopup.instances.clear()
    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.path_picker.FileBrowser",
        _FakeBrowser,
    )
    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.path_picker.Popup",
        _FakePopup,
    )

    canceled_target = TextInput(text="unchanged")
    show_path_picker_popup(
        target=canceled_target,
        mode="file",
        title="Cancel File",
        path_hint=lambda: str(tmp_path),
    )
    canceled_popup = _FakePopup.instances[-1]
    canceled_browser = cast(_FakeBrowser, canceled_popup.content)
    canceled_browser._bound["on_canceled"](canceled_browser)
    assert canceled_target.text == "unchanged"
    assert canceled_popup.dismissed is True


def test_build_path_input_row_and_labeled_field_bind_browse_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_calls: list[dict[str, object]] = []

    def _fake_show_path_picker_popup(**kwargs: object) -> None:
        captured_calls.append(kwargs)

    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.path_picker.show_path_picker_popup",
        _fake_show_path_picker_popup,
    )

    field = TextInput(text="")
    picker = PathFieldPicker(
        pick_mode="file",
        title="Pick a file",
        path_hint=lambda: "/tmp",
        use_basename_only=True,
    )

    row = build_path_input_row(field, picker)
    browse_button = row.children[0]
    browse_button.dispatch("on_release")

    assert captured_calls
    assert captured_calls[0]["target"] is field
    assert captured_calls[0]["mode"] == "file"
    assert cast(Any, field).size_hint_x == 0.72

    labeled_field = TextInput(text="")
    card = build_labeled_path_field("Database", labeled_field, picker)
    label_texts = [widget.text for widget in card.walk(restrict=True) if hasattr(widget, "text")]
    assert "Database" in label_texts
