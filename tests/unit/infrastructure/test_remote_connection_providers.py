"""Unit tests for concrete remote connection providers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import socket
import ssl
from types import SimpleNamespace
from typing import Any, cast

import pytest

from polyglot_site_translator.domain.remote_connections.models import (
    BuiltinRemoteConnectionType,
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionFlags,
)
from polyglot_site_translator.infrastructure.remote_connections import ftp, ssh


def _build_config(connection_type: str) -> RemoteConnectionConfigInput:
    """Handle build config.

    Args:
        connection_type:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return RemoteConnectionConfigInput(
        connection_type=connection_type,
        host="example.test",
        port=22 if connection_type in {"sftp", "scp"} else 21,
        username="deploy",
        password="secret",
        remote_path="/remote/path",
    )


def _build_remote_config(connection_type: str) -> RemoteConnectionConfig:
    """Handle build remote config.

    Args:
        connection_type:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return RemoteConnectionConfig(
        id="remote-1",
        site_project_id="site-1",
        connection_type=connection_type,
        host="example.test",
        port=22 if connection_type in {"sftp", "scp"} else 21,
        username="deploy",
        password="secret",
        remote_path="/remote/path",
    )


@dataclass
class _BaseFakeFtpClient:
    """Test helper for BaseFakeFtpClient.

    Attributes:
        actions:
            Documented attribute exposed by this type.
        fail_on:
            Documented attribute exposed by this type.
        quit_raises:
            Documented attribute exposed by this type.
    """

    actions: list[str]
    fail_on: str | None = None
    quit_raises: bool = False

    def connect(self, *, host: str, port: int, timeout: int) -> None:
        """Handle connect.

        Args:
            self:
                Value supplied to this callable.
            host:
                Value supplied to this callable.
            port:
                Value supplied to this callable.
            timeout:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.actions.append(f"connect:{host}:{port}:{timeout}")
        if self.fail_on == "connect":
            msg = "connect failed"
            raise OSError(msg)

    def login(self, *, user: str, passwd: str) -> None:
        """Handle login.

        Args:
            self:
                Value supplied to this callable.
            user:
                Value supplied to this callable.
            passwd:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.actions.append(f"login:{user}:{passwd}")
        if self.fail_on == "login":
            msg = "login failed"
            raise OSError(msg)

    def cwd(self, remote_path: str) -> None:
        """Handle cwd.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.actions.append(f"cwd:{remote_path}")
        if self.fail_on == "cwd":
            msg = "cwd failed"
            raise OSError(msg)

    def mlsd(self, remote_path: str) -> list[tuple[str, dict[str, str]]]:
        """Handle mlsd.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.actions.append(f"mlsd:{remote_path}")
        return [("messages.po", {"type": "file", "size": "7"})]

    def retrbinary(self, command: str, callback: Any) -> None:
        """Handle retrbinary.

        Args:
            self:
                Value supplied to this callable.
            command:
                Value supplied to this callable.
            callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.actions.append(f"retrbinary:{command}")
        callback(b"payload")

    def quit(self) -> None:
        """Handle quit.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.actions.append("quit")
        if self.quit_raises:
            msg = "quit failed"
            raise OSError(msg)

    def close(self) -> None:
        """Handle close.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.actions.append("close")


class _FakeExplicitFtpsClient(_BaseFakeFtpClient):
    """Test helper for FakeExplicitFtpsClient.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def auth(self) -> None:
        """Handle auth.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.actions.append("auth")
        if self.fail_on == "auth":
            msg = "auth failed"
            raise OSError(msg)

    def prot_p(self) -> None:
        """Handle prot p.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.actions.append("prot_p")
        if self.fail_on == "prot_p":
            msg = "prot_p failed"
            raise OSError(msg)


class _FakeImplicitFtpsClient(_BaseFakeFtpClient):
    """Test helper for FakeImplicitFtpsClient.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self,
        *,
        actions: list[str],
        context: object,
        fail_on: str | None = None,
        quit_raises: bool = False,
    ) -> None:
        """Initialize the test helper state.

        Args:
            self:
                Value supplied to this callable.
            actions:
                Value supplied to this callable.
            context:
                Value supplied to this callable.
            fail_on:
                Value supplied to this callable.
            quit_raises:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(actions=actions, fail_on=fail_on, quit_raises=quit_raises)
        self.context = context

    def prot_p(self) -> None:
        """Handle prot p.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.actions.append("prot_p")
        if self.fail_on == "prot_p":
            msg = "prot_p failed"
            raise OSError(msg)


def test_ftp_provider_returns_success_when_connection_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ftp provider returns success when connection succeeds.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    actions: list[str] = []
    fake_client = _BaseFakeFtpClient(actions=actions)
    monkeypatch.setattr(ftp, "FTP", lambda: fake_client)

    result = ftp.FTPRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.FTP.value)
    )

    assert result.success is True
    assert result.error_code is None
    assert result.message == "Connected successfully using FTP."
    assert actions == [
        "connect:example.test:21:10",
        "login:deploy:secret",
        "cwd:/remote/path",
        "quit",
    ]


def test_ftp_provider_closes_client_when_quit_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ftp provider closes client when quit raises.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    actions: list[str] = []
    fake_client = _BaseFakeFtpClient(actions=actions, fail_on="cwd", quit_raises=True)
    monkeypatch.setattr(ftp, "FTP", lambda: fake_client)

    result = ftp.FTPRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.FTP.value)
    )

    assert result.success is False
    assert result.error_code == "remote_path_not_found"
    assert result.message == (
        "FTP connection test failed for ftp example.test:21 at remote path "
        "'/remote/path'. Cause (remote_path_not_found): cwd failed"
    )
    assert actions[-2:] == ["quit", "close"]


def test_ftp_provider_classifies_dns_resolution_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ftp provider classifies dns resolution failures.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        gaierror:
            Raised when this callable hits the corresponding error path.
    """
    actions: list[str] = []

    class _DnsFailingFtpClient(_BaseFakeFtpClient):
        """Test helper for DnsFailingFtpClient.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        def connect(self, *, host: str, port: int, timeout: int) -> None:
            """Handle connect.

            Args:
                self:
                    Value supplied to this callable.
                host:
                    Value supplied to this callable.
                port:
                    Value supplied to this callable.
                timeout:
                    Value supplied to this callable.

            Returns:
                value:
                    Structured value returned by this callable.

            Raises:
                gaierror:
                    Raised when this callable hits the corresponding error path.
            """
            self.actions.append(f"connect:{host}:{port}:{timeout}")
            msg = "Temporary failure in name resolution"
            raise socket.gaierror(msg)

    fake_client = _DnsFailingFtpClient(actions=actions)
    monkeypatch.setattr(ftp, "FTP", lambda: fake_client)

    result = ftp.FTPRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.FTP.value)
    )

    assert result.success is False
    assert result.error_code == "dns_resolution_failed"
    assert result.message == (
        "FTP connection test failed for ftp example.test:21 at remote path "
        "'/remote/path'. Cause (dns_resolution_failed): Temporary failure "
        "in name resolution"
    )


def test_ftp_error_normalization_covers_timeout_refusal_and_permission_cases() -> None:
    """Verify ftp error normalization covers timeout refusal and permission cases.

    Returns:
        value:
            Structured value returned by this callable.
    """
    timeout_error = ftp._normalize_ftp_error(
        OSError("timed out"),
        default_code="ftp_connection_failed",
    )
    refusal_error = ftp._normalize_ftp_error(
        OSError("Connection refused"),
        default_code="ftp_connection_failed",
    )
    permission_error = ftp._normalize_ftp_error(
        OSError("Permission denied"),
        default_code="download_failed",
    )

    assert timeout_error.error_code == "connection_timeout"
    assert refusal_error.error_code == "connection_refused"
    assert permission_error.error_code == "remote_permission_denied"


def test_ftp_error_normalization_covers_default_and_tls_cases() -> None:
    """Verify ftp error normalization covers default and tls cases.

    Returns:
        value:
            Structured value returned by this callable.
    """
    default_error = ftp._normalize_ftp_error(
        OSError("unexpected ftp error"),
        default_code="ftp_connection_failed",
    )
    tls_error = ftp._normalize_ftp_error(
        OSError("TLS handshake failed"),
        default_code="ftps_explicit_connection_failed",
    )

    assert default_error.error_code == "ftp_connection_failed"
    assert tls_error.error_code == "tls_handshake_failed"


def test_explicit_ftps_provider_authenticates_and_protects_data_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify explicit ftps provider authenticates and protects data channel.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    actions: list[str] = []
    fake_client = _FakeExplicitFtpsClient(actions=actions)
    monkeypatch.setattr(ftp, "FTP_TLS", lambda: fake_client)

    result = ftp.ExplicitFTPSRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.FTPS_EXPLICIT.value)
    )

    assert result.success is True
    assert result.message == "Connected successfully using explicit FTPS."
    assert actions == [
        "connect:example.test:21:10",
        "auth",
        "login:deploy:secret",
        "prot_p",
        "cwd:/remote/path",
        "quit",
    ]


def test_explicit_ftps_provider_returns_failure_on_tls_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify explicit ftps provider returns failure on tls error.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    actions: list[str] = []
    fake_client = _FakeExplicitFtpsClient(
        actions=actions, fail_on="auth", quit_raises=True
    )
    monkeypatch.setattr(ftp, "FTP_TLS", lambda: fake_client)

    result = ftp.ExplicitFTPSRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.FTPS_EXPLICIT.value)
    )

    assert result.success is False
    assert result.error_code == "tls_handshake_failed"
    assert result.message == (
        "FTPS explicit connection test failed for ftps_explicit example.test:21 "
        "at remote path '/remote/path'. Cause (tls_handshake_failed): auth failed"
    )
    assert actions[-2:] == ["quit", "close"]


def test_explicit_ftps_provider_downloads_remote_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify explicit ftps provider downloads remote file.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    actions: list[str] = []
    fake_client = _FakeExplicitFtpsClient(actions=actions)
    provider = ftp.ExplicitFTPSRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)

    file_bytes = provider.download_file(
        _build_remote_config("ftps_explicit"),
        "/srv/app/messages.po",
    )

    assert file_bytes == b"payload"
    assert actions == [
        "connect:example.test:21:10",
        "auth",
        "login:deploy:secret",
        "prot_p",
        "retrbinary:RETR /srv/app/messages.po",
        "quit",
    ]


def test_implicit_ftp_tls_wraps_socket_and_reads_server_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify implicit ftp tls wraps socket and reads server response.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    events: list[str] = []

    class _FakeRawSocket:
        """Test helper for FakeRawSocket.

        Attributes:
            family:
                Documented attribute exposed by this type.
        """

        family = 123

    class _FakeWrappedSocket:
        """Test helper for FakeWrappedSocket.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        def makefile(self, mode: str, encoding: str) -> str:
            """Handle makefile.

            Args:
                self:
                    Value supplied to this callable.
                mode:
                    Value supplied to this callable.
                encoding:
                    Value supplied to this callable.

            Returns:
                value:
                    Structured value returned by this callable.
            """
            events.append(f"makefile:{mode}:{encoding}")
            return "wrapped-file"

    class _FakeContext:
        """Test helper for FakeContext.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        def wrap_socket(
            self, sock: object, *, server_hostname: str
        ) -> _FakeWrappedSocket:
            """Handle wrap socket.

            Args:
                self:
                    Value supplied to this callable.
                sock:
                    Value supplied to this callable.
                server_hostname:
                    Value supplied to this callable.

            Returns:
                value:
                    Structured value returned by this callable.
            """
            assert sock is raw_socket
            events.append(f"wrap_socket:{server_hostname}")
            return wrapped_socket

    raw_socket = _FakeRawSocket()
    wrapped_socket = _FakeWrappedSocket()

    def _create_connection(
        address: tuple[str, int],
        timeout: float | None,
        source_address: tuple[str, int] | None,
    ) -> _FakeRawSocket:
        """Handle create connection.

        Args:
            address:
                Value supplied to this callable.
            timeout:
                Value supplied to this callable.
            source_address:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        events.append(f"create_connection:{address}:{timeout}:{source_address}")
        return raw_socket

    monkeypatch.setattr(
        socket,
        "create_connection",
        _create_connection,
    )

    client = cast(Any, object.__new__(ftp.ImplicitFtpTls))
    client.context = _FakeContext()
    client.encoding = "utf-8"
    client.getresp = lambda: "220 ready"

    response = ftp.ImplicitFtpTls.connect(
        client,
        host="example.test",
        port=990,
        timeout=10,
        source_address=("127.0.0.1", 0),
    )

    assert response == "220 ready"
    assert client.host == "example.test"
    assert client.port == 990
    assert client.timeout == 10
    assert client.source_address == ("127.0.0.1", 0)
    assert client.af == 123
    assert client.file == "wrapped-file"
    assert events == [
        "create_connection:('example.test', 990):10:('127.0.0.1', 0)",
        "wrap_socket:example.test",
        "makefile:r:utf-8",
    ]


def test_implicit_ftp_tls_keeps_existing_timeout_when_timeout_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify implicit ftp tls keeps existing timeout when timeout is omitted.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """

    class _FakeRawSocket:
        """Test helper for FakeRawSocket.

        Attributes:
            family:
                Documented attribute exposed by this type.
        """

        family = 123

    class _FakeWrappedSocket:
        """Test helper for FakeWrappedSocket.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        @staticmethod
        def makefile(mode: str, encoding: str) -> str:
            """Handle makefile.

            Args:
                mode:
                    Value supplied to this callable.
                encoding:
                    Value supplied to this callable.

            Returns:
                value:
                    Structured value returned by this callable.
            """
            return "wrapped-file"

    class _FakeContext:
        """Test helper for FakeContext.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        @staticmethod
        def wrap_socket(sock: object, *, server_hostname: str) -> _FakeWrappedSocket:
            """Handle wrap socket.

            Args:
                sock:
                    Value supplied to this callable.
                server_hostname:
                    Value supplied to this callable.

            Returns:
                value:
                    Structured value returned by this callable.
            """
            assert sock is raw_socket
            assert server_hostname == "example.test"
            return wrapped_socket

    raw_socket = _FakeRawSocket()
    wrapped_socket = _FakeWrappedSocket()
    monkeypatch.setattr(socket, "create_connection", lambda *args: raw_socket)

    client = cast(Any, object.__new__(ftp.ImplicitFtpTls))
    client.context = _FakeContext()
    client.encoding = "utf-8"
    client.timeout = 30
    client.getresp = lambda: "220 ready"

    response = ftp.ImplicitFtpTls.connect(
        client,
        host="example.test",
        port=990,
        timeout=None,
    )

    assert response == "220 ready"
    assert client.timeout == 30


def test_implicit_ftps_provider_uses_tls_context_and_returns_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify implicit ftps provider uses tls context and returns success.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    actions: list[str] = []
    fake_context = object()
    captured_contexts: list[object] = []

    def _build_client(*, context: object) -> _FakeImplicitFtpsClient:
        """Handle build client.

        Args:
            context:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        captured_contexts.append(context)
        return _FakeImplicitFtpsClient(actions=actions, context=context)

    monkeypatch.setattr(ssl, "create_default_context", lambda: fake_context)
    monkeypatch.setattr(ftp, "ImplicitFtpTls", _build_client)

    result = ftp.ImplicitFTPSRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.FTPS_IMPLICIT.value)
    )

    assert result.success is True
    assert result.message == "Connected successfully using implicit FTPS."
    assert captured_contexts == [fake_context]
    assert actions == [
        "connect:example.test:21:10",
        "login:deploy:secret",
        "prot_p",
        "cwd:/remote/path",
        "quit",
    ]


def test_implicit_ftps_provider_returns_failure_when_login_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify implicit ftps provider returns failure when login fails.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    actions: list[str] = []
    fake_context = object()
    monkeypatch.setattr(ssl, "create_default_context", lambda: fake_context)
    monkeypatch.setattr(
        ftp,
        "ImplicitFtpTls",
        lambda *, context: _FakeImplicitFtpsClient(
            actions=actions,
            context=context,
            fail_on="login",
            quit_raises=True,
        ),
    )

    result = ftp.ImplicitFTPSRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.FTPS_IMPLICIT.value)
    )

    assert result.success is False
    assert result.error_code == "authentication_failed"
    assert result.message == (
        "FTPS implicit connection test failed for ftps_implicit example.test:21 "
        "at remote path '/remote/path'. Cause (authentication_failed): login failed"
    )
    assert actions[-2:] == ["quit", "close"]


def test_implicit_ftps_provider_lists_remote_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify implicit ftps provider lists remote files.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    actions: list[str] = []
    fake_client = _FakeImplicitFtpsClient(actions=actions, context=object())
    provider = ftp.ImplicitFTPSRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)

    remote_files = provider.list_remote_files(_build_remote_config("ftps_implicit"))

    assert [remote_file.remote_path for remote_file in remote_files] == [
        "/remote/path/messages.po"
    ]
    assert actions == [
        "connect:example.test:21:10",
        "login:deploy:secret",
        "prot_p",
        "mlsd:/remote/path",
        "quit",
    ]


def test_close_ftp_client_uses_oserror_branch_when_library_error_tuple_excludes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify close ftp client uses oserror branch when library error tuple excludes it.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        OSError:
            Raised when this callable hits the corresponding error path.
    """
    events: list[str] = []

    class _OSErrorFtpClient:
        """Test helper for OSErrorFtpClient.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        @staticmethod
        def quit() -> None:
            """Handle quit.

            Returns:
                value:
                    Structured value returned by this callable.

            Raises:
                OSError:
                    Raised when this callable hits the corresponding error path.
            """
            events.append("quit")
            msg = "network down"
            raise OSError(msg)

        @staticmethod
        def close() -> None:
            """Handle close.

            Returns:
                value:
                    Structured value returned by this callable.
            """
            events.append("close")

    monkeypatch.setattr(ftp, "all_errors", (EOFError,))

    ftp._close_ftp_client(cast(Any, _OSErrorFtpClient()))

    assert events == ["quit", "close"]


def test_close_ftp_socket_uses_oserror_branch_when_library_error_tuple_excludes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify close ftp socket uses oserror branch when library error tuple excludes it.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        OSError:
            Raised when this callable hits the corresponding error path.
    """

    class _OSErrorSocketClient:
        """Test helper for OSErrorSocketClient.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        @staticmethod
        def close() -> None:
            """Handle close.

            Returns:
                value:
                    Structured value returned by this callable.

            Raises:
                OSError:
                    Raised when this callable hits the corresponding error path.
            """
            msg = "socket close failed"
            raise OSError(msg)

    monkeypatch.setattr(ftp, "all_errors", (EOFError,))

    ftp._close_ftp_socket(cast(Any, _OSErrorSocketClient()))


class _FakeSftpClient:
    """Test helper for FakeSftpClient.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(self, actions: list[str], *, fail_on_chdir: bool = False) -> None:
        """Initialize the test helper state.

        Args:
            self:
                Value supplied to this callable.
            actions:
                Value supplied to this callable.
            fail_on_chdir:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._actions = actions
        self._fail_on_chdir = fail_on_chdir

    def chdir(self, remote_path: str) -> None:
        """Handle chdir.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self._actions.append(f"chdir:{remote_path}")
        if self._fail_on_chdir:
            msg = "missing remote path"
            raise OSError(msg)

    def close(self) -> None:
        """Handle close.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._actions.append("sftp_close")


class _FakeSshClient:
    """Test helper for FakeSshClient.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self,
        actions: list[str],
        *,
        fail_on_connect: bool = False,
        fail_on_chdir: bool = False,
    ) -> None:
        """Initialize the test helper state.

        Args:
            self:
                Value supplied to this callable.
            actions:
                Value supplied to this callable.
            fail_on_connect:
                Value supplied to this callable.
            fail_on_chdir:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._actions = actions
        self._fail_on_connect = fail_on_connect
        self._fail_on_chdir = fail_on_chdir

    def load_system_host_keys(self) -> None:
        """Handle load system host keys.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._actions.append("load_system_host_keys")

    def load_host_keys(self, filename: str) -> None:
        """Handle load host keys.

        Args:
            self:
                Value supplied to this callable.
            filename:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._actions.append(f"load_host_keys:{filename}")

    def set_missing_host_key_policy(self, policy: object) -> None:
        """Handle set missing host key policy.

        Args:
            self:
                Value supplied to this callable.
            policy:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._actions.append(f"set_missing_host_key_policy:{policy.__class__.__name__}")

    def connect(
        self,
        *,
        hostname: str,
        port: int,
        username: str,
        password: str,
        timeout: int,
    ) -> None:
        """Handle connect.

        Args:
            self:
                Value supplied to this callable.
            hostname:
                Value supplied to this callable.
            port:
                Value supplied to this callable.
            username:
                Value supplied to this callable.
            password:
                Value supplied to this callable.
            timeout:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self._actions.append(
            f"connect:{hostname}:{port}:{username}:{password}:{timeout}"
        )
        if self._fail_on_connect:
            msg = "ssh connect failed"
            raise OSError(msg)

    def open_sftp(self) -> _FakeSftpClient:
        """Handle open sftp.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._actions.append("open_sftp")
        return _FakeSftpClient(self._actions, fail_on_chdir=self._fail_on_chdir)

    def close(self) -> None:
        """Handle close.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._actions.append("ssh_close")


def test_sftp_provider_returns_success_when_ssh_transport_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify sftp provider returns success when ssh transport succeeds.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    actions: list[str] = []
    monkeypatch.setattr(ssh, "_build_ssh_client", lambda: _FakeSshClient(actions))

    result = ssh.SFTPRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.SFTP.value)
    )

    assert result.success is True
    assert result.message == "Connected successfully using SFTP."
    assert actions == [
        "load_system_host_keys",
        "connect:example.test:22:deploy:secret:10",
        "open_sftp",
        "chdir:/remote/path",
        "sftp_close",
        "ssh_close",
    ]


def test_sftp_provider_can_auto_add_unknown_hosts_when_verification_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify sftp provider can auto add unknown hosts when verification is disabled.

    Args:
        monkeypatch:
            Value supplied to this callable.
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    actions: list[str] = []

    class _FakeAutoAddPolicy:
        """Test helper for FakeAutoAddPolicy.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        pass

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(
        ssh,
        "import_module",
        lambda module_name: SimpleNamespace(
            SSHClient=lambda: _FakeSshClient(actions),
            SSHException=OSError,
            AutoAddPolicy=_FakeAutoAddPolicy,
        ),
    )
    config = RemoteConnectionConfigInput(
        connection_type=BuiltinRemoteConnectionType.SFTP.value,
        host="example.test",
        port=22,
        username="deploy",
        password="secret",
        remote_path="/remote/path",
        flags=RemoteConnectionFlags(verify_host=False),
    )

    result = ssh.SFTPRemoteConnectionProvider().test_connection(config)

    assert result.success is True
    assert actions[:4] == [
        "load_system_host_keys",
        f"load_host_keys:{tmp_path / '.ssh' / 'known_hosts'}",
        "set_missing_host_key_policy:_FakeAutoAddPolicy",
        "connect:example.test:22:deploy:secret:10",
    ]
    assert (tmp_path / ".ssh" / "known_hosts").exists()


def test_scp_provider_returns_failure_when_ssh_client_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify scp provider returns failure when ssh client errors.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    monkeypatch.setattr(
        ssh,
        "_build_ssh_client",
        lambda: _FakeSshClient([], fail_on_connect=True),
    )

    result = ssh.SCPRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.SCP.value)
    )

    assert result.success is False
    assert result.error_code == "ssh_connection_failed"
    assert result.message == (
        "SSH connection test failed for scp example.test:22 at remote path "
        "'/remote/path'. Cause (ssh_connection_failed): ssh connect failed"
    )


def test_scp_provider_classifies_ssh_dns_resolution_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify scp provider classifies ssh dns resolution failures.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        gaierror:
            Raised when this callable hits the corresponding error path.
    """

    class _DnsFailingSshClient(_FakeSshClient):
        """Test helper for DnsFailingSshClient.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        def connect(
            self,
            *,
            hostname: str,
            port: int,
            username: str,
            password: str,
            timeout: int,
        ) -> None:
            """Handle connect.

            Args:
                self:
                    Value supplied to this callable.
                hostname:
                    Value supplied to this callable.
                port:
                    Value supplied to this callable.
                username:
                    Value supplied to this callable.
                password:
                    Value supplied to this callable.
                timeout:
                    Value supplied to this callable.

            Returns:
                value:
                    Structured value returned by this callable.

            Raises:
                gaierror:
                    Raised when this callable hits the corresponding error path.
            """
            self._actions.append(
                f"connect:{hostname}:{port}:{username}:{password}:{timeout}"
            )
            msg = "Temporary failure in name resolution"
            raise socket.gaierror(msg)

    monkeypatch.setattr(
        ssh,
        "_build_ssh_client",
        lambda: _DnsFailingSshClient([]),
    )

    result = ssh.SCPRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.SCP.value)
    )

    assert result.success is False
    assert result.error_code == "dns_resolution_failed"
    assert result.message == (
        "SSH connection test failed for scp example.test:22 at remote path "
        "'/remote/path'. Cause (dns_resolution_failed): Temporary failure "
        "in name resolution"
    )


def test_sftp_provider_returns_failure_when_remote_path_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify sftp provider returns failure when remote path is invalid.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    monkeypatch.setattr(
        ssh,
        "_build_ssh_client",
        lambda: _FakeSshClient([], fail_on_chdir=True),
    )

    result = ssh.SFTPRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.SFTP.value)
    )

    assert result.success is False
    assert result.error_code == "remote_path_not_found"
    assert result.message == (
        "SSH connection test failed for sftp example.test:22 at remote path "
        "'/remote/path'. Cause (remote_path_not_found): missing remote path"
    )


def test_ssh_error_normaliz_covers_timeout_refusal_aut_fac8() -> None:
    """Verify SSH error normalization covers transport cases.

    io.

    Returns:
        value:
            Structured value returned by this callable.
    """
    timeout_error = ssh._normalize_ssh_error(
        OSError("timed out"),
        default_code="ssh_connection_failed",
    )
    refusal_error = ssh._normalize_ssh_error(
        OSError("Connection refused"),
        default_code="ssh_connection_failed",
    )
    auth_error = ssh._normalize_ssh_error(
        OSError("Authentication failed"),
        default_code="ssh_connection_failed",
    )
    host_key_error = ssh._normalize_ssh_error(
        OSError("Host key verification failed"),
        default_code="ssh_connection_failed",
    )
    transport_error = ssh._normalize_ssh_error(
        OSError("Broken pipe"),
        default_code="download_failed",
    )

    assert timeout_error.error_code == "connection_timeout"
    assert refusal_error.error_code == "connection_refused"
    assert auth_error.error_code == "authentication_failed"
    assert host_key_error.error_code == "host_key_failed"
    assert transport_error.error_code == "transport_io_failed"


def test_ssh_error_normalization_covers_remote_path_and_default_cases() -> None:
    """Verify ssh error normalization covers remote path and default cases.

    Returns:
        value:
            Structured value returned by this callable.
    """
    unknown_host_error = ssh._normalize_ssh_error(
        OSError("Server '127.0.0.1' not found in known_hosts"),
        default_code="ssh_connection_failed",
    )
    path_error = ssh._normalize_ssh_error(
        OSError("No such file"),
        default_code="remote_listing_failed",
    )
    default_error = ssh._normalize_ssh_error(
        OSError("unexpected ssh error"),
        default_code="ssh_connection_failed",
    )

    assert unknown_host_error.error_code == "unknown_ssh_host_key"
    assert path_error.error_code == "remote_path_not_found"
    assert default_error.error_code == "ssh_connection_failed"


def test_ssh_providers_report_missing_paramiko_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ssh providers report missing paramiko dependency.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    monkeypatch.setattr(
        ssh,
        "_build_ssh_client",
        lambda: (_ for _ in ()).throw(ModuleNotFoundError("paramiko")),
    )

    result = ssh.SFTPRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.SFTP.value)
    )

    assert result.success is False
    assert result.error_code == "missing_dependency"
    assert result.message == "Paramiko is required for SSH-based remote connections."


def test_build_ssh_client_uses_paramiko_ssh_client_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify build ssh client uses paramiko ssh client factory.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    sentinel = object()
    monkeypatch.setattr(
        ssh,
        "import_module",
        lambda module_name: (
            SimpleNamespace(SSHClient=lambda: sentinel)
            if module_name == "paramiko"
            else None
        ),
    )

    assert ssh._build_ssh_client() is sentinel
