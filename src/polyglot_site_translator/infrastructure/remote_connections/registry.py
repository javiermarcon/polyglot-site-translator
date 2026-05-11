"""Registry for remote connection providers."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import inspect
import pkgutil

from polyglot_site_translator.domain.remote_connections.contracts import (
    RemoteConnectionProvider,
)
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.infrastructure.remote_connections import (
    __path__ as remote_connections_package_path,
)
from polyglot_site_translator.infrastructure.remote_connections.base import (
    BaseRemoteConnectionProvider,
)


@dataclass(frozen=True)
class RemoteConnectionRegistry:
    """Resolve remote connection providers by discoverable connection type.

    Attributes:
        providers (list[RemoteConnectionProvider]): Documented attribute exposed by this type.
    """

    providers: list[RemoteConnectionProvider]

    @classmethod
    def default_registry(
        cls,
        *,
        providers: list[RemoteConnectionProvider],
    ) -> RemoteConnectionRegistry:
        """Build a registry from an explicit provider list.

        Args:
            providers (list[RemoteConnectionProvider]): Value supplied to this callable.

        Returns:
            RemoteConnectionRegistry: Structured value returned by this callable.
        """
        return cls(providers=list(providers))

    @classmethod
    def discover_installed(cls) -> RemoteConnectionRegistry:
        """Discover installed remote connection providers dynamically.

        Returns:
            RemoteConnectionRegistry: Structured value returned by this callable.
        """
        providers: list[RemoteConnectionProvider] = []
        for module_info in pkgutil.iter_modules(remote_connections_package_path):
            if module_info.name in {"base", "registry"}:
                continue
            module = importlib.import_module(
                f"polyglot_site_translator.infrastructure.remote_connections.{module_info.name}"
            )
            for _, provider_class in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(provider_class, BaseRemoteConnectionProvider)
                    and provider_class is not BaseRemoteConnectionProvider
                    and provider_class.__module__ == module.__name__
                ):
                    providers.append(provider_class())
        providers.sort(key=lambda provider: provider.descriptor.connection_type)
        return cls(providers=providers)

    def list_connection_descriptors(self) -> list[RemoteConnectionTypeDescriptor]:
        """Return connection descriptors preserving registration order.

        Returns:
            list[RemoteConnectionTypeDescriptor]: Structured value returned by this callable.
        """
        return [provider.descriptor for provider in self.providers]

    def get_provider(self, connection_type: str) -> RemoteConnectionProvider:
        """Return a provider for the given connection type.

        Args:
            connection_type (str): Value supplied to this callable.

        Returns:
            RemoteConnectionProvider: Structured value returned by this callable.

        Raises:
            LookupError: Raised when this callable hits the corresponding error path.
        """
        for provider in self.providers:
            if provider.descriptor.connection_type == connection_type:
                return provider
        msg = f"Unsupported remote connection type: {connection_type}"
        raise LookupError(msg)
