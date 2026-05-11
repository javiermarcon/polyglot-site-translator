"""Filesystem helpers for sync workflows touching the local workspace."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from polyglot_site_translator.domain.sync.models import LocalSyncFile


class LocalSyncWorkspace:
    """Prepare, inspect, and write the local workspace for sync workflows.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def ensure_directory(self, path: Path) -> int:
        """Create a directory and return how many path segments were created.

        Args:
            self:
                Value supplied to this callable.
            path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
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
        """Persist downloaded bytes in the local workspace.

        Args:
            self:
                Value supplied to this callable.
            target_path:
                Value supplied to this callable.
            contents:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        target_path.write_bytes(contents)

    @staticmethod
    def read_file(source_path: Path) -> bytes:
        """Read a local file before uploading it to the remote workspace.

        Args:
            source_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return source_path.read_bytes()

    def iter_local_files(self, local_root: Path) -> Iterable[LocalSyncFile]:
        """Yield regular files under the local workspace in a stable order.

        Args:
            self:
                Value supplied to this callable.
            local_root:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        normalized_root = local_root.resolve()
        if not normalized_root.exists():
            return iter(())
        if not normalized_root.is_dir():
            msg = f"Local sync root is not a directory: {local_root}"
            raise OSError(msg)
        return self._iter_local_files(normalized_root)

    @staticmethod
    def _iter_local_files(local_root: Path) -> Iterable[LocalSyncFile]:
        """Iterate through local files.

        Args:
            local_root:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        for path in sorted(local_root.rglob("*")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(local_root).as_posix()
            yield LocalSyncFile(
                local_path=path,
                relative_path=relative_path,
                size_bytes=path.stat().st_size,
            )
