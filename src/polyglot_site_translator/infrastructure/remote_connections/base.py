"""Base class for discoverable remote connection providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import RemoteSyncFile, SyncProgressCallback


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
    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> list[RemoteSyncFile]:
        """Return the remote files available for synchronization."""

    @abstractmethod
    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        """Download a remote file and return its contents."""
