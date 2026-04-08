"""Contracts for remote connection providers."""

from __future__ import annotations

from typing import Protocol

from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)


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
