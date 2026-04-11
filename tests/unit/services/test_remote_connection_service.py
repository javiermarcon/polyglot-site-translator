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
from polyglot_site_translator.domain.site_registry.errors import SiteRegistryValidationError
from polyglot_site_translator.domain.sync.models import RemoteSyncFile, SyncProgressEvent
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.services.remote_connections import RemoteConnectionService


@dataclass(frozen=True)
class StubRemoteConnectionProvider:
    """Small provider stub for remote connection service tests."""

    descriptor: RemoteConnectionTypeDescriptor
    result: RemoteConnectionTestResult

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
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
        return []

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        return iter(())

    def open_session(self, config: RemoteConnectionConfig) -> Any:
        msg = f"open_session not used in this test for {config.connection_type}"
        raise AssertionError(msg)

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> bytes:
        msg = f"download not used in this test for {remote_path}"
        raise AssertionError(msg)

    def ensure_remote_directory(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> int:
        msg = f"ensure_remote_directory not used in this test for {remote_path}"
        raise AssertionError(msg)

    def upload_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        contents: bytes,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> None:
        msg = f"upload not used in this test for {remote_path}"
        raise AssertionError(msg)


def test_remote_connection_service_lists_no_connection_and_discovered_descriptors() -> None:
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
    service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(providers=[])
    )

    assert service.validate_optional_config(None) is None
    assert service.can_test_connection(None) is False


def test_remote_connection_service_treats_no_remote_connection_as_optional_none() -> None:
    service = RemoteConnectionService(registry=RemoteConnectionRegistry.discover_installed())

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
    service = RemoteConnectionService(registry=RemoteConnectionRegistry.discover_installed())

    with pytest.raises(SiteRegistryValidationError, match=r"Remote host must not be empty\."):
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


def test_remote_connection_service_tests_a_valid_provider_and_returns_structured_result() -> None:
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


def test_remote_connection_service_returns_false_for_invalid_testability_and_rejects_none() -> None:
    service = RemoteConnectionService(registry=RemoteConnectionRegistry.discover_installed())

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
