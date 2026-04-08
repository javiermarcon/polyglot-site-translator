"""Unit tests for provider-level remote sync operations."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

import pytest

from polyglot_site_translator.domain.remote_connections.models import RemoteConnectionConfig
from polyglot_site_translator.infrastructure.remote_connections import ftp, ssh


def _build_ftp_config(connection_type: str = "ftp") -> RemoteConnectionConfig:
    return RemoteConnectionConfig(
        id="remote-1",
        site_project_id="site-1",
        connection_type=connection_type,
        host="example.test",
        port=21,
        username="deploy",
        password="secret",
        remote_path="/srv/app",
    )


def _build_ssh_config(connection_type: str = "sftp") -> RemoteConnectionConfig:
    return RemoteConnectionConfig(
        id="remote-1",
        site_project_id="site-1",
        connection_type=connection_type,
        host="example.test",
        port=22,
        username="deploy",
        password="secret",
        remote_path="/srv/app",
    )


@dataclass
class _FakeFtpClient:
    actions: list[str]
    listing: dict[str, list[tuple[str, dict[str, str]]]]
    file_bytes: dict[str, bytes]
    fail_on_retrbinary: str | None = None

    def connect(self, *, host: str, port: int, timeout: int) -> None:
        self.actions.append(f"connect:{host}:{port}:{timeout}")

    def login(self, *, user: str, passwd: str) -> None:
        self.actions.append(f"login:{user}:{passwd}")

    def cwd(self, remote_path: str) -> None:
        self.actions.append(f"cwd:{remote_path}")

    def mlsd(self, remote_path: str) -> list[tuple[str, dict[str, str]]]:
        self.actions.append(f"mlsd:{remote_path}")
        return list(self.listing.get(remote_path, []))

    def retrbinary(self, command: str, callback: Any) -> None:
        self.actions.append(f"retrbinary:{command}")
        remote_path = command.replace("RETR ", "", 1)
        if self.fail_on_retrbinary == remote_path:
            msg = f"download failed for {remote_path}"
            raise OSError(msg)
        callback(self.file_bytes[remote_path])

    def quit(self) -> None:
        self.actions.append("quit")

    def close(self) -> None:
        self.actions.append("close")


def test_ftp_provider_lists_remote_files_recursively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actions: list[str] = []
    fake_client = _FakeFtpClient(
        actions=actions,
        listing={
            "/srv/app": [
                ("locale", {"type": "dir"}),
                ("README.md", {"type": "file", "size": "12"}),
            ],
            "/srv/app/locale": [
                ("es.po", {"type": "file", "size": "20"}),
            ],
        },
        file_bytes={},
    )
    provider = ftp.FTPRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)

    remote_files = provider.list_remote_files(_build_ftp_config())

    assert [remote_file.relative_path for remote_file in remote_files] == [
        "locale/es.po",
        "README.md",
    ]
    assert [remote_file.remote_path for remote_file in remote_files] == [
        "/srv/app/locale/es.po",
        "/srv/app/README.md",
    ]
    assert actions[:3] == [
        "connect:example.test:21:10",
        "login:deploy:secret",
        "mlsd:/srv/app",
    ]


def test_ftp_provider_downloads_remote_file_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    actions: list[str] = []
    fake_client = _FakeFtpClient(
        actions=actions,
        listing={},
        file_bytes={"/srv/app/messages.po": b'msgid "hello"\n'},
    )
    provider = ftp.FTPRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)

    file_bytes = provider.download_file(_build_ftp_config(), "/srv/app/messages.po")

    assert file_bytes == b'msgid "hello"\n'
    assert actions == [
        "connect:example.test:21:10",
        "login:deploy:secret",
        "retrbinary:RETR /srv/app/messages.po",
        "quit",
    ]


def test_ftp_provider_wraps_download_failures_as_os_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeFtpClient(
        actions=[],
        listing={},
        file_bytes={"/srv/app/messages.po": b""},
        fail_on_retrbinary="/srv/app/messages.po",
    )
    provider = ftp.FTPRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)

    with pytest.raises(OSError, match=r"download failed for /srv/app/messages\.po"):
        provider.download_file(_build_ftp_config(), "/srv/app/messages.po")


def test_explicit_ftps_provider_lists_remote_files(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _FakeFtpClient(
        actions=[],
        listing={"/srv/app": [("messages.po", {"type": "file", "size": "8"})]},
        file_bytes={},
    )
    provider = ftp.ExplicitFTPSRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)
    monkeypatch.setattr(ftp, "_connect_explicit_ftps_client", lambda client, config: None)

    remote_files = provider.list_remote_files(_build_ftp_config("ftps_explicit"))

    assert [remote_file.remote_path for remote_file in remote_files] == ["/srv/app/messages.po"]


def test_implicit_ftps_provider_downloads_remote_file(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _FakeFtpClient(
        actions=[],
        listing={},
        file_bytes={"/srv/app/messages.po": b"payload"},
    )
    provider = ftp.ImplicitFTPSRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)
    monkeypatch.setattr(ftp, "_connect_implicit_ftps_client", lambda client, config: None)

    file_bytes = provider.download_file(_build_ftp_config("ftps_implicit"), "/srv/app/messages.po")

    assert file_bytes == b"payload"


def test_ftp_provider_wraps_listing_failures_as_os_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeFtpClient(actions=[], listing={}, file_bytes={})

    def _failing_mlsd(remote_path: str) -> list[tuple[str, dict[str, str]]]:
        msg = f"listing failed for {remote_path}"
        raise OSError(msg)

    fake_client.mlsd = _failing_mlsd  # type: ignore[method-assign]
    provider = ftp.FTPRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)

    with pytest.raises(OSError, match=r"listing failed for /srv/app"):
        provider.list_remote_files(_build_ftp_config())


def test_walk_ftp_directory_skips_navigation_and_unknown_entries() -> None:
    remote_files = ftp._walk_ftp_directory(
        client=cast(
            Any,
            _FakeFtpClient(
                actions=[],
                listing={
                    "/": [
                        (".", {"type": "cdir"}),
                        ("..", {"type": "pdir"}),
                        ("tmp", {"type": "dir"}),
                        ("ignored", {"type": "link"}),
                    ],
                    "/tmp": [("messages.po", {"type": "file", "size": "7"})],
                },
                file_bytes={},
            ),
        ),
        base_remote_path="/",
        current_remote_path="/",
    )

    assert [remote_file.relative_path for remote_file in remote_files] == ["tmp/messages.po"]


def test_ftp_remote_path_helpers_normalize_and_join_root_paths() -> None:
    assert ftp._normalize_remote_path(".") == "/"
    assert ftp._join_remote_path("/", "messages.po") == "/messages.po"


@dataclass
class _FakeSftpEntry:
    filename: str
    st_mode: int
    st_size: int


class _FakeRemoteFile:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.closed = False

    def read(self) -> bytes:
        return self._payload

    def close(self) -> None:
        self.closed = True


class _FakeSftpClient:
    def __init__(
        self,
        listing: dict[str, list[_FakeSftpEntry]],
        file_bytes: dict[str, bytes],
    ) -> None:
        self._listing = listing
        self._file_bytes = file_bytes
        self.actions: list[str] = []

    def listdir_attr(self, remote_path: str) -> list[_FakeSftpEntry]:
        self.actions.append(f"listdir_attr:{remote_path}")
        return list(self._listing.get(remote_path, []))

    def file(self, remote_path: str, *, mode: str) -> _FakeRemoteFile:
        self.actions.append(f"file:{remote_path}:{mode}")
        return _FakeRemoteFile(self._file_bytes[remote_path])

    def chdir(self, remote_path: str) -> None:
        self.actions.append(f"chdir:{remote_path}")

    def close(self) -> None:
        self.actions.append("sftp_close")


class _FakeSshClient:
    def __init__(self, sftp_client: _FakeSftpClient) -> None:
        self._sftp_client = sftp_client
        self.actions: list[str] = []

    def load_system_host_keys(self) -> None:
        self.actions.append("load_system_host_keys")

    def connect(
        self,
        *,
        hostname: str,
        port: int,
        username: str,
        password: str,
        timeout: int,
    ) -> None:
        self.actions.append(f"connect:{hostname}:{port}:{username}:{password}:{timeout}")

    def open_sftp(self) -> _FakeSftpClient:
        self.actions.append("open_sftp")
        return self._sftp_client

    def close(self) -> None:
        self.actions.append("ssh_close")


def test_sftp_provider_lists_remote_files_recursively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sftp_client = _FakeSftpClient(
        listing={
            "/srv/app": [
                _FakeSftpEntry("locale", 0o040755, 0),
                _FakeSftpEntry("README.md", 0o100644, 12),
            ],
            "/srv/app/locale": [
                _FakeSftpEntry("es.po", 0o100644, 20),
            ],
        },
        file_bytes={},
    )
    ssh_client = _FakeSshClient(sftp_client)
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)
    provider = ssh.SFTPRemoteConnectionProvider()

    remote_files = provider.list_remote_files(_build_ssh_config())

    assert [remote_file.relative_path for remote_file in remote_files] == [
        "locale/es.po",
        "README.md",
    ]
    assert sftp_client.actions == [
        "listdir_attr:/srv/app",
        "listdir_attr:/srv/app/locale",
        "sftp_close",
    ]
    assert ssh_client.actions == [
        "open_sftp",
        "ssh_close",
    ]


def test_sftp_provider_downloads_remote_file_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    sftp_client = _FakeSftpClient(
        listing={},
        file_bytes={"/srv/app/messages.po": b'msgid "hello"\n'},
    )
    ssh_client = _FakeSshClient(sftp_client)
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)
    provider = ssh.SFTPRemoteConnectionProvider()

    file_bytes = provider.download_file(_build_ssh_config(), "/srv/app/messages.po")

    assert file_bytes == b'msgid "hello"\n'
    assert sftp_client.actions == [
        "file:/srv/app/messages.po:rb",
        "sftp_close",
    ]
    assert ssh_client.actions == [
        "open_sftp",
        "ssh_close",
    ]


def test_scp_provider_lists_remote_files(monkeypatch: pytest.MonkeyPatch) -> None:
    sftp_client = _FakeSftpClient(
        listing={"/srv/app": [_FakeSftpEntry("messages.po", 0o100644, 8)]},
        file_bytes={},
    )
    ssh_client = _FakeSshClient(sftp_client)
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)

    remote_files = ssh.SCPRemoteConnectionProvider().list_remote_files(_build_ssh_config("scp"))

    assert [remote_file.relative_path for remote_file in remote_files] == ["messages.po"]


def test_scp_provider_downloads_remote_file_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    sftp_client = _FakeSftpClient(
        listing={},
        file_bytes={"/srv/app/messages.po": b"payload"},
    )
    ssh_client = _FakeSshClient(sftp_client)
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)

    payload = ssh.SCPRemoteConnectionProvider().download_file(
        _build_ssh_config("scp"),
        "/srv/app/messages.po",
    )

    assert payload == b"payload"


def test_connect_ssh_client_wraps_paramiko_ssh_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeSshError(OSError):
        pass

    class _FailingSshClient(_FakeSshClient):
        def connect(
            self,
            *,
            hostname: str,
            port: int,
            username: str,
            password: str,
            timeout: int,
        ) -> None:
            msg = "ssh transport failed"
            raise _FakeSshError(msg)

    monkeypatch.setattr(
        ssh,
        "import_module",
        lambda module_name: SimpleNamespace(SSHException=_FakeSshError),
    )
    monkeypatch.setattr(
        ssh,
        "_build_ssh_client",
        lambda: _FailingSshClient(_FakeSftpClient(listing={}, file_bytes={})),
    )

    with pytest.raises(OSError, match="ssh transport failed"):
        ssh._connect_ssh_client(_build_ssh_config())


def test_ssh_remote_path_helper_joins_root_paths() -> None:
    assert ssh._join_remote_path("/", "messages.po") == "/messages.po"


def test_build_ssh_client_uses_paramiko_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(
        ssh,
        "import_module",
        lambda module_name: (
            SimpleNamespace(SSHClient=lambda: sentinel) if module_name == "paramiko" else None
        ),
    )

    assert ssh._build_ssh_client() is sentinel
