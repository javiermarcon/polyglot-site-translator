"""Unit tests for shared adapter filesystem helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from polyglot_site_translator.adapters.base import BaseFrameworkAdapter
from polyglot_site_translator.adapters.common import (
    find_first_level_directory,
    find_first_level_file,
    read_text_if_present,
)
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.sync.scope import SyncFilterSpec, SyncFilterType


class _AdapterWithDefaultSyncScope(BaseFrameworkAdapter):
    framework_type = "example"
    adapter_name = "example_adapter"
    display_name = "Example"

    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        return FrameworkDetectionResult.unmatched(project_path=str(project_path))

    def get_sync_filters(self, project_path: Path) -> tuple[SyncFilterSpec, ...]:
        return (
            SyncFilterSpec(
                relative_path="locale",
                filter_type=SyncFilterType.DIRECTORY,
                description="Example catalogs.",
            ),
        )


class _AdapterWithNoCustomFilters(BaseFrameworkAdapter):
    framework_type = "empty"
    adapter_name = "empty_adapter"
    display_name = "Empty"

    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        return FrameworkDetectionResult.unmatched(project_path=str(project_path))


def test_find_first_level_file_prefers_root_and_nested_matches(tmp_path: Path) -> None:
    root_file = tmp_path / "settings.py"
    root_file.write_text("ROOT = True\n", encoding="utf-8")
    nested_dir = tmp_path / "config"
    nested_dir.mkdir()
    nested_file = nested_dir / "settings.py"
    nested_file.write_text("NESTED = True\n", encoding="utf-8")

    assert find_first_level_file(tmp_path, "settings.py") == root_file

    root_file.unlink()

    assert find_first_level_file(tmp_path, "settings.py") == nested_file


def test_find_first_level_directory_finds_root_and_nested_matches(tmp_path: Path) -> None:
    root_dir = tmp_path / "locale"
    root_dir.mkdir()
    nested_parent = tmp_path / "project"
    nested_parent.mkdir()
    nested_dir = nested_parent / "locale"
    nested_dir.mkdir()

    assert find_first_level_directory(tmp_path, "locale") == root_dir

    root_dir.rmdir()

    assert find_first_level_directory(tmp_path, "locale") == nested_dir


def test_read_text_if_present_handles_missing_binary_and_read_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert read_text_if_present(tmp_path / "missing.txt") == ""

    binary_file = tmp_path / "binary.txt"
    binary_file.write_bytes(b"\xff\xfe")

    assert read_text_if_present(binary_file) == ""

    text_file = tmp_path / "text.txt"
    text_file.write_text("hello\n", encoding="utf-8")

    def raise_os_error(*_args: object, **_kwargs: object) -> str:
        msg = "boom"
        raise OSError(msg)

    monkeypatch.setattr(Path, "read_text", raise_os_error)

    assert read_text_if_present(text_file) == ""


def test_base_framework_adapter_default_scope_delegates_to_sync_filters() -> None:
    scope = _AdapterWithDefaultSyncScope().get_sync_scope(Path("/workspace/project"))

    assert [sync_filter.relative_path for sync_filter in scope.filters] == ["locale"]
    assert scope.excludes == ()


def test_base_framework_adapter_default_filters_are_empty_when_not_overridden() -> None:
    adapter = _AdapterWithNoCustomFilters()

    assert adapter.get_sync_filters(Path("/workspace/project")) == ()
