"""Filesystem helpers for remote-to-local sync workflows."""

from __future__ import annotations

from pathlib import Path


class LocalSyncWorkspace:
    """Prepare local directories and persist downloaded file bytes."""

    def ensure_directory(self, path: Path) -> int:
        """Create a directory and return how many path segments were created."""
        if path.exists():
            if path.is_dir():
                return 0
            msg = f"Local sync target exists as a file: {path}"
            raise OSError(msg)
        missing_segments: list[Path] = []
        current_path = path
        while not current_path.exists():
            missing_segments.append(current_path)
            parent = current_path.parent
            if parent == current_path:
                break
            current_path = parent
        path.mkdir(parents=True, exist_ok=True)
        return len(missing_segments)

    def write_file(self, target_path: Path, contents: bytes) -> None:
        """Persist downloaded bytes in the local workspace."""
        target_path.write_bytes(contents)
