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
from polyglot_site_translator.domain.sync.models import (
    RemoteSyncFile,
    SyncProgressCallback,
)


class RemoteConnectionOperationError(OSError):
    """Concrete remote operation failure with a stable structured error code.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, *, error_code: str, message: str) -> None:
        """Capture the stable provider-facing error code alongside the transport.

        message.

        Args:
            self:
                Value supplied to this callable.
            error_code:
                Value supplied to this callable.
            message:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(message)
        self.error_code = error_code


class RemoteConnectionDependencyError(RemoteConnectionOperationError):
    """Raised when a remote provider cannot run because a dependency is missing.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class RemoteConnectionConfigurationError(RemoteConnectionOperationError):
    """Raised when local provider configuration prevents a remote operation.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class RemoteConnectionTransportError(RemoteConnectionOperationError):
    """Raised when opening or using the remote transport fails.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class RemoteConnectionListingError(RemoteConnectionOperationError):
    """Raised when remote file discovery fails.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class RemoteConnectionDownloadError(RemoteConnectionOperationError):
    """Raised when a remote file download fails.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class RemoteConnectionDirectoryError(RemoteConnectionOperationError):
    """Raised when remote directory preparation fails.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class RemoteConnectionUploadError(RemoteConnectionOperationError):
    """Raised when uploading a remote file fails.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class BaseRemoteConnectionSession(ABC):
    """Reusable remote connection session with state and controlled connect retries.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self, config: RemoteConnectionConfig, *, max_connect_attempts: int = 2
    ) -> None:
        """Store remote config and initialize lifecycle state for a reusable session.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            max_connect_attempts:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ValueError:
                Raised when this callable hits the corresponding error path.
        """
        if max_connect_attempts <= 0:
            msg = "max_connect_attempts must be a positive integer."
            raise ValueError(msg)
        self._config = config
        self._max_connect_attempts = max_connect_attempts
        self._state = RemoteConnectionSessionState.CLOSED

    @property
    def state(self) -> RemoteConnectionSessionState:
        """Return the current session lifecycle state.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self._state

    def iter_remote_files(
        self,
        progress_callback: SyncProgressCallback | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Yield remote files incrementally using the current session.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._ensure_open(progress_callback)
        return self._iter_remote_files(progress_callback)

    def download_file(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        """Download a remote file through the current session.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._ensure_open(progress_callback)
        return self._download_file(remote_path, progress_callback)

    def close(
        self,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Close the session and release remote resources.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
        """Create a remote directory path through the current session.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._ensure_open(progress_callback)
        return self._ensure_remote_directory(remote_path, progress_callback)

    def upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: SyncProgressCallback | None = None,
    ) -> None:
        """Upload file contents through the current session.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            contents:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._ensure_open(progress_callback)
        self._upload_file(remote_path, contents, progress_callback)

    def _ensure_open(self, progress_callback: SyncProgressCallback | None) -> None:
        """Handle ensure open.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
        """
        if self._state is RemoteConnectionSessionState.OPEN:
            return
        if self._state is RemoteConnectionSessionState.FAILED:
            msg = "Remote session is in a failed state."
            raise RemoteConnectionOperationError(
                error_code="remote_session_failed",
                message=msg,
            )
        attempt_number = 1
        while True:
            try:
                self._connect(progress_callback)
            except RemoteConnectionOperationError as error:
                self._reset_after_failed_connect()
                if (
                    attempt_number < self._max_connect_attempts
                    and self._should_retry_connect(error)
                ):
                    attempt_number += 1
                    continue
                self._state = RemoteConnectionSessionState.FAILED
                raise
            else:
                self._state = RemoteConnectionSessionState.OPEN
                return

    @staticmethod
    def _should_retry_connect(error: RemoteConnectionOperationError) -> bool:
        """Handle should retry connect.

        Args:
            error:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return error.error_code in {"connection_timeout", "transport_io_failed"}

    @abstractmethod
    def _connect(self, progress_callback: SyncProgressCallback | None) -> None:
        """Open the concrete transport session.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    @abstractmethod
    def _iter_remote_files(
        self,
        progress_callback: SyncProgressCallback | None,
    ) -> Iterable[RemoteSyncFile]:
        """Yield remote files using an open concrete transport session.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    @abstractmethod
    def _download_file(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None,
    ) -> bytes:
        """Download a remote file using an open concrete transport session.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    @abstractmethod
    def _ensure_remote_directory(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None,
    ) -> int:
        """Create a remote directory path using an open concrete transport session.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    @abstractmethod
    def _upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: SyncProgressCallback | None,
    ) -> None:
        """Upload file contents using an open concrete transport session.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            contents:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    @abstractmethod
    def _close(self, progress_callback: SyncProgressCallback | None) -> None:
        """Close the concrete transport session.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    @abstractmethod
    def _reset_after_failed_connect(self) -> None:
        """Reset transport resources after a failed connect attempt.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """


class BaseRemoteConnectionProvider(ABC):
    """Abstract discoverable remote connection provider.

    Attributes:
        descriptor:
            Documented attribute exposed by this type.
    """

    descriptor: RemoteConnectionTypeDescriptor

    @abstractmethod
    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Attempt a transport-level connection test.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    @abstractmethod
    def open_session(self, config: RemoteConnectionConfig) -> RemoteConnectionSession:
        """Create a reusable remote session for sync workflows.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
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
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.
            max_files:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ValueError:
                Raised when this callable hits the corresponding error path.
        """
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
        """Yield remote files through a short-lived reusable session.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
        """Download one remote file through a short-lived reusable session.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
        """Create a remote directory path through a short-lived reusable session.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
        """Upload one local file through a short-lived reusable session.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            contents:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        session = self.open_session(config)
        try:
            session.upload_file(remote_path, contents, progress_callback)
        finally:
            session.close(progress_callback)
