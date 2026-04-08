"""Contracts for remote connection providers."""

from __future__ import annotations

from typing import Protocol

from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import RemoteSyncFile


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

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
    ) -> list[RemoteSyncFile]:
        """Return the remote files available for synchronization."""

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
    ) -> bytes:
        """Download a remote file and return its contents."""
