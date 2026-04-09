"""Base class for discoverable remote connection providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from itertools import islice

from polyglot_site_translator.domain.remote_connections.contracts import (
    DEFAULT_MATERIALIZED_REMOTE_FILE_LIMIT,
)
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import RemoteSyncFile, SyncProgressCallback


class RemoteConnectionOperationError(OSError):
    """Concrete remote operation failure with a stable structured error code."""

    def __init__(self, *, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class BaseRemoteConnectionProvider(ABC):
    """Abstract discoverable remote connection provider."""

    descriptor: RemoteConnectionTypeDescriptor

    @abstractmethod
    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Attempt a transport-level connection test."""

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
        iterator = iter(self.iter_remote_files(config, progress_callback))
        try:
            return list(islice(iterator, max_files))
        finally:
            iterator_close = getattr(iterator, "close", None)
            if callable(iterator_close):
                cast_close = iterator_close
                cast_close()

    @abstractmethod
    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Yield remote files incrementally."""

    @abstractmethod
    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        """Download a remote file and return its contents."""
