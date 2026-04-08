"""SFTP and SCP remote connection providers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from polyglot_site_translator.domain.remote_connections.models import (
    BuiltinRemoteConnectionType,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.infrastructure.remote_connections.base import (
    BaseRemoteConnectionProvider,
)


class SFTPRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for SFTP connectivity tests."""

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.SFTP.value,
        display_name="SFTP",
        default_port=22,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        return _test_ssh_connection(config, "Connected successfully using SFTP.")


class SCPRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for SCP connectivity tests over SSH."""

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.SCP.value,
        display_name="SCP",
        default_port=22,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        return _test_ssh_connection(config, "Connected successfully using SCP.")


def _test_ssh_connection(
    config: RemoteConnectionConfigInput,
    success_message: str,
) -> RemoteConnectionTestResult:
    try:
        ssh_client = _build_ssh_client()
        ssh_client.load_system_host_keys()
        ssh_client.connect(
            hostname=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            timeout=10,
        )
        sftp_client = ssh_client.open_sftp()
        sftp_client.chdir(config.remote_path)
        sftp_client.close()
        ssh_client.close()
    except ModuleNotFoundError:
        return RemoteConnectionTestResult(
            success=False,
            connection_type=config.connection_type,
            host=config.host,
            port=config.port,
            message="Paramiko is required for SSH-based remote connections.",
            error_code="missing_dependency",
        )
    except OSError as error:
        return RemoteConnectionTestResult(
            success=False,
            connection_type=config.connection_type,
            host=config.host,
            port=config.port,
            message=str(error),
            error_code="ssh_connection_failed",
        )
    return RemoteConnectionTestResult(
        success=True,
        connection_type=config.connection_type,
        host=config.host,
        port=config.port,
        message=success_message,
        error_code=None,
    )


def _build_ssh_client() -> Any:
    paramiko = import_module("paramiko")
    return paramiko.SSHClient()
