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
    """Reusable remote session used for multi-step sync workflows.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    @property
    def state(self) -> RemoteConnectionSessionState:
        """Return the current session lifecycle state.

        Returns:
            RemoteConnectionSessionState: Structured value returned by this callable.
        """

    def iter_remote_files(
        self,
        progress_callback: SyncProgressCallback | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Yield remote files incrementally using the existing session.

        Args:
            progress_callback (SyncProgressCallback | None): Value supplied to this callable.

        Returns:
            Iterable[RemoteSyncFile]: Structured value returned by this callable.
        """

    def download_file(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        """Download a remote file through the existing session.

        Args:
            remote_path (str): Value supplied to this callable.
            progress_callback (SyncProgressCallback | None): Value supplied to this callable.

        Returns:
            bytes: Structured value returned by this callable.
        """

    def ensure_remote_directory(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> int:
        """Create a remote directory path and return how many segments were created.

        Args:
            remote_path (str): Value supplied to this callable.
            progress_callback (SyncProgressCallback | None): Value supplied to this callable.

        Returns:
            int: Structured value returned by this callable.
        """

    def upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Upload file contents through the existing session.

        Args:
            remote_path (str): Value supplied to this callable.
            contents (bytes): Value supplied to this callable.
            progress_callback (SyncProgressCallback | None): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """

    def close(
        self,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Close the session and release remote resources.

        Args:
            progress_callback (SyncProgressCallback | None): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """


class RemoteConnectionProvider(Protocol):
    """Infrastructure provider capable of validating a connection type.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    @property
    def descriptor(self) -> RemoteConnectionTypeDescriptor:
        """Return typed metadata for the provider.

        Returns:
            RemoteConnectionTypeDescriptor: Structured value returned by this callable.
        """

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Attempt a connection test and return a structured result.

        Args:
            config (RemoteConnectionConfigInput): Value supplied to this callable.

        Returns:
            RemoteConnectionTestResult: Structured value returned by this callable.
        """

    def open_session(
        self,
        config: RemoteConnectionConfig,
    ) -> RemoteConnectionSession:
        """Open a reusable session for listing and downloading remote files.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.

        Returns:
            RemoteConnectionSession: Structured value returned by this callable.
        """

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
        *,
        max_files: int = DEFAULT_MATERIALIZED_REMOTE_FILE_LIMIT,
    ) -> list[RemoteSyncFile]:
        """Return a bounded materialized list of remote files.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.
            progress_callback (SyncProgressCallback | None): Value supplied to this callable.
            max_files (int): Value supplied to this callable.

        Returns:
            list[RemoteSyncFile]: Structured value returned by this callable.
        """

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Yield remote files available for synchronization incrementally.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.
            progress_callback (SyncProgressCallback | None): Value supplied to this callable.

        Returns:
            Iterable[RemoteSyncFile]: Structured value returned by this callable.
        """

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        """Download a remote file and return its contents.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.
            remote_path (str): Value supplied to this callable.
            progress_callback (SyncProgressCallback | None): Value supplied to this callable.

        Returns:
            bytes: Structured value returned by this callable.
        """

    def ensure_remote_directory(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> int:
        """Create a remote directory path and return how many segments were created.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.
            remote_path (str): Value supplied to this callable.
            progress_callback (SyncProgressCallback | None): Value supplied to this callable.

        Returns:
            int: Structured value returned by this callable.
        """

    def upload_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        contents: bytes,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Upload file contents to the remote workspace.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.
            remote_path (str): Value supplied to this callable.
            contents (bytes): Value supplied to this callable.
            progress_callback (SyncProgressCallback | None): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
