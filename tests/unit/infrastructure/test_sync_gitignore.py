"""Unit tests for deriving sync exclusions from .gitignore."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.infrastructure.sync_gitignore import (
    load_gitignore_sync_rules,
)


def test_load_gitignore_sync_rules_returns_empty_tuple_when_file_is_missing(
    tmp_path: Path,
) -> None:
    """Verify load gitignore sync rules returns empty tuple when file is missing.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    assert load_gitignore_sync_rules(tmp_path) == ()


def test_load_gitignore_sync_rules_supports_directory_and_glob_patterns(
    tmp_path: Path,
) -> None:
    """Verify load gitignore sync rules supports directory and glob patterns.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    (tmp_path / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.env\n!keep.me\n# comment\n",
        encoding="utf-8",
    )

    rules = load_gitignore_sync_rules(tmp_path)

    assert [rule.relative_path for rule in rules] == ["__pycache__", "*.pyc", ".env"]
    assert [rule.filter_type.value for rule in rules] == ["glob", "glob", "glob"]


def test_load_gitignore_sync_rules_supports_nested_directories_and_files(
    tmp_path: Path,
) -> None:
    """Verify load gitignore sync rules supports nested directories and files.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    (tmp_path / ".gitignore").write_text(
        "/cache/tmp/\nconfig/settings.local.py\n",
        encoding="utf-8",
    )

    rules = load_gitignore_sync_rules(tmp_path)

    assert [rule.relative_path for rule in rules] == ["cache/tmp", "config/settings.local.py"]
    assert [rule.filter_type.value for rule in rules] == ["directory", "file"]
