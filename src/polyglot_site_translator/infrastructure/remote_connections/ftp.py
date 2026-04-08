"""FTP and FTPS remote connection providers."""

from __future__ import annotations

from ftplib import FTP, FTP_TLS, all_errors
import socket
import ssl

from polyglot_site_translator.domain.remote_connections.models import (
    BuiltinRemoteConnectionType,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.infrastructure.remote_connections.base import (
    BaseRemoteConnectionProvider,
)


class FTPRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for plain FTP connectivity tests."""

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.FTP.value,
        display_name="FTP",
        default_port=21,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        client = FTP()
        try:
            client.connect(host=config.host, port=config.port, timeout=10)
            client.login(user=config.username, passwd=config.password)
            client.cwd(config.remote_path)
        except all_errors as error:
            return _failure_result(config, str(error), "ftp_connection_failed")
        finally:
            try:
                client.quit()
            except all_errors:
                client.close()
        return _success_result(config, "Connected successfully using FTP.")


class ExplicitFTPSRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for explicit FTPS connectivity tests."""

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.FTPS_EXPLICIT.value,
        display_name="FTPS Explicit",
        default_port=21,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        client = FTP_TLS()
        try:
            client.connect(host=config.host, port=config.port, timeout=10)
            client.auth()
            client.login(user=config.username, passwd=config.password)
            client.prot_p()
            client.cwd(config.remote_path)
        except all_errors as error:
            return _failure_result(config, str(error), "ftps_explicit_connection_failed")
        finally:
            try:
                client.quit()
            except all_errors:
                client.close()
        return _success_result(config, "Connected successfully using explicit FTPS.")


class ImplicitFtpTls(FTP_TLS):
    """Minimal implicit FTPS client for connectivity checks."""

    def connect(
        self,
        host: str = "",
        port: int = 0,
        timeout: float | None = None,
        source_address: tuple[str, int] | None = None,
    ) -> str:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.source_address = source_address
        self.sock = socket.create_connection((host, port), timeout, source_address)
        self.af = self.sock.family
        self.sock = self.context.wrap_socket(self.sock, server_hostname=host)
        self.file = self.sock.makefile("r", encoding=self.encoding)
        return self.getresp()


class ImplicitFTPSRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for implicit FTPS connectivity tests."""

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.FTPS_IMPLICIT.value,
        display_name="FTPS Implicit",
        default_port=990,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        client = ImplicitFtpTls(context=ssl.create_default_context())
        try:
            client.connect(host=config.host, port=config.port, timeout=10)
            client.login(user=config.username, passwd=config.password)
            client.prot_p()
            client.cwd(config.remote_path)
        except all_errors as error:
            return _failure_result(config, str(error), "ftps_implicit_connection_failed")
        finally:
            try:
                client.quit()
            except all_errors:
                client.close()
        return _success_result(config, "Connected successfully using implicit FTPS.")


def _success_result(
    config: RemoteConnectionConfigInput,
    message: str,
) -> RemoteConnectionTestResult:
    return RemoteConnectionTestResult(
        success=True,
        connection_type=config.connection_type,
        host=config.host,
        port=config.port,
        message=message,
        error_code=None,
    )


def _failure_result(
    config: RemoteConnectionConfigInput,
    message: str,
    error_code: str,
) -> RemoteConnectionTestResult:
    return RemoteConnectionTestResult(
        success=False,
        connection_type=config.connection_type,
        host=config.host,
        port=config.port,
        message=message,
        error_code=error_code,
    )
