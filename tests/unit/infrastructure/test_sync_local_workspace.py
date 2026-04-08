"""Unit tests for local sync workspace filesystem helpers."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from polyglot_site_translator.infrastructure.sync_local import LocalSyncWorkspace


class _RootLikePath:
    def __init__(self) -> None:
        self.parent = self
        self.mkdir_calls: list[tuple[bool, bool]] = []

    def exists(self) -> bool:
        return False

    def is_dir(self) -> bool:
        return False

    def mkdir(self, *, parents: bool, exist_ok: bool) -> None:
        self.mkdir_calls.append((parents, exist_ok))


def test_local_sync_workspace_creates_missing_directories(tmp_path: Path) -> None:
    workspace = LocalSyncWorkspace()

    created_segments = workspace.ensure_directory(tmp_path / "workspace" / "site" / "locale")

    assert created_segments == 3
    assert (tmp_path / "workspace" / "site" / "locale").is_dir()


def test_local_sync_workspace_returns_zero_when_directory_already_exists(tmp_path: Path) -> None:
    workspace = LocalSyncWorkspace()
    existing_directory = tmp_path / "workspace"
    existing_directory.mkdir()

    created_segments = workspace.ensure_directory(existing_directory)

    assert created_segments == 0


def test_local_sync_workspace_rejects_file_paths(tmp_path: Path) -> None:
    workspace = LocalSyncWorkspace()
    occupied_path = tmp_path / "occupied"
    occupied_path.write_text("occupied", encoding="utf-8")

    with pytest.raises(OSError, match="Local sync target exists as a file"):
        workspace.ensure_directory(occupied_path)


def test_local_sync_workspace_writes_downloaded_file_bytes(tmp_path: Path) -> None:
    workspace = LocalSyncWorkspace()
    target_file = tmp_path / "workspace" / "site" / "locale" / "es.po"
    workspace.ensure_directory(target_file.parent)

    workspace.write_file(target_file, b'msgid "hello"\n')

    assert target_file.read_bytes() == b'msgid "hello"\n'


def test_local_sync_workspace_stops_counting_at_self_parent_roots() -> None:
    workspace = LocalSyncWorkspace()
    root_path = _RootLikePath()

    created_segments = workspace.ensure_directory(cast(Path, root_path))

    assert created_segments == 1
    assert root_path.mkdir_calls == [(True, True)]
