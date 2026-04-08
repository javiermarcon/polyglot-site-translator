"""Unit tests for concrete remote connection providers."""

from __future__ import annotations

from dataclasses import dataclass
import socket
import ssl
from types import SimpleNamespace
from typing import Any, cast

import pytest

from polyglot_site_translator.domain.remote_connections.models import (
    BuiltinRemoteConnectionType,
    RemoteConnectionConfigInput,
)
from polyglot_site_translator.infrastructure.remote_connections import ftp, ssh


def _build_config(connection_type: str) -> RemoteConnectionConfigInput:
    return RemoteConnectionConfigInput(
        connection_type=connection_type,
        host="example.test",
        port=22 if connection_type in {"sftp", "scp"} else 21,
        username="deploy",
        password="secret",
        remote_path="/remote/path",
    )


@dataclass
class _BaseFakeFtpClient:
    actions: list[str]
    fail_on: str | None = None
    quit_raises: bool = False

    def connect(self, *, host: str, port: int, timeout: int) -> None:
        self.actions.append(f"connect:{host}:{port}:{timeout}")
        if self.fail_on == "connect":
            msg = "connect failed"
            raise OSError(msg)

    def login(self, *, user: str, passwd: str) -> None:
        self.actions.append(f"login:{user}:{passwd}")
        if self.fail_on == "login":
            msg = "login failed"
            raise OSError(msg)

    def cwd(self, remote_path: str) -> None:
        self.actions.append(f"cwd:{remote_path}")
        if self.fail_on == "cwd":
            msg = "cwd failed"
            raise OSError(msg)

    def quit(self) -> None:
        self.actions.append("quit")
        if self.quit_raises:
            msg = "quit failed"
            raise OSError(msg)

    def close(self) -> None:
        self.actions.append("close")


class _FakeExplicitFtpsClient(_BaseFakeFtpClient):
    def auth(self) -> None:
        self.actions.append("auth")
        if self.fail_on == "auth":
            msg = "auth failed"
            raise OSError(msg)

    def prot_p(self) -> None:
        self.actions.append("prot_p")
        if self.fail_on == "prot_p":
            msg = "prot_p failed"
            raise OSError(msg)


class _FakeImplicitFtpsClient(_BaseFakeFtpClient):
    def __init__(
        self,
        *,
        actions: list[str],
        context: object,
        fail_on: str | None = None,
        quit_raises: bool = False,
    ) -> None:
        super().__init__(actions=actions, fail_on=fail_on, quit_raises=quit_raises)
        self.context = context

    def prot_p(self) -> None:
        self.actions.append("prot_p")
        if self.fail_on == "prot_p":
            msg = "prot_p failed"
            raise OSError(msg)


def test_ftp_provider_returns_success_when_connection_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    actions: list[str] = []
    fake_client = _BaseFakeFtpClient(actions=actions, fail_on="cwd", quit_raises=True)
    monkeypatch.setattr(ftp, "FTP", lambda: fake_client)

    result = ftp.FTPRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.FTP.value)
    )

    assert result.success is False
    assert result.error_code == "ftp_connection_failed"
    assert result.message == "cwd failed"
    assert actions[-2:] == ["quit", "close"]


def test_explicit_ftps_provider_authenticates_and_protects_data_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    actions: list[str] = []
    fake_client = _FakeExplicitFtpsClient(actions=actions, fail_on="auth", quit_raises=True)
    monkeypatch.setattr(ftp, "FTP_TLS", lambda: fake_client)

    result = ftp.ExplicitFTPSRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.FTPS_EXPLICIT.value)
    )

    assert result.success is False
    assert result.error_code == "ftps_explicit_connection_failed"
    assert result.message == "auth failed"
    assert actions[-2:] == ["quit", "close"]


def test_implicit_ftp_tls_wraps_socket_and_reads_server_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class _FakeRawSocket:
        family = 123

    class _FakeWrappedSocket:
        def makefile(self, mode: str, encoding: str) -> str:
            events.append(f"makefile:{mode}:{encoding}")
            return "wrapped-file"

    class _FakeContext:
        def wrap_socket(self, sock: object, *, server_hostname: str) -> _FakeWrappedSocket:
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


def test_implicit_ftps_provider_uses_tls_context_and_returns_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actions: list[str] = []
    fake_context = object()
    captured_contexts: list[object] = []

    def _build_client(*, context: object) -> _FakeImplicitFtpsClient:
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
    assert result.error_code == "ftps_implicit_connection_failed"
    assert result.message == "login failed"
    assert actions[-2:] == ["quit", "close"]


class _FakeSftpClient:
    def __init__(self, actions: list[str], *, fail_on_chdir: bool = False) -> None:
        self._actions = actions
        self._fail_on_chdir = fail_on_chdir

    def chdir(self, remote_path: str) -> None:
        self._actions.append(f"chdir:{remote_path}")
        if self._fail_on_chdir:
            msg = "missing remote path"
            raise OSError(msg)

    def close(self) -> None:
        self._actions.append("sftp_close")


class _FakeSshClient:
    def __init__(
        self,
        actions: list[str],
        *,
        fail_on_connect: bool = False,
        fail_on_chdir: bool = False,
    ) -> None:
        self._actions = actions
        self._fail_on_connect = fail_on_connect
        self._fail_on_chdir = fail_on_chdir

    def load_system_host_keys(self) -> None:
        self._actions.append("load_system_host_keys")

    def connect(
        self,
        *,
        hostname: str,
        port: int,
        username: str,
        password: str,
        timeout: int,
    ) -> None:
        self._actions.append(f"connect:{hostname}:{port}:{username}:{password}:{timeout}")
        if self._fail_on_connect:
            msg = "ssh connect failed"
            raise OSError(msg)

    def open_sftp(self) -> _FakeSftpClient:
        self._actions.append("open_sftp")
        return _FakeSftpClient(self._actions, fail_on_chdir=self._fail_on_chdir)

    def close(self) -> None:
        self._actions.append("ssh_close")


def test_sftp_provider_returns_success_when_ssh_transport_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


def test_scp_provider_returns_failure_when_ssh_client_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    assert result.message == "ssh connect failed"


def test_sftp_provider_returns_failure_when_remote_path_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ssh,
        "_build_ssh_client",
        lambda: _FakeSshClient([], fail_on_chdir=True),
    )

    result = ssh.SFTPRemoteConnectionProvider().test_connection(
        _build_config(BuiltinRemoteConnectionType.SFTP.value)
    )

    assert result.success is False
    assert result.error_code == "ssh_connection_failed"
    assert result.message == "missing remote path"


def test_ssh_providers_report_missing_paramiko_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    sentinel = object()
    monkeypatch.setattr(
        ssh,
        "import_module",
        lambda module_name: (
            SimpleNamespace(SSHClient=lambda: sentinel) if module_name == "paramiko" else None
        ),
    )

    assert ssh._build_ssh_client() is sentinel
