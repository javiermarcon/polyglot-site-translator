"""SFTP and SCP remote connection providers."""

from __future__ import annotations

from collections.abc import Iterator
from importlib import import_module
import posixpath
import stat
from typing import Any, cast

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
    RemoteConnectionOperationError,
)


class SFTPRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for SFTP connectivity tests and downloads."""

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

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> list[RemoteSyncFile]:
        return list(self.iter_remote_files(config, progress_callback))

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> Iterator[RemoteSyncFile]:
        return _iter_ssh_files(config, progress_callback)

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        return _download_ssh_file(config, remote_path, progress_callback, "SFTP")


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

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> list[RemoteSyncFile]:
        return list(self.iter_remote_files(config, progress_callback))

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: SyncProgressCallback | None = None,
    ) -> Iterator[RemoteSyncFile]:
        return _iter_ssh_files(config, progress_callback)

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: SyncProgressCallback | None = None,
    ) -> bytes:
        return _download_ssh_file(config, remote_path, progress_callback, "SCP")


def _test_ssh_connection(
    config: RemoteConnectionConfigInput,
    success_message: str,
) -> RemoteConnectionTestResult:
    try:
        ssh_client = _connect_ssh_client(config)
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
        normalized_error = _normalize_ssh_error(
            error,
            default_code="ssh_connection_failed",
        )
        return RemoteConnectionTestResult(
            success=False,
            connection_type=config.connection_type,
            host=config.host,
            port=config.port,
            message=str(normalized_error),
            error_code=normalized_error.error_code,
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


def _connect_ssh_client(
    config: RemoteConnectionConfig | RemoteConnectionConfigInput,
) -> Any:
    ssh_client = _build_ssh_client()
    ssh_exception_type: type[BaseException] = OSError
    try:
        paramiko_module = import_module("paramiko")
    except ModuleNotFoundError:
        pass
    else:
        ssh_exception_type = cast(
            type[BaseException],
            paramiko_module.SSHException,
        )
    ssh_client.load_system_host_keys()
    try:
        ssh_client.connect(
            hostname=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            timeout=10,
        )
    except (OSError, ssh_exception_type) as error:
        ssh_client.close()
        raise _normalize_ssh_error(error, default_code="ssh_connection_failed") from error
    return ssh_client


def _iter_ssh_files(
    config: RemoteConnectionConfig,
    progress_callback: SyncProgressCallback | None = None,
) -> Iterator[RemoteSyncFile]:
    _emit_progress(
        progress_callback,
        SyncProgressEvent(
            stage=SyncProgressStage.LISTING_REMOTE,
            message=f"Connecting to {config.host}:{config.port} for remote listing.",
            command_text=f"SSH CONNECT {config.host}:{config.port}",
        ),
    )
    ssh_client = _connect_ssh_client(config)
    sftp_client = ssh_client.open_sftp()
    try:
        normalized_root = posixpath.normpath(config.remote_path)
        yield from _walk_sftp_directory(
            sftp_client=sftp_client,
            base_remote_path=normalized_root,
            current_remote_path=normalized_root,
            progress_callback=progress_callback,
        )
    except OSError as error:
        raise _normalize_ssh_error(error, default_code="remote_listing_failed") from error
    finally:
        sftp_client.close()
        ssh_client.close()


def _download_ssh_file(
    config: RemoteConnectionConfig,
    remote_path: str,
    progress_callback: SyncProgressCallback | None,
    transport_label: str,
) -> bytes:
    _emit_progress(
        progress_callback,
        SyncProgressEvent(
            stage=SyncProgressStage.DOWNLOADING_FILE,
            message=f"Connecting to {config.host}:{config.port} for file download.",
            command_text=f"SSH CONNECT {config.host}:{config.port}",
        ),
    )
    ssh_client = _connect_ssh_client(config)
    sftp_client = ssh_client.open_sftp()
    try:
        _emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.DOWNLOADING_FILE,
                message=f"Downloading remote file {remote_path}.",
                command_text=f"{transport_label} GET {remote_path}",
            ),
        )
        remote_file = sftp_client.file(remote_path, mode="rb")
        try:
            return cast(bytes, remote_file.read())
        finally:
            remote_file.close()
    except OSError as error:
        raise _normalize_ssh_error(error, default_code="download_failed") from error
    finally:
        sftp_client.close()
        ssh_client.close()


def _normalize_ssh_error(
    error: BaseException,
    *,
    default_code: str,
) -> RemoteConnectionOperationError:
    error_message = str(error).strip() or default_code.replace("_", " ")
    normalized_message = error_message.lower()
    error_code = default_code
    if _matches_any(
        normalized_message,
        [
            "temporary failure in name resolution",
            "name or service not known",
            "nodename nor servname provided",
            "getaddrinfo failed",
        ],
    ):
        error_code = "dns_resolution_failed"
    elif _matches_any(normalized_message, ["timed out", "timeout"]):
        error_code = "connection_timeout"
    elif _matches_any(normalized_message, ["connection refused", "actively refused"]):
        error_code = "connection_refused"
    elif _matches_any(
        normalized_message,
        ["authentication failed", "auth failed", "permission denied", "login failed"],
    ):
        error_code = "authentication_failed"
    elif _matches_any(
        normalized_message,
        ["host key", "known_hosts", "hostkey"],
    ):
        error_code = "host_key_failed"
    elif _matches_any(
        normalized_message,
        ["no such file", "missing remote path", "not found"],
    ):
        error_code = "remote_path_not_found"
    elif _matches_any(normalized_message, ["channel", "connection reset", "broken pipe"]):
        error_code = "transport_io_failed"
    return RemoteConnectionOperationError(
        error_code=error_code,
        message=error_message,
    )


def _matches_any(message: str, patterns: list[str]) -> bool:
    return any(pattern in message for pattern in patterns)


def _walk_sftp_directory(
    *,
    sftp_client: Any,
    base_remote_path: str,
    current_remote_path: str,
    progress_callback: SyncProgressCallback | None = None,
) -> Iterator[RemoteSyncFile]:
    _emit_progress(
        progress_callback,
        SyncProgressEvent(
            stage=SyncProgressStage.LISTING_REMOTE,
            message=f"Listing remote directory {current_remote_path}.",
            command_text=f"SFTP LIST {current_remote_path}",
        ),
    )
    for entry in sftp_client.listdir_attr(current_remote_path):
        remote_path = _join_remote_path(current_remote_path, entry.filename)
        if stat.S_ISDIR(entry.st_mode):
            yield from _walk_sftp_directory(
                sftp_client=sftp_client,
                base_remote_path=base_remote_path,
                current_remote_path=remote_path,
                progress_callback=progress_callback,
            )
            continue
        yield RemoteSyncFile(
            remote_path=remote_path,
            relative_path=posixpath.relpath(remote_path, base_remote_path),
            size_bytes=int(getattr(entry, "st_size", 0)),
        )


def _join_remote_path(base_path: str, name: str) -> str:
    if base_path == "/":
        return f"/{name}"
    return posixpath.join(base_path, name)


def _emit_progress(
    progress_callback: SyncProgressCallback | None,
    event: SyncProgressEvent,
) -> None:
    if progress_callback is None:
        return
    progress_callback(event)
