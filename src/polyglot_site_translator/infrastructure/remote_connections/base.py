"""Base class for discoverable remote connection providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)


class BaseRemoteConnectionProvider(ABC):
    """Abstract discoverable remote connection provider."""

    descriptor: RemoteConnectionTypeDescriptor

    @abstractmethod
    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Attempt a transport-level connection test."""
