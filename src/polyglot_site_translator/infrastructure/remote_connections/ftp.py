"""FTP and FTPS remote connection providers."""

from __future__ import annotations

from collections.abc import Callable
from ftplib import FTP, FTP_TLS, all_errors
import posixpath
import socket
import ssl
from typing import cast

from polyglot_site_translator.domain.remote_connections.models import (
    BuiltinRemoteConnectionType,
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import (
    RemoteSyncFile,
    SyncProgressCallback,
    SyncProgressEvent,
    SyncProgressStage,
)
from polyglot_site_translator.infrastructure.remote_connections.base import (
    BaseRemoteConnectionProvider,
)

_ConnectFunction = Callable[
    [FTP, RemoteConnectionConfig | RemoteConnectionConfigInput],
    None,
]


class FTPRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for plain FTP connectivity tests and downloads."""

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.FTP.value,
        display_name="FTP",
        default_port=21,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        client = self._build_client()
        try:
            _connect_ftp_client(client, config)
            client.cwd(config.remote_path)
        except all_errors as error:
            return _failure_result(config, str(error), "ftp_connection_failed")
        finally:
            _close_ftp_client(client)
        return _success_result(config, "Connected successfully using FTP.")

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> list[RemoteSyncFile]:
        return _list_ftp_files(
            config=config,
            client=self._build_client(),
            progress_callback=progress_callback,
        )

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        return _download_ftp_file(
            config=config,
            client=self._build_client(),
            remote_path=remote_path,
            progress_callback=progress_callback,
        )

    def _build_client(self) -> FTP:
        return FTP()


class ExplicitFTPSRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for explicit FTPS connectivity tests and downloads."""

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.FTPS_EXPLICIT.value,
        display_name="FTPS Explicit",
        default_port=21,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        client = self._build_client()
        try:
            _connect_explicit_ftps_client(client, config)
            client.cwd(config.remote_path)
        except all_errors as error:
            return _failure_result(config, str(error), "ftps_explicit_connection_failed")
        finally:
            _close_ftp_client(client)
        return _success_result(config, "Connected successfully using explicit FTPS.")

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> list[RemoteSyncFile]:
        return _list_ftp_files(
            config=config,
            client=self._build_client(),
            connect_fn=_connect_explicit_ftps_client,
            progress_callback=progress_callback,
        )

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        return _download_ftp_file(
            config=config,
            client=self._build_client(),
            remote_path=remote_path,
            connect_fn=_connect_explicit_ftps_client,
            progress_callback=progress_callback,
        )

    def _build_client(self) -> FTP_TLS:
        return FTP_TLS()


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
    """Provider for implicit FTPS connectivity tests and downloads."""

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.FTPS_IMPLICIT.value,
        display_name="FTPS Implicit",
        default_port=990,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        client = self._build_client()
        try:
            _connect_implicit_ftps_client(client, config)
            client.cwd(config.remote_path)
        except all_errors as error:
            return _failure_result(config, str(error), "ftps_implicit_connection_failed")
        finally:
            _close_ftp_client(client)
        return _success_result(config, "Connected successfully using implicit FTPS.")

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> list[RemoteSyncFile]:
        return _list_ftp_files(
            config=config,
            client=self._build_client(),
            connect_fn=_connect_implicit_ftps_client,
            progress_callback=progress_callback,
        )

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        return _download_ftp_file(
            config=config,
            client=self._build_client(),
            remote_path=remote_path,
            connect_fn=_connect_implicit_ftps_client,
            progress_callback=progress_callback,
        )

    def _build_client(self) -> ImplicitFtpTls:
        return ImplicitFtpTls(context=ssl.create_default_context())


def _connect_ftp_client(
    client: FTP,
    config: RemoteConnectionConfig | RemoteConnectionConfigInput,
) -> None:
    client.connect(host=config.host, port=config.port, timeout=10)
    client.login(user=config.username, passwd=config.password)


def _connect_explicit_ftps_client(
    client: FTP,
    config: RemoteConnectionConfig | RemoteConnectionConfigInput,
) -> None:
    typed_client = cast(FTP_TLS, client)
    typed_client.connect(host=config.host, port=config.port, timeout=10)
    typed_client.auth()
    typed_client.login(user=config.username, passwd=config.password)
    typed_client.prot_p()


def _connect_implicit_ftps_client(
    client: FTP,
    config: RemoteConnectionConfig | RemoteConnectionConfigInput,
) -> None:
    typed_client = cast(ImplicitFtpTls, client)
    typed_client.connect(host=config.host, port=config.port, timeout=10)
    typed_client.login(user=config.username, passwd=config.password)
    typed_client.prot_p()


def _list_ftp_files(
    *,
    config: RemoteConnectionConfig,
    client: FTP,
    connect_fn: _ConnectFunction = _connect_ftp_client,
    progress_callback: SyncProgressCallback | None = None,
) -> list[RemoteSyncFile]:
    try:
        _emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.LISTING_REMOTE,
                message=f"Connecting to {config.host}:{config.port} for remote listing.",
                command_text=f"FTP CONNECT {config.host}:{config.port}",
            ),
        )
        connect_fn(client, config)
        normalized_root = _normalize_remote_path(config.remote_path)
        return _walk_ftp_directory(
            client=client,
            base_remote_path=normalized_root,
            current_remote_path=normalized_root,
            progress_callback=progress_callback,
        )
    except all_errors as error:
        raise OSError(str(error)) from error
    finally:
        _close_ftp_client(client)


def _download_ftp_file(
    *,
    config: RemoteConnectionConfig,
    client: FTP,
    remote_path: str,
    connect_fn: _ConnectFunction = _connect_ftp_client,
    progress_callback: SyncProgressCallback | None = None,
) -> bytes:
    chunks: list[bytes] = []
    try:
        _emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.DOWNLOADING_FILE,
                message=f"Connecting to {config.host}:{config.port} for file download.",
                command_text=f"FTP CONNECT {config.host}:{config.port}",
            ),
        )
        connect_fn(client, config)
        _emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.DOWNLOADING_FILE,
                message=f"Downloading remote file {remote_path}.",
                command_text=f"FTP RETR {remote_path}",
            ),
        )
        client.retrbinary(f"RETR {remote_path}", chunks.append)
    except all_errors as error:
        raise OSError(str(error)) from error
    finally:
        _close_ftp_client(client)
    return b"".join(chunks)


def _walk_ftp_directory(
    *,
    client: FTP,
    base_remote_path: str,
    current_remote_path: str,
    progress_callback: SyncProgressCallback | None = None,
) -> list[RemoteSyncFile]:
    remote_files: list[RemoteSyncFile] = []
    _emit_progress(
        progress_callback,
        SyncProgressEvent(
            stage=SyncProgressStage.LISTING_REMOTE,
            message=f"Listing remote directory {current_remote_path}.",
            command_text=f"FTP MLSD {current_remote_path}",
        ),
    )
    for name, facts in client.mlsd(current_remote_path):
        if name in {".", ".."}:
            continue
        remote_path = _join_remote_path(current_remote_path, name)
        if facts.get("type") == "dir":
            remote_files.extend(
                _walk_ftp_directory(
                    client=client,
                    base_remote_path=base_remote_path,
                    current_remote_path=remote_path,
                    progress_callback=progress_callback,
                )
            )
            continue
        if facts.get("type") != "file":
            continue
        remote_files.append(
            RemoteSyncFile(
                remote_path=remote_path,
                relative_path=posixpath.relpath(remote_path, base_remote_path),
                size_bytes=int(facts.get("size", "0")),
            )
        )
    return remote_files


def _normalize_remote_path(remote_path: str) -> str:
    normalized_path = posixpath.normpath(remote_path)
    if normalized_path == ".":
        return "/"
    return normalized_path


def _join_remote_path(base_path: str, name: str) -> str:
    if base_path == "/":
        return f"/{name}"
    return posixpath.join(base_path, name)


def _close_ftp_client(client: FTP) -> None:
    try:
        client.quit()
    except all_errors:
        client.close()


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


def _emit_progress(
    progress_callback: SyncProgressCallback | None,
    event: SyncProgressEvent,
) -> None:
    if progress_callback is None:
        return
    progress_callback(event)
