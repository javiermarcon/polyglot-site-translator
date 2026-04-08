"""Unit tests for discoverable remote connection providers."""

from __future__ import annotations

from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)


def test_remote_connection_registry_discovers_builtin_connection_types() -> None:
    registry = RemoteConnectionRegistry.discover_installed()

    assert [
        descriptor.connection_type for descriptor in registry.list_connection_descriptors()
    ] == ["ftp", "ftps_explicit", "ftps_implicit", "scp", "sftp"]


def test_remote_connection_registry_resolves_a_provider_by_type() -> None:
    registry = RemoteConnectionRegistry.discover_installed()

    provider = registry.get_provider("sftp")

    assert provider.descriptor.connection_type == "sftp"
    assert provider.descriptor.default_port == 22
