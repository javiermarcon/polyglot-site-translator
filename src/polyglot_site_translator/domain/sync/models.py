"""Typed models for synchronization workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SyncDirection(StrEnum):
    """Supported synchronization directions."""

    REMOTE_TO_LOCAL = "remote_to_local"
    LOCAL_TO_REMOTE = "local_to_remote"


@dataclass(frozen=True)
class RemoteSyncFile:
    """A file discovered in the remote workspace for synchronization."""

    remote_path: str
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class SyncSummary:
    """Structured counters produced by a sync execution."""

    files_discovered: int
    files_downloaded: int
    directories_created: int
    bytes_downloaded: int


@dataclass(frozen=True)
class SyncError:
    """Structured sync failure information."""

    code: str
    message: str
    remote_path: str | None = None
    local_path: str | None = None


@dataclass(frozen=True)
class SyncResult:
    """Structured result returned by a sync workflow."""

    direction: SyncDirection
    success: bool
    project_id: str
    connection_type: str | None
    local_path: str
    summary: SyncSummary
    error: SyncError | None
