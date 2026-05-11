"""Typed models for synchronization workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class SyncDirection(StrEnum):
    """Supported synchronization directions.

    Attributes:
        REMOTE_TO_LOCAL: Documented attribute exposed by this type.
        LOCAL_TO_REMOTE: Documented attribute exposed by this type.
    """

    REMOTE_TO_LOCAL = "remote_to_local"
    LOCAL_TO_REMOTE = "local_to_remote"


class SyncProgressStage(StrEnum):
    """Supported progress stages reported during sync execution.

    Attributes:
        PREPARING_LOCAL: Documented attribute exposed by this type.
        PREPARING_REMOTE: Documented attribute exposed by this type.
        LISTING_LOCAL: Documented attribute exposed by this type.
        LISTING_REMOTE: Documented attribute exposed by this type.
        DOWNLOADING_FILE: Documented attribute exposed by this type.
        UPLOADING_FILE: Documented attribute exposed by this type.
        WRITING_LOCAL_FILE: Documented attribute exposed by this type.
        COMPLETED: Documented attribute exposed by this type.
        FAILED: Documented attribute exposed by this type.
    """

    PREPARING_LOCAL = "preparing_local"
    PREPARING_REMOTE = "preparing_remote"
    LISTING_LOCAL = "listing_local"
    LISTING_REMOTE = "listing_remote"
    DOWNLOADING_FILE = "downloading_file"
    UPLOADING_FILE = "uploading_file"
    WRITING_LOCAL_FILE = "writing_local_file"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class RemoteSyncFile:
    """A file discovered in the remote workspace for synchronization.

    Attributes:
        remote_path (str): Documented attribute exposed by this type.
        relative_path (str): Documented attribute exposed by this type.
        size_bytes (int): Documented attribute exposed by this type.
    """

    remote_path: str
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class LocalSyncFile:
    """A file discovered in the local workspace for synchronization.

    Attributes:
        local_path (Path): Documented attribute exposed by this type.
        relative_path (str): Documented attribute exposed by this type.
        size_bytes (int): Documented attribute exposed by this type.
    """

    local_path: Path
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class SyncProgressEvent:
    """Structured progress event emitted during a sync workflow.

    Attributes:
        stage (SyncProgressStage): Documented attribute exposed by this type.
        message (str): Documented attribute exposed by this type.
        command_text (str | None): Documented attribute exposed by this type.
        files_discovered (int | None): Documented attribute exposed by this type.
        files_downloaded (int | None): Documented attribute exposed by this type.
        files_uploaded (int | None): Documented attribute exposed by this type.
        total_files (int | None): Documented attribute exposed by this type.
        bytes_downloaded (int | None): Documented attribute exposed by this type.
        bytes_uploaded (int | None): Documented attribute exposed by this type.
    """

    stage: SyncProgressStage
    message: str
    command_text: str | None = None
    files_discovered: int | None = None
    files_downloaded: int | None = None
    files_uploaded: int | None = None
    total_files: int | None = None
    bytes_downloaded: int | None = None
    bytes_uploaded: int | None = None


@dataclass(frozen=True)
class SyncSummary:
    """Structured counters produced by a sync execution.

    Attributes:
        files_discovered (int): Documented attribute exposed by this type.
        files_downloaded (int): Documented attribute exposed by this type.
        directories_created (int): Documented attribute exposed by this type.
        bytes_downloaded (int): Documented attribute exposed by this type.
        files_uploaded (int): Documented attribute exposed by this type.
        bytes_uploaded (int): Documented attribute exposed by this type.
    """

    files_discovered: int
    files_downloaded: int
    directories_created: int
    bytes_downloaded: int
    files_uploaded: int = 0
    bytes_uploaded: int = 0


@dataclass(frozen=True)
class SyncError:
    """Structured sync failure information.

    Attributes:
        code (str): Documented attribute exposed by this type.
        message (str): Documented attribute exposed by this type.
        remote_path (str | None): Documented attribute exposed by this type.
        local_path (str | None): Documented attribute exposed by this type.
    """

    code: str
    message: str
    remote_path: str | None = None
    local_path: str | None = None


@dataclass(frozen=True)
class SyncResult:
    """Structured result returned by a sync workflow.

    Attributes:
        direction (SyncDirection): Documented attribute exposed by this type.
        success (bool): Documented attribute exposed by this type.
        project_id (str): Documented attribute exposed by this type.
        connection_type (str | None): Documented attribute exposed by this type.
        local_path (str): Documented attribute exposed by this type.
        summary (SyncSummary): Documented attribute exposed by this type.
        error (SyncError | None): Documented attribute exposed by this type.
    """

    direction: SyncDirection
    success: bool
    project_id: str
    connection_type: str | None
    local_path: str
    summary: SyncSummary
    error: SyncError | None


SyncProgressCallback = Callable[[SyncProgressEvent], None]
