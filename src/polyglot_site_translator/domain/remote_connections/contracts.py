"""Contracts for remote connection providers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionSessionState,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import RemoteSyncFile, SyncProgressCallback

DEFAULT_MATERIALIZED_REMOTE_FILE_LIMIT = 1000


class RemoteConnectionSession(Protocol):
    """Reusable remote session used for multi-step sync workflows."""

    @property
    def state(self) -> RemoteConnectionSessionState:
        """Return the current session lifecycle state."""

    def iter_remote_files(
        self,
        progress_callback: SyncProgressCallback | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Yield remote files incrementally using the existing session."""

    def download_file(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        """Download a remote file through the existing session."""

    def ensure_remote_directory(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> int:
        """Create a remote directory path and return how many segments were created."""

    def upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Upload file contents through the existing session."""

    def close(
        self,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Close the session and release remote resources."""


class RemoteConnectionProvider(Protocol):
    """Infrastructure provider capable of validating a connection type."""

    @property
    def descriptor(self) -> RemoteConnectionTypeDescriptor:
        """Return typed metadata for the provider."""

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Attempt a connection test and return a structured result."""

    def open_session(
        self,
        config: RemoteConnectionConfig,
    ) -> RemoteConnectionSession:
        """Open a reusable session for listing and downloading remote files."""

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
        *,
        max_files: int = DEFAULT_MATERIALIZED_REMOTE_FILE_LIMIT,
    ) -> list[RemoteSyncFile]:
        """Return a bounded materialized list of remote files."""

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Yield remote files available for synchronization incrementally."""

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        """Download a remote file and return its contents."""

    def ensure_remote_directory(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> int:
        """Create a remote directory path and return how many segments were created."""

    def upload_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        contents: bytes,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Upload file contents to the remote workspace."""
