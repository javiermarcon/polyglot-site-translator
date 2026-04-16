"""Tests for path hint helpers used by the Kivy file chooser."""

from __future__ import annotations

from pathlib import Path

import pytest

from polyglot_site_translator.presentation.kivy.widgets.path_picker import (
    directory_only_listing_filter,
    initial_browse_directory,
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


def test_directory_only_listing_filter_accepts_directory(tmp_path: Path) -> None:
    sub = tmp_path / "d"
    sub.mkdir()
    assert directory_only_listing_filter(str(tmp_path), str(sub)) is True


def test_directory_only_listing_filter_rejects_file(tmp_path: Path) -> None:
    file_path = tmp_path / "f.txt"
    file_path.write_text("x", encoding="utf-8")
    assert directory_only_listing_filter(str(tmp_path), str(file_path)) is False
