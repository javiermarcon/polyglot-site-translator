"""Typed models for synchronization workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class SyncDirection(StrEnum):
    """Supported synchronization directions."""

    REMOTE_TO_LOCAL = "remote_to_local"
    LOCAL_TO_REMOTE = "local_to_remote"


class SyncProgressStage(StrEnum):
    """Supported progress stages reported during sync execution."""

    PREPARING_LOCAL = "preparing_local"
    LISTING_REMOTE = "listing_remote"
    DOWNLOADING_FILE = "downloading_file"
    WRITING_LOCAL_FILE = "writing_local_file"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class RemoteSyncFile:
    """A file discovered in the remote workspace for synchronization."""

    remote_path: str
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class SyncProgressEvent:
    """Structured progress event emitted during a sync workflow."""

    stage: SyncProgressStage
    message: str
    command_text: str | None = None
    files_discovered: int | None = None
    files_downloaded: int | None = None
    total_files: int | None = None
    bytes_downloaded: int | None = None


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


SyncProgressCallback = Callable[[SyncProgressEvent], None]
