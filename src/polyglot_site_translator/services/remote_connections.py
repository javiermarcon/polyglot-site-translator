"""Application service for remote connection catalogs, validation, and tests."""

from __future__ import annotations

from polyglot_site_translator.domain.remote_connections.contracts import (
    RemoteConnectionProvider,
)
from polyglot_site_translator.domain.remote_connections.models import (
    NO_REMOTE_CONNECTION_VALUE,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
    no_remote_connection_descriptor,
)
from polyglot_site_translator.domain.site_registry.errors import SiteRegistryValidationError
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)


class RemoteConnectionService:
    """Orchestrate remote connection validation and provider dispatch."""

    def __init__(self, *, registry: RemoteConnectionRegistry) -> None:
        self._registry = registry

    def list_supported_connection_types(self) -> list[RemoteConnectionTypeDescriptor]:
        """Return the optional no-connection option plus discovered providers."""
        return [
            no_remote_connection_descriptor(),
            *self._registry.list_connection_descriptors(),
        ]

    def validate_optional_config(
        self,
        config: RemoteConnectionConfigInput | None,
    ) -> RemoteConnectionConfigInput | None:
        """Validate a remote config only when remote access is actually configured."""
        if config is None:
            return None
        connection_type = _require_text(config.connection_type, "Remote connection type")
        if connection_type == NO_REMOTE_CONNECTION_VALUE:
            return None
        self._require_supported_type(connection_type)
        return RemoteConnectionConfigInput(
            connection_type=connection_type,
            host=_require_text(config.host, "Remote host"),
            port=_require_port(config.port),
            username=_require_text(config.username, "Remote username"),
            password=_require_text(config.password, "Remote password"),
            remote_path=_require_text(config.remote_path, "Remote path"),
            flags=config.flags,
        )

    def can_test_connection(self, config: RemoteConnectionConfigInput | None) -> bool:
        """Return whether a remote config is complete enough to run a test."""
        try:
            validated_config = self.validate_optional_config(config)
        except SiteRegistryValidationError:
            return False
        return validated_config is not None

    def test_connection(self, config: RemoteConnectionConfigInput) -> RemoteConnectionTestResult:
        """Validate and test a remote connection using the matching provider."""
        validated_config = self.validate_optional_config(config)
        if validated_config is None:
            msg = "Remote connection test requires a configured remote connection."
            raise SiteRegistryValidationError(msg)
        provider = self._require_supported_type(validated_config.connection_type)
        return provider.test_connection(validated_config)

    def _require_supported_type(
        self,
        connection_type: str,
    ) -> RemoteConnectionProvider:
        try:
            return self._registry.get_provider(connection_type)
        except LookupError as error:
            raise SiteRegistryValidationError(str(error)) from error


def _require_text(value: str, label: str) -> str:
    normalized_value = value.strip()
    if normalized_value:
        return normalized_value
    msg = f"{label} must not be empty."
    raise SiteRegistryValidationError(msg)


def _require_port(port: int) -> int:
    if port > 0:
        return port
    msg = "Remote port must be a positive integer."
    raise SiteRegistryValidationError(msg)
