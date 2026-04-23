"""Base classes for discoverable remote connection providers and sessions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from itertools import islice

from polyglot_site_translator.domain.remote_connections.contracts import (
    DEFAULT_MATERIALIZED_REMOTE_FILE_LIMIT,
    RemoteConnectionSession,
)
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionSessionState,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import RemoteSyncFile, SyncProgressCallback


class RemoteConnectionOperationError(OSError):
    """Concrete remote operation failure with a stable structured error code."""

    def __init__(self, *, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class RemoteConnectionDependencyError(RemoteConnectionOperationError):
    """Raised when a remote provider cannot run because a dependency is missing."""


class RemoteConnectionConfigurationError(RemoteConnectionOperationError):
    """Raised when local provider configuration prevents a remote operation."""


class RemoteConnectionTransportError(RemoteConnectionOperationError):
    """Raised when opening or using the remote transport fails."""


class RemoteConnectionListingError(RemoteConnectionOperationError):
    """Raised when remote file discovery fails."""


class RemoteConnectionDownloadError(RemoteConnectionOperationError):
    """Raised when a remote file download fails."""


class RemoteConnectionDirectoryError(RemoteConnectionOperationError):
    """Raised when remote directory preparation fails."""


class RemoteConnectionUploadError(RemoteConnectionOperationError):
    """Raised when uploading a remote file fails."""


class BaseRemoteConnectionSession(ABC):
    """Reusable remote connection session with state and controlled connect retries."""

    def __init__(self, config: RemoteConnectionConfig, *, max_connect_attempts: int = 2) -> None:
        if max_connect_attempts <= 0:
            msg = "max_connect_attempts must be a positive integer."
            raise ValueError(msg)
        self._config = config
        self._max_connect_attempts = max_connect_attempts
        self._state = RemoteConnectionSessionState.CLOSED

    @property
    def state(self) -> RemoteConnectionSessionState:
        """Return the current session lifecycle state."""
        return self._state

    def iter_remote_files(
        self,
        progress_callback: SyncProgressCallback | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Yield remote files incrementally using the current session."""
        self._ensure_open(progress_callback)
        return self._iter_remote_files(progress_callback)

    def download_file(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        """Download a remote file through the current session."""
        self._ensure_open(progress_callback)
        return self._download_file(remote_path, progress_callback)

    def close(
        self,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Close the session and release remote resources."""
        if self._state is RemoteConnectionSessionState.CLOSED:
            return
        try:
            self._close(progress_callback)
        except RemoteConnectionOperationError:
            self._state = RemoteConnectionSessionState.FAILED
            raise
        finally:
            if self._state is not RemoteConnectionSessionState.FAILED:
                self._state = RemoteConnectionSessionState.CLOSED

    def ensure_remote_directory(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> int:
        """Create a remote directory path through the current session."""
        self._ensure_open(progress_callback)
        return self._ensure_remote_directory(remote_path, progress_callback)

    def upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Upload file contents through the current session."""
        self._ensure_open(progress_callback)
        self._upload_file(remote_path, contents, progress_callback)

    def _ensure_open(self, progress_callback: SyncProgressCallback | None) -> None:
        if self._state is RemoteConnectionSessionState.OPEN:
            return
        if self._state is RemoteConnectionSessionState.FAILED:
            msg = "Remote session is in a failed state."
            raise RemoteConnectionOperationError(
                error_code="remote_session_failed",
                message=msg,
            )
        last_error: RemoteConnectionOperationError | None = None
        for attempt_number in range(1, self._max_connect_attempts + 1):
            try:
                self._connect(progress_callback)
            except RemoteConnectionOperationError as error:
                last_error = error
                self._reset_after_failed_connect()
                if attempt_number >= self._max_connect_attempts or not self._should_retry_connect(
                    error
                ):
                    break
            else:
                self._state = RemoteConnectionSessionState.OPEN
                return
        self._state = RemoteConnectionSessionState.FAILED
        if last_error is not None:
            raise last_error
        msg = "Remote session could not be opened."
        raise RemoteConnectionOperationError(
            error_code="remote_session_open_failed",
            message=msg,
        )

    def _should_retry_connect(self, error: RemoteConnectionOperationError) -> bool:
        return error.error_code in {"connection_timeout", "transport_io_failed"}

    @abstractmethod
    def _connect(self, progress_callback: SyncProgressCallback | None) -> None:
        """Open the concrete transport session."""

    @abstractmethod
    def _iter_remote_files(
        self,
        progress_callback: SyncProgressCallback | None,
    ) -> Iterable[RemoteSyncFile]:
        """Yield remote files using an open concrete transport session."""

    @abstractmethod
    def _download_file(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None,
    ) -> bytes:
        """Download a remote file using an open concrete transport session."""

    @abstractmethod
    def _ensure_remote_directory(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None,
    ) -> int:
        """Create a remote directory path using an open concrete transport session."""

    @abstractmethod
    def _upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: SyncProgressCallback | None,
    ) -> None:
        """Upload file contents using an open concrete transport session."""

    @abstractmethod
    def _close(self, progress_callback: SyncProgressCallback | None) -> None:
        """Close the concrete transport session."""

    @abstractmethod
    def _reset_after_failed_connect(self) -> None:
        """Reset transport resources after a failed connect attempt."""


class BaseRemoteConnectionProvider(ABC):
    """Abstract discoverable remote connection provider."""

    descriptor: RemoteConnectionTypeDescriptor

    @abstractmethod
    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Attempt a transport-level connection test."""

    @abstractmethod
    def open_session(self, config: RemoteConnectionConfig) -> RemoteConnectionSession:
        """Create a reusable remote session for sync workflows."""

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
        *,
        max_files: int = DEFAULT_MATERIALIZED_REMOTE_FILE_LIMIT,
    ) -> list[RemoteSyncFile]:
        """Return a bounded materialized list of remote files."""
        if max_files <= 0:
            msg = "max_files must be a positive integer."
            raise ValueError(msg)
        session = self.open_session(config)
        try:
            iterator = iter(session.iter_remote_files(progress_callback))
            return list(islice(iterator, max_files))
        finally:
            session.close(progress_callback)

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Yield remote files through a short-lived reusable session."""
        session = self.open_session(config)
        try:
            yield from session.iter_remote_files(progress_callback)
        finally:
            session.close(progress_callback)

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        """Download one remote file through a short-lived reusable session."""
        session = self.open_session(config)
        try:
            return session.download_file(remote_path, progress_callback)
        finally:
            session.close(progress_callback)

    def ensure_remote_directory(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> int:
        """Create a remote directory path through a short-lived reusable session."""
        session = self.open_session(config)
        try:
            return session.ensure_remote_directory(remote_path, progress_callback)
        finally:
            session.close(progress_callback)

    def upload_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        contents: bytes,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Upload one local file through a short-lived reusable session."""
        session = self.open_session(config)
        try:
            session.upload_file(remote_path, contents, progress_callback)
        finally:
            session.close(progress_callback)
