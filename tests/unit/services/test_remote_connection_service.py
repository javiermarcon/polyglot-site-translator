"""Unit tests for remote connection orchestration."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import pytest

from polyglot_site_translator.domain.remote_connections.models import (
    NO_REMOTE_CONNECTION_VALUE,
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryValidationError,
)
from polyglot_site_translator.domain.sync.models import (
    RemoteSyncFile,
    SyncProgressEvent,
)
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.services.remote_connections import RemoteConnectionService


@dataclass(frozen=True)
class StubRemoteConnectionProvider:
    """Test helper for StubRemoteConnectionProvider.

    Attributes:
        descriptor:
            Documented attribute exposed by this type.
        result:
            Documented attribute exposed by this type.
    """

    descriptor: RemoteConnectionTypeDescriptor
    result: RemoteConnectionTestResult

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Verify connection.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return RemoteConnectionTestResult(
            success=self.result.success,
            connection_type=config.connection_type,
            host=config.host,
            port=config.port,
            message=self.result.message,
            error_code=self.result.error_code,
        )

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
        *,
        max_files: int = 1000,
    ) -> list[RemoteSyncFile]:
        """Handle list remote files.

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
        """
        return []

    @staticmethod
    def iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Handle iter remote files.

        Args:
            config:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return iter(())

    @staticmethod
    def open_session(config: RemoteConnectionConfig) -> Any:
        """Handle open session.

        Args:
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            AssertionError:
                Raised when this callable hits the corresponding error path.
        """
        msg = f"open_session not used in this test for {config.connection_type}"
        raise AssertionError(msg)

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> bytes:
        """Handle download file.

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

        Raises:
            AssertionError:
                Raised when this callable hits the corresponding error path.
        """
        msg = f"download not used in this test for {remote_path}"
        raise AssertionError(msg)

    @staticmethod
    def ensure_remote_directory(
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> int:
        """Handle ensure remote directory.

        Args:
            config:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            AssertionError:
                Raised when this callable hits the corresponding error path.
        """
        msg = f"ensure_remote_directory not used in this test for {remote_path}"
        raise AssertionError(msg)

    @staticmethod
    def upload_file(
        config: RemoteConnectionConfig,
        remote_path: str,
        contents: bytes,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> None:
        """Handle upload file.

        Args:
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

        Raises:
            AssertionError:
                Raised when this callable hits the corresponding error path.
        """
        msg = f"upload not used in this test for {remote_path}"
        raise AssertionError(msg)


def test_remote_connection_service_lists_no_connection_and_discovered_descriptors() -> (
    None
):
    """Verify remote connection service lists no connection and discovered descriptors.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[
                StubRemoteConnectionProvider(
                    descriptor=RemoteConnectionTypeDescriptor(
                        connection_type="sftp",
                        display_name="SFTP",
                        default_port=22,
                    ),
                    result=RemoteConnectionTestResult(
                        success=True,
                        connection_type="sftp",
                        host="example.com",
                        port=22,
                        message="ok",
                        error_code=None,
                    ),
                )
            ]
        )
    )

    descriptors = service.list_supported_connection_types()

    assert [descriptor.connection_type for descriptor in descriptors] == [
        NO_REMOTE_CONNECTION_VALUE,
        "sftp",
    ]


def test_remote_connection_service_accepts_missing_remote_configuration() -> None:
    """Verify remote connection service accepts missing remote configuration.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(providers=[])
    )

    assert service.validate_optional_config(None) is None
    assert service.can_test_connection(None) is False


def test_remote_connection_service_treats_no_remote_connection_as_optional_none() -> (
    None
):
    """Verify remote connection service treats no remote connection as optional none.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.discover_installed()
    )

    assert (
        service.validate_optional_config(
            RemoteConnectionConfigInput(
                connection_type=NO_REMOTE_CONNECTION_VALUE,
                host="",
                port=0,
                username="",
                password="",
                remote_path="",
            )
        )
        is None
    )


def test_remote_connection_service_rejects_incomplete_remote_configuration() -> None:
    """Verify remote connection service rejects incomplete remote configuration.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.discover_installed()
    )

    with pytest.raises(
        SiteRegistryValidationError, match=r"Remote host must not be empty\."
    ):
        service.validate_optional_config(
            RemoteConnectionConfigInput(
                connection_type="ftp",
                host="",
                port=21,
                username="deploy",
                password="secret",
                remote_path="/public_html",
            )
        )


def test_remote_connecti_service_tests_valid_provider__27f6() -> None:
    """Verify remote connection service tests a valid provider and returns structured.

    result.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[
                StubRemoteConnectionProvider(
                    descriptor=RemoteConnectionTypeDescriptor(
                        connection_type="sftp",
                        display_name="SFTP",
                        default_port=22,
                    ),
                    result=RemoteConnectionTestResult(
                        success=True,
                        connection_type="sftp",
                        host="placeholder",
                        port=22,
                        message="Connected successfully.",
                        error_code=None,
                    ),
                )
            ]
        )
    )

    result = service.test_connection(
        RemoteConnectionConfigInput(
            connection_type="sftp",
            host="example.com",
            port=22,
            username="deploy",
            password="secret",
            remote_path="/srv/app",
        )
    )

    assert result.success is True
    assert result.connection_type == "sftp"
    assert result.host == "example.com"
    assert result.port == 22
    assert result.message == "Connected successfully."


def test_remote_connection_service_rejects_unknown_connection_types() -> None:
    """Verify remote connection service rejects unknown connection types.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(providers=[])
    )

    with pytest.raises(
        SiteRegistryValidationError,
        match=r"Unsupported remote connection type: gopher",
    ):
        service.test_connection(
            RemoteConnectionConfigInput(
                connection_type="gopher",
                host="example.com",
                port=70,
                username="deploy",
                password="secret",
                remote_path="/",
            )
        )


def test_remote_connecti_service_returns_false_invalid_c8d9() -> None:
    """Verify remote connection service returns false for invalid testability and.

    rejects none.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.discover_installed()
    )

    assert (
        service.can_test_connection(
            RemoteConnectionConfigInput(
                connection_type="ftp",
                host="",
                port=21,
                username="deploy",
                password="secret",
                remote_path="/public_html",
            )
        )
        is False
    )
    with pytest.raises(
        SiteRegistryValidationError,
        match=r"Remote connection test requires a configured remote connection\.",
    ):
        service.test_connection(
            RemoteConnectionConfigInput(
                connection_type=NO_REMOTE_CONNECTION_VALUE,
                host="",
                port=0,
                username="",
                password="",
                remote_path="",
            )
        )
