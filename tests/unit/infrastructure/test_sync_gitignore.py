"""Unit tests for deriving sync exclusions from .gitignore."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.infrastructure.sync_gitignore import (
    load_gitignore_sync_rules,
)


def test_load_gitignore_sync_rules_returns_empty_tuple_when_file_is_missing(
    tmp_path: Path,
) -> None:
    assert load_gitignore_sync_rules(tmp_path) == ()


def test_load_gitignore_sync_rules_supports_directory_and_glob_patterns(
    tmp_path: Path,
) -> None:
    (tmp_path / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.env\n!keep.me\n# comment\n",
        encoding="utf-8",
    )

    rules = load_gitignore_sync_rules(tmp_path)

    assert [rule.relative_path for rule in rules] == ["__pycache__", "*.pyc", ".env"]
    assert [rule.filter_type.value for rule in rules] == ["glob", "glob", "glob"]
