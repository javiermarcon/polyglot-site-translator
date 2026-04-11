"""Unit tests for provider-level remote sync operations."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

import pytest

from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionSessionState,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import RemoteSyncFile
from polyglot_site_translator.infrastructure.remote_connections import (
    ftp,
    ssh,
)
from polyglot_site_translator.infrastructure.remote_connections.base import (
    BaseRemoteConnectionProvider,
    BaseRemoteConnectionSession,
    RemoteConnectionOperationError,
)


@dataclass
class _ListBackedSession:
    files: list[RemoteSyncFile]
    state: RemoteConnectionSessionState = RemoteConnectionSessionState.OPEN
    close_calls: int = 0
    uploaded_files: dict[str, bytes] | None = None
    created_directories: list[str] | None = None

    def iter_remote_files(self, progress_callback: Any = None) -> Iterator[RemoteSyncFile]:
        return iter(self.files)

    def download_file(self, remote_path: str, progress_callback: Any = None) -> bytes:
        msg = f"download not used in this test for {remote_path}"
        raise AssertionError(msg)

    def ensure_remote_directory(self, remote_path: str, progress_callback: Any = None) -> int:
        if self.created_directories is None:
            self.created_directories = []
        self.created_directories.append(remote_path)
        return 1

    def upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: Any = None,
    ) -> None:
        if self.uploaded_files is None:
            self.uploaded_files = {}
        self.uploaded_files[remote_path] = contents

    def close(self, progress_callback: Any = None) -> None:
        self.close_calls += 1
        self.state = RemoteConnectionSessionState.CLOSED


class _ControlledBaseSession(BaseRemoteConnectionSession):
    def __init__(
        self,
        config: RemoteConnectionConfig,
        *,
        connect_errors: list[RemoteConnectionOperationError] | None = None,
        close_error: RemoteConnectionOperationError | None = None,
        max_connect_attempts: int = 2,
    ) -> None:
        super().__init__(config, max_connect_attempts=max_connect_attempts)
        self.connect_errors = connect_errors or []
        self.close_error = close_error
        self.connect_calls = 0
        self.reset_calls = 0
        self.close_calls = 0

    def _connect(self, progress_callback: Any = None) -> None:
        self.connect_calls += 1
        if self.connect_errors:
            raise self.connect_errors.pop(0)

    def _iter_remote_files(self, progress_callback: Any = None) -> Iterator[RemoteSyncFile]:
        yield RemoteSyncFile(
            remote_path="/srv/app/messages.po",
            relative_path="messages.po",
            size_bytes=8,
        )

    def _download_file(self, remote_path: str, progress_callback: Any = None) -> bytes:
        return remote_path.encode()

    def _ensure_remote_directory(self, remote_path: str, progress_callback: Any = None) -> int:
        return 1

    def _upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: Any = None,
    ) -> None:
        return None

    def _close(self, progress_callback: Any = None) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error

    def _reset_after_failed_connect(self) -> None:
        self.reset_calls += 1


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
    existing_directories: set[str] | None = None

    def __post_init__(self) -> None:
        if self.existing_directories is None:
            self.existing_directories = set()
            for remote_path in self.listing:
                current_path = remote_path
                while current_path and current_path != "/":
                    self.existing_directories.add(current_path)
                    current_path = current_path.rsplit("/", 1)[0] or "/"
                self.existing_directories.add("/")

    def connect(self, *, host: str, port: int, timeout: int) -> None:
        self.actions.append(f"connect:{host}:{port}:{timeout}")

    def login(self, *, user: str, passwd: str) -> None:
        self.actions.append(f"login:{user}:{passwd}")

    def cwd(self, remote_path: str) -> None:
        self.actions.append(f"cwd:{remote_path}")
        if self.existing_directories is None or remote_path not in self.existing_directories:
            msg = f"missing directory {remote_path}"
            raise OSError(msg)

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

    def mkd(self, remote_path: str) -> str:
        self.actions.append(f"mkd:{remote_path}")
        if self.existing_directories is None:
            self.existing_directories = set()
        self.existing_directories.add(remote_path)
        return remote_path

    def storbinary(self, command: str, payload: Any) -> str:
        self.actions.append(f"storbinary:{command}")
        remote_path = command.replace("STOR ", "", 1)
        self.file_bytes[remote_path] = cast(bytes, payload.read())
        return "226 Transfer complete"

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


def test_base_remote_session_rejects_invalid_retry_attempts() -> None:
    with pytest.raises(ValueError, match="max_connect_attempts must be a positive integer"):
        _ControlledBaseSession(_build_ssh_config(), max_connect_attempts=0)


def test_base_remote_session_retries_retryable_connect_failures() -> None:
    session = _ControlledBaseSession(
        _build_ssh_config(),
        connect_errors=[
            RemoteConnectionOperationError(
                error_code="connection_timeout",
                message="timed out",
            )
        ],
    )

    remote_files = list(session.iter_remote_files())

    assert [remote_file.relative_path for remote_file in remote_files] == ["messages.po"]
    assert session.connect_calls == 2
    assert session.reset_calls == 1
    assert session.state is RemoteConnectionSessionState.OPEN


def test_base_remote_session_close_is_noop_before_open() -> None:
    session = _ControlledBaseSession(_build_ssh_config())

    session.close()

    assert session.close_calls == 0
    assert session.state is RemoteConnectionSessionState.CLOSED


def test_base_remote_session_exhausts_retryable_connect_failures() -> None:
    session = _ControlledBaseSession(
        _build_ssh_config(),
        connect_errors=[
            RemoteConnectionOperationError(
                error_code="connection_timeout",
                message="first timeout",
            ),
            RemoteConnectionOperationError(
                error_code="connection_timeout",
                message="second timeout",
            ),
        ],
    )

    with pytest.raises(RemoteConnectionOperationError, match="second timeout"):
        list(session.iter_remote_files())

    assert session.connect_calls == 2
    assert session.reset_calls == 2
    assert session.state is RemoteConnectionSessionState.FAILED


def test_base_remote_session_fails_without_retry_for_non_retryable_connect_errors() -> None:
    session = _ControlledBaseSession(
        _build_ssh_config(),
        connect_errors=[
            RemoteConnectionOperationError(
                error_code="authentication_failed",
                message="auth failed",
            )
        ],
    )

    with pytest.raises(RemoteConnectionOperationError, match="auth failed"):
        list(session.iter_remote_files())

    assert session.connect_calls == 1
    assert session.reset_calls == 1
    assert session.state is RemoteConnectionSessionState.FAILED
    with pytest.raises(RemoteConnectionOperationError, match="Remote session is in a failed state"):
        session.download_file("/srv/app/messages.po")


def test_base_remote_session_marks_failed_when_close_fails() -> None:
    session = _ControlledBaseSession(
        _build_ssh_config(),
        close_error=RemoteConnectionOperationError(
            error_code="close_failed",
            message="close failed",
        ),
    )
    session.download_file("/srv/app/messages.po")

    with pytest.raises(RemoteConnectionOperationError, match="close failed"):
        session.close()

    assert session.close_calls == 1
    assert session.state is RemoteConnectionSessionState.FAILED


def test_base_remote_provider_materializes_a_bounded_remote_file_list() -> None:
    class _IteratorBackedProvider(BaseRemoteConnectionProvider):
        descriptor = RemoteConnectionTypeDescriptor(
            connection_type="sftp",
            display_name="SFTP",
            default_port=22,
        )

        def test_connection(
            self,
            config: RemoteConnectionConfigInput,
        ) -> RemoteConnectionTestResult:
            return RemoteConnectionTestResult(
                success=True,
                connection_type=config.connection_type,
                host=config.host,
                port=config.port,
                message="ok",
                error_code=None,
            )

        def __init__(self) -> None:
            self.session = _ListBackedSession(
                files=[
                    RemoteSyncFile(
                        remote_path="/srv/app/messages-1.po",
                        relative_path="messages-1.po",
                        size_bytes=8,
                    ),
                    RemoteSyncFile(
                        remote_path="/srv/app/messages-2.po",
                        relative_path="messages-2.po",
                        size_bytes=8,
                    ),
                    RemoteSyncFile(
                        remote_path="/srv/app/messages-3.po",
                        relative_path="messages-3.po",
                        size_bytes=8,
                    ),
                ]
            )

        def open_session(self, config: RemoteConnectionConfig) -> _ListBackedSession:
            return self.session

    provider = _IteratorBackedProvider()

    remote_files = provider.list_remote_files(_build_ssh_config(), max_files=2)

    assert [remote_file.relative_path for remote_file in remote_files] == [
        "messages-1.po",
        "messages-2.po",
    ]
    assert provider.session.close_calls == 1


def test_base_remote_provider_closes_the_session_when_materialization_is_truncated() -> None:
    class _IteratorBackedProvider(BaseRemoteConnectionProvider):
        descriptor = RemoteConnectionTypeDescriptor(
            connection_type="sftp",
            display_name="SFTP",
            default_port=22,
        )

        def __init__(self) -> None:
            self.session = _ListBackedSession(
                files=[
                    RemoteSyncFile(
                        remote_path="/srv/app/messages-1.po",
                        relative_path="messages-1.po",
                        size_bytes=8,
                    ),
                    RemoteSyncFile(
                        remote_path="/srv/app/messages-2.po",
                        relative_path="messages-2.po",
                        size_bytes=8,
                    ),
                ]
            )

        def test_connection(
            self,
            config: RemoteConnectionConfigInput,
        ) -> RemoteConnectionTestResult:
            return RemoteConnectionTestResult(
                success=True,
                connection_type=config.connection_type,
                host=config.host,
                port=config.port,
                message="ok",
                error_code=None,
            )

        def open_session(self, config: RemoteConnectionConfig) -> _ListBackedSession:
            return self.session

    provider = _IteratorBackedProvider()

    remote_files = provider.list_remote_files(_build_ssh_config(), max_files=1)

    assert [remote_file.relative_path for remote_file in remote_files] == ["messages-1.po"]
    assert provider.session.close_calls == 1
    assert provider.session.state is RemoteConnectionSessionState.CLOSED


def test_base_remote_provider_iter_remote_files_closes_the_session() -> None:
    class _IteratorBackedProvider(BaseRemoteConnectionProvider):
        descriptor = RemoteConnectionTypeDescriptor(
            connection_type="sftp",
            display_name="SFTP",
            default_port=22,
        )

        def __init__(self) -> None:
            self.session = _ListBackedSession(
                files=[
                    RemoteSyncFile(
                        remote_path="/srv/app/messages.po",
                        relative_path="messages.po",
                        size_bytes=8,
                    )
                ]
            )

        def test_connection(
            self,
            config: RemoteConnectionConfigInput,
        ) -> RemoteConnectionTestResult:
            return RemoteConnectionTestResult(
                success=True,
                connection_type=config.connection_type,
                host=config.host,
                port=config.port,
                message="ok",
                error_code=None,
            )

        def open_session(self, config: RemoteConnectionConfig) -> _ListBackedSession:
            return self.session

    provider = _IteratorBackedProvider()

    remote_files = list(provider.iter_remote_files(_build_ssh_config()))

    assert [remote_file.relative_path for remote_file in remote_files] == ["messages.po"]
    assert provider.session.close_calls == 1


def test_base_remote_provider_rejects_non_positive_materialization_limits() -> None:
    class _IteratorBackedProvider(BaseRemoteConnectionProvider):
        descriptor = RemoteConnectionTypeDescriptor(
            connection_type="sftp",
            display_name="SFTP",
            default_port=22,
        )

        def test_connection(
            self,
            config: RemoteConnectionConfigInput,
        ) -> RemoteConnectionTestResult:
            return RemoteConnectionTestResult(
                success=True,
                connection_type=config.connection_type,
                host=config.host,
                port=config.port,
                message="ok",
                error_code=None,
            )

        def open_session(self, config: RemoteConnectionConfig) -> _ListBackedSession:
            return _ListBackedSession(
                files=[
                    RemoteSyncFile(
                        remote_path="/srv/app/messages.po",
                        relative_path="messages.po",
                        size_bytes=8,
                    )
                ]
            )

    provider = _IteratorBackedProvider()

    with pytest.raises(ValueError, match="max_files must be a positive integer"):
        provider.list_remote_files(_build_ssh_config(), max_files=0)


def test_ftp_provider_reuses_one_session_for_listing_and_multiple_downloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actions: list[str] = []
    fake_client = _FakeFtpClient(
        actions=actions,
        listing={
            "/srv/app": [
                ("messages.po", {"type": "file", "size": "8"}),
                ("theme.po", {"type": "file", "size": "10"}),
            ],
        },
        file_bytes={
            "/srv/app/messages.po": b"messages",
            "/srv/app/theme.po": b"theme",
        },
    )
    provider = ftp.FTPRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)

    session = provider.open_session(_build_ftp_config())
    remote_files = list(session.iter_remote_files())
    payloads = [session.download_file(remote_file.remote_path) for remote_file in remote_files]
    session.close()

    assert [remote_file.relative_path for remote_file in remote_files] == [
        "messages.po",
        "theme.po",
    ]
    assert payloads == [b"messages", b"theme"]
    assert actions == [
        "connect:example.test:21:10",
        "login:deploy:secret",
        "mlsd:/srv/app",
        "retrbinary:RETR /srv/app/messages.po",
        "retrbinary:RETR /srv/app/theme.po",
        "quit",
    ]


def test_ftp_session_wraps_connect_failures_and_resets_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients = [
        _FakeFtpClient(actions=[], listing={}, file_bytes={}),
        _FakeFtpClient(actions=[], listing={}, file_bytes={}),
    ]

    def _failing_connect(
        client: Any,
        config: RemoteConnectionConfig | RemoteConnectionConfigInput,
    ) -> None:
        msg = "login failed"
        raise OSError(msg)

    provider = ftp.FTPRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: clients.pop(0))
    session = ftp._FtpRemoteConnectionSession(
        config=_build_ftp_config(),
        client_factory=provider._build_client,
        connect_fn=_failing_connect,
        connect_error_code="ftp_connection_failed",
        transport_label="FTP",
    )

    with pytest.raises(RemoteConnectionOperationError, match="login failed") as error:
        list(session.iter_remote_files())

    assert error.value.error_code == "authentication_failed"


def test_ftp_normalizes_empty_error_messages_to_default_code() -> None:
    error = ftp._normalize_ftp_error(OSError(), default_code="download_failed")

    assert error.error_code == "download_failed"
    assert str(error) == "download failed"


def test_sftp_provider_reuses_one_session_for_listing_and_multiple_downloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sftp_client = _FakeSftpClient(
        listing={
            "/srv/app": [
                _FakeSftpEntry("messages.po", 0o100644, 8),
                _FakeSftpEntry("theme.po", 0o100644, 5),
            ],
        },
        file_bytes={
            "/srv/app/messages.po": b"messages",
            "/srv/app/theme.po": b"theme",
        },
    )
    ssh_client = _FakeSshClient(sftp_client)
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)
    provider = ssh.SFTPRemoteConnectionProvider()

    session = provider.open_session(_build_ssh_config())
    remote_files = list(session.iter_remote_files())
    payloads = [session.download_file(remote_file.remote_path) for remote_file in remote_files]
    session.close()

    assert [remote_file.relative_path for remote_file in remote_files] == [
        "messages.po",
        "theme.po",
    ]
    assert payloads == [b"messages", b"theme"]
    assert sftp_client.actions == [
        "listdir_attr:/srv/app",
        "file:/srv/app/messages.po:rb",
        "file:/srv/app/theme.po:rb",
        "sftp_close",
    ]
    assert ssh_client.actions == [
        "open_sftp",
        "ssh_close",
    ]


def test_sftp_provider_creates_remote_directories_and_uploads_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sftp_client = _FakeSftpClient(
        listing={"/srv/app": []},
        file_bytes={},
    )
    ssh_client = _FakeSshClient(sftp_client)
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)
    provider = ssh.SFTPRemoteConnectionProvider()

    directories_created = provider.ensure_remote_directory(
        _build_ssh_config(),
        "/srv/app/locale/es",
    )
    provider.upload_file(
        _build_ssh_config(),
        "/srv/app/locale/es/messages.po",
        b'msgid "hola"\n',
    )

    assert directories_created == 2
    assert sftp_client._file_bytes["/srv/app/locale/es/messages.po"] == b'msgid "hola"\n'
    assert "mkdir:/srv/app/locale" in sftp_client.actions
    assert "mkdir:/srv/app/locale/es" in sftp_client.actions
    assert "file:/srv/app/locale/es/messages.po:wb" in sftp_client.actions


def test_sftp_session_wraps_open_sftp_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    class _OpenSftpFailingSshClient(_FakeSshClient):
        def open_sftp(self) -> _FakeSftpClient:
            msg = "Broken pipe"
            raise OSError(msg)

    ssh_client = _OpenSftpFailingSshClient(_FakeSftpClient(listing={}, file_bytes={}))
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)
    provider = ssh.SFTPRemoteConnectionProvider()

    with pytest.raises(RemoteConnectionOperationError, match="Broken pipe") as error:
        list(provider.open_session(_build_ssh_config()).iter_remote_files())

    assert error.value.error_code == "transport_io_failed"
    assert ssh_client.actions == ["ssh_close", "ssh_close"]


def test_sftp_session_rejects_listing_without_open_client() -> None:
    session = ssh.SFTPRemoteConnectionProvider().open_session(_build_ssh_config())

    with pytest.raises(RemoteConnectionOperationError, match="SFTP client is not open"):
        list(session._iter_remote_files(None))


def test_sftp_session_rejects_download_without_open_client() -> None:
    session = ssh.SFTPRemoteConnectionProvider().open_session(_build_ssh_config())

    with pytest.raises(RemoteConnectionOperationError, match="SFTP client is not open"):
        session._download_file("/srv/app/messages.po", None)


def test_sftp_session_rejects_remote_directory_creation_without_open_client() -> None:
    session = ssh.SFTPRemoteConnectionProvider().open_session(_build_ssh_config())

    with pytest.raises(RemoteConnectionOperationError, match="SFTP client is not open"):
        session._ensure_remote_directory("/srv/app/locale", None)


def test_sftp_session_rejects_upload_without_open_client() -> None:
    session = ssh.SFTPRemoteConnectionProvider().open_session(_build_ssh_config())

    with pytest.raises(RemoteConnectionOperationError, match="SFTP client is not open"):
        session._upload_file("/srv/app/locale/es.po", b"payload", None)


def test_sftp_session_wraps_incremental_listing_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ListingFailingSftpClient(_FakeSftpClient):
        def listdir_attr(self, remote_path: str) -> list[_FakeSftpEntry]:
            msg = "No such file"
            raise OSError(msg)

    ssh_client = _FakeSshClient(_ListingFailingSftpClient(listing={}, file_bytes={}))
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)
    session = ssh.SFTPRemoteConnectionProvider().open_session(_build_ssh_config())

    with pytest.raises(RemoteConnectionOperationError, match="No such file") as error:
        list(session.iter_remote_files())

    assert error.value.error_code == "remote_path_not_found"


def test_sftp_session_wraps_incremental_download_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _DownloadFailingSftpClient(_FakeSftpClient):
        def file(self, remote_path: str, *, mode: str) -> _FakeRemoteFile:
            msg = "Broken pipe"
            raise OSError(msg)

    ssh_client = _FakeSshClient(_DownloadFailingSftpClient(listing={}, file_bytes={}))
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)
    session = ssh.SFTPRemoteConnectionProvider().open_session(_build_ssh_config())

    with pytest.raises(RemoteConnectionOperationError, match="Broken pipe") as error:
        session.download_file("/srv/app/messages.po")

    assert error.value.error_code == "transport_io_failed"


def test_ssh_close_helpers_ignore_missing_and_failing_clients() -> None:
    class _FailingCloseClient:
        def close(self) -> None:
            msg = "close failed"
            raise OSError(msg)

    class _AttributeFailingCloseClient:
        def close(self) -> None:
            msg = "close unavailable"
            raise AttributeError(msg)

    ssh._close_sftp_client(None)
    ssh._close_ssh_client(None)
    ssh._close_sftp_client(_FailingCloseClient())
    ssh._close_sftp_client(_AttributeFailingCloseClient())
    ssh._close_ssh_client(_FailingCloseClient())
    ssh._close_ssh_client(_AttributeFailingCloseClient())


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


def test_ftp_provider_creates_remote_directories_and_uploads_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actions: list[str] = []
    fake_client = _FakeFtpClient(
        actions=actions,
        listing={"/srv/app": []},
        file_bytes={},
    )
    provider = ftp.FTPRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)

    directories_created = provider.ensure_remote_directory(
        _build_ftp_config(),
        "/srv/app/locale/es",
    )
    provider.upload_file(
        _build_ftp_config(),
        "/srv/app/locale/es/messages.po",
        b'msgid "hola"\n',
    )

    assert directories_created == 2
    assert fake_client.file_bytes["/srv/app/locale/es/messages.po"] == b'msgid "hola"\n'
    assert "mkd:/srv/app/locale" in actions
    assert "mkd:/srv/app/locale/es" in actions
    assert "storbinary:STOR /srv/app/locale/es/messages.po" in actions


def test_ftp_session_returns_zero_for_root_remote_directories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeFtpClient(actions=[], listing={"/": []}, file_bytes={})
    provider = ftp.FTPRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)
    session = provider.open_session(_build_ftp_config())

    directories_created = session.ensure_remote_directory("/")

    assert directories_created == 0


def test_sftp_session_returns_zero_for_root_remote_directories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sftp_client = _FakeSftpClient(listing={"/": []}, file_bytes={})
    ssh_client = _FakeSshClient(sftp_client)
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)
    session = ssh.SFTPRemoteConnectionProvider().open_session(_build_ssh_config())

    directories_created = session.ensure_remote_directory("/")

    assert directories_created == 0


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
    class _ListingFailingFtpClient(_FakeFtpClient):
        def mlsd(self, remote_path: str) -> list[tuple[str, dict[str, str]]]:
            msg = f"listing failed for {remote_path}"
            raise OSError(msg)

    fake_client = _ListingFailingFtpClient(actions=[], listing={}, file_bytes={})
    provider = ftp.FTPRemoteConnectionProvider()
    monkeypatch.setattr(provider, "_build_client", lambda: fake_client)

    with pytest.raises(OSError, match=r"listing failed for /srv/app"):
        provider.list_remote_files(_build_ftp_config())


def test_close_ftp_client_ignores_quit_failures_from_half_open_connections() -> None:
    class _HalfOpenFtpClient:
        def quit(self) -> None:
            msg = "socket is not connected"
            raise AttributeError(msg)

        def close(self) -> None:
            return None

    ftp._close_ftp_client(cast(Any, _HalfOpenFtpClient()))


def test_close_ftp_client_ignores_close_failures_after_quit_errors() -> None:
    class _CloseFailingFtpClient:
        def quit(self) -> None:
            msg = "socket is not connected"
            raise AttributeError(msg)

        def close(self) -> None:
            msg = "close failed"
            raise OSError(msg)

    ftp._close_ftp_client(cast(Any, _CloseFailingFtpClient()))


def test_close_ftp_client_ignores_library_close_failures_after_os_errors() -> None:
    class _LibraryCloseFailingFtpClient:
        def quit(self) -> None:
            msg = "network down"
            raise OSError(msg)

        def close(self) -> None:
            msg = "close failed"
            raise EOFError(msg)

    ftp._close_ftp_client(cast(Any, _LibraryCloseFailingFtpClient()))


def test_ftp_emit_progress_ignores_missing_callbacks() -> None:
    ftp._emit_progress(None, cast(Any, object()))


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
    def __init__(
        self,
        payload: bytes = b"",
        *,
        writable: bool = False,
        on_close: Callable[[bytes], None] | None = None,
    ) -> None:
        self._payload = payload
        self._writable = writable
        self._on_close = on_close
        self.closed = False

    def read(self) -> bytes:
        return self._payload

    def write(self, payload: bytes) -> int:
        if not self._writable:
            msg = "remote file opened as read-only"
            raise OSError(msg)
        self._payload += payload
        return len(payload)

    def close(self) -> None:
        self.closed = True
        if self._on_close is not None:
            self._on_close(self._payload)


class _FakeSftpClient:
    def __init__(
        self,
        listing: dict[str, list[_FakeSftpEntry]],
        file_bytes: dict[str, bytes],
    ) -> None:
        self._listing = listing
        self._file_bytes = file_bytes
        self._directories = {"/"}
        for remote_path in listing:
            current_path = remote_path
            while current_path and current_path != "/":
                self._directories.add(current_path)
                current_path = current_path.rsplit("/", 1)[0] or "/"
        self.actions: list[str] = []

    def listdir_attr(self, remote_path: str) -> list[_FakeSftpEntry]:
        self.actions.append(f"listdir_attr:{remote_path}")
        return list(self._listing.get(remote_path, []))

    def file(self, remote_path: str, *, mode: str) -> _FakeRemoteFile:
        self.actions.append(f"file:{remote_path}:{mode}")
        if mode == "wb":
            return _FakeRemoteFile(
                writable=True,
                on_close=lambda payload: self._file_bytes.__setitem__(remote_path, payload),
            )
        return _FakeRemoteFile(self._file_bytes[remote_path])

    def chdir(self, remote_path: str) -> None:
        self.actions.append(f"chdir:{remote_path}")

    def stat(self, remote_path: str) -> _FakeSftpEntry:
        self.actions.append(f"stat:{remote_path}")
        if remote_path not in self._directories:
            msg = f"missing directory {remote_path}"
            raise OSError(msg)
        return _FakeSftpEntry(remote_path.rsplit("/", 1)[-1], 0o040755, 0)

    def mkdir(self, remote_path: str) -> None:
        self.actions.append(f"mkdir:{remote_path}")
        self._directories.add(remote_path)
        self._listing.setdefault(remote_path, [])

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


def test_sftp_provider_skips_symlinks_and_special_files_during_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sftp_client = _FakeSftpClient(
        listing={
            "/srv/app": [
                _FakeSftpEntry("messages.po", 0o100644, 8),
                _FakeSftpEntry("venv-lib64", 0o120777, 0),
                _FakeSftpEntry("socket", 0o140777, 0),
            ],
        },
        file_bytes={},
    )
    ssh_client = _FakeSshClient(sftp_client)
    progress_events: list[str] = []
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)

    remote_files = ssh.SFTPRemoteConnectionProvider().list_remote_files(
        _build_ssh_config(),
        progress_callback=lambda event: progress_events.append(event.command_text or ""),
    )

    assert [remote_file.relative_path for remote_file in remote_files] == ["messages.po"]
    assert "SFTP SKIP /srv/app/venv-lib64" in progress_events
    assert "SFTP SKIP /srv/app/socket" in progress_events


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


def test_iter_ssh_files_wraps_listing_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _ListingFailingSftpClient(_FakeSftpClient):
        def __init__(self) -> None:
            super().__init__(listing={}, file_bytes={})

        def listdir_attr(self, remote_path: str) -> list[_FakeSftpEntry]:
            msg = "No such file"
            raise OSError(msg)

    ssh_client = _FakeSshClient(_ListingFailingSftpClient())
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)

    with pytest.raises(RemoteConnectionOperationError, match="No such file") as error:
        list(ssh._iter_ssh_files(_build_ssh_config()))

    assert error.value.error_code == "remote_path_not_found"


def test_download_ssh_file_wraps_transport_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _DownloadFailingSftpClient(_FakeSftpClient):
        def __init__(self) -> None:
            super().__init__(listing={}, file_bytes={})

        def file(self, remote_path: str, *, mode: str) -> _FakeRemoteFile:
            msg = "Broken pipe"
            raise OSError(msg)

    ssh_client = _FakeSshClient(_DownloadFailingSftpClient())
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)

    with pytest.raises(
        RemoteConnectionOperationError,
        match=r"Failed to download remote file '/srv/app/messages\.po'.*Broken pipe",
    ) as error:
        ssh._download_ssh_file(_build_ssh_config(), "/srv/app/messages.po", None, "SFTP")

    assert error.value.error_code == "transport_io_failed"


def test_download_ssh_file_explains_generic_sftp_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _DownloadFailingSftpClient(_FakeSftpClient):
        def __init__(self) -> None:
            super().__init__(listing={}, file_bytes={})

        def file(self, remote_path: str, *, mode: str) -> _FakeRemoteFile:
            msg = "Failure"
            raise OSError(msg)

    ssh_client = _FakeSshClient(_DownloadFailingSftpClient())
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)

    with pytest.raises(
        RemoteConnectionOperationError,
        match=r"generic SFTP failure.*directory, symlink, special file",
    ) as error:
        ssh._download_ssh_file(_build_ssh_config(), "/srv/app/venv/lib64", None, "SCP")

    assert error.value.error_code == "download_failed"


def test_download_ssh_file_reads_and_closes_remote_file(monkeypatch: pytest.MonkeyPatch) -> None:
    sftp_client = _FakeSftpClient(
        listing={},
        file_bytes={"/srv/app/messages.po": b"payload"},
    )
    ssh_client = _FakeSshClient(sftp_client)
    monkeypatch.setattr(ssh, "_connect_ssh_client", lambda config: ssh_client)

    payload = ssh._download_ssh_file(_build_ssh_config(), "/srv/app/messages.po", None, "SFTP")

    assert payload == b"payload"
    assert sftp_client.actions == [
        "file:/srv/app/messages.po:rb",
        "sftp_close",
    ]
    assert ssh_client.actions == [
        "open_sftp",
        "ssh_close",
    ]


def test_ssh_emit_progress_ignores_missing_callbacks() -> None:
    ssh._emit_progress(None, cast(Any, object()))


def test_ssh_emit_progress_calls_callback() -> None:
    events: list[object] = []

    ssh._emit_progress(events.append, cast(Any, object()))

    assert len(events) == 1


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
