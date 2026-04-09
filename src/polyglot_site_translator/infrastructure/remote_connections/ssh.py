"""SFTP and SCP remote connection providers."""

from __future__ import annotations

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
        return _list_ssh_files(config, progress_callback)

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
        return _list_ssh_files(config, progress_callback)

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
        raise OSError(str(error)) from error
    return ssh_client


def _list_ssh_files(
    config: RemoteConnectionConfig,
    progress_callback: SyncProgressCallback | None = None,
) -> list[RemoteSyncFile]:
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
        return _walk_sftp_directory(
            sftp_client=sftp_client,
            base_remote_path=normalized_root,
            current_remote_path=normalized_root,
            progress_callback=progress_callback,
        )
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
        sftp_client.close()
        ssh_client.close()


def _walk_sftp_directory(
    *,
    sftp_client: Any,
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
            command_text=f"SFTP LIST {current_remote_path}",
        ),
    )
    for entry in sftp_client.listdir_attr(current_remote_path):
        remote_path = _join_remote_path(current_remote_path, entry.filename)
        if stat.S_ISDIR(entry.st_mode):
            remote_files.extend(
                _walk_sftp_directory(
                    sftp_client=sftp_client,
                    base_remote_path=base_remote_path,
                    current_remote_path=remote_path,
                    progress_callback=progress_callback,
                )
            )
            continue
        remote_files.append(
            RemoteSyncFile(
                remote_path=remote_path,
                relative_path=posixpath.relpath(remote_path, base_remote_path),
                size_bytes=int(getattr(entry, "st_size", 0)),
            )
        )
    return remote_files


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
