"""SFTP and SCP remote connection providers."""

from __future__ import annotations

from collections.abc import Iterator
from importlib import import_module
from pathlib import Path
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
    BaseRemoteConnectionSession,
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

    def open_session(
        self,
        config: RemoteConnectionConfig,
    ) -> _SshRemoteConnectionSession:
        return _SshRemoteConnectionSession(config=config, transport_label="SFTP")


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

    def open_session(
        self,
        config: RemoteConnectionConfig,
    ) -> _SshRemoteConnectionSession:
        return _SshRemoteConnectionSession(config=config, transport_label="SCP")


class _SshRemoteConnectionSession(BaseRemoteConnectionSession):
    """Reusable SSH-backed session for SFTP/SCP listing and downloads."""

    def __init__(
        self,
        *,
        config: RemoteConnectionConfig,
        transport_label: str,
    ) -> None:
        super().__init__(config)
        self._transport_label = transport_label
        self._ssh_client: Any | None = None
        self._sftp_client: Any | None = None

    def _connect(self, progress_callback: SyncProgressCallback | None) -> None:
        _emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.LISTING_REMOTE,
                message=f"Connecting to {self._config.host}:{self._config.port}.",
                command_text=f"SSH CONNECT {self._config.host}:{self._config.port}",
            ),
        )
        self._ssh_client = _connect_ssh_client(self._config)
        try:
            self._sftp_client = self._ssh_client.open_sftp()
        except OSError as error:
            self._reset_after_failed_connect()
            raise _normalize_ssh_error(
                error,
                default_code="ssh_connection_failed",
            ) from error

    def _iter_remote_files(
        self,
        progress_callback: SyncProgressCallback | None,
    ) -> Iterator[RemoteSyncFile]:
        if self._sftp_client is None:
            msg = "SFTP client is not open."
            raise RemoteConnectionOperationError(
                error_code="remote_session_not_open",
                message=msg,
            )
        try:
            normalized_root = posixpath.normpath(self._config.remote_path)
            yield from _walk_sftp_directory(
                sftp_client=self._sftp_client,
                base_remote_path=normalized_root,
                current_remote_path=normalized_root,
                progress_callback=progress_callback,
            )
        except OSError as error:
            raise _normalize_ssh_error(error, default_code="remote_listing_failed") from error

    def _download_file(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None,
    ) -> bytes:
        if self._sftp_client is None:
            msg = "SFTP client is not open."
            raise RemoteConnectionOperationError(
                error_code="remote_session_not_open",
                message=msg,
            )
        try:
            _emit_progress(
                progress_callback,
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message=f"Downloading remote file {remote_path}.",
                    command_text=f"{self._transport_label} GET {remote_path}",
                ),
            )
            remote_file = self._sftp_client.file(remote_path, mode="rb")
            try:
                return cast(bytes, remote_file.read())
            finally:
                remote_file.close()
        except OSError as error:
            raise _normalize_ssh_operation_error(
                error,
                default_code="download_failed",
                operation="download remote file",
                remote_path=remote_path,
            ) from error

    def _close(self, progress_callback: SyncProgressCallback | None) -> None:
        _emit_progress(
            progress_callback,
            SyncProgressEvent(
                stage=SyncProgressStage.DOWNLOADING_FILE,
                message="Closing SSH remote sync session.",
                command_text=f"SSH CLOSE {self._config.host}:{self._config.port}",
            ),
        )
        _close_sftp_client(self._sftp_client)
        self._sftp_client = None
        _close_ssh_client(self._ssh_client)
        self._ssh_client = None

    def _reset_after_failed_connect(self) -> None:
        _close_sftp_client(self._sftp_client)
        _close_ssh_client(self._ssh_client)
        self._sftp_client = None
        self._ssh_client = None


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
            message=_format_connection_test_error(
                config=config,
                error=normalized_error,
            ),
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
    paramiko_module: Any | None = None
    try:
        paramiko_module = import_module("paramiko")
    except ModuleNotFoundError:
        pass
    else:
        ssh_exception_type = cast(
            type[BaseException],
            paramiko_module.SSHException,
        )
    try:
        _configure_host_key_policy(
            ssh_client=ssh_client,
            config=config,
            paramiko_module=paramiko_module,
        )
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


def _configure_host_key_policy(
    *,
    ssh_client: Any,
    config: RemoteConnectionConfig | RemoteConnectionConfigInput,
    paramiko_module: Any | None,
) -> None:
    ssh_client.load_system_host_keys()
    if config.flags.verify_host:
        return
    if paramiko_module is None:
        paramiko_module = import_module("paramiko")
    known_hosts_path = _ensure_user_known_hosts_file()
    ssh_client.load_host_keys(str(known_hosts_path))
    ssh_client.set_missing_host_key_policy(paramiko_module.AutoAddPolicy())


def _ensure_user_known_hosts_file() -> Path:
    known_hosts_path = Path.home() / ".ssh" / "known_hosts"
    known_hosts_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    known_hosts_path.touch(mode=0o600, exist_ok=True)
    return known_hosts_path


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
        raise _normalize_ssh_operation_error(
            error,
            default_code="download_failed",
            operation="download remote file",
            remote_path=remote_path,
        ) from error
    finally:
        sftp_client.close()
        ssh_client.close()


def _close_sftp_client(sftp_client: Any | None) -> None:
    if sftp_client is None:
        return
    try:
        sftp_client.close()
    except OSError:
        return
    except AttributeError:
        return


def _close_ssh_client(ssh_client: Any | None) -> None:
    if ssh_client is None:
        return
    try:
        ssh_client.close()
    except OSError:
        return
    except AttributeError:
        return


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
        ["not found in known_hosts", "server not found in known_hosts"],
    ):
        error_code = "unknown_ssh_host_key"
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


def _normalize_ssh_operation_error(
    error: BaseException,
    *,
    default_code: str,
    operation: str,
    remote_path: str,
) -> RemoteConnectionOperationError:
    normalized_error = _normalize_ssh_error(error, default_code=default_code)
    reason = str(normalized_error).strip()
    message = f"Failed to {operation} '{remote_path}'. SSH/SFTP reported: {reason}."
    if reason.lower() == "failure":
        message = (
            f"Failed to {operation} '{remote_path}'. The server returned a generic SFTP "
            "failure without details. The path may be a directory, symlink, special file, "
            "or a file blocked by server permissions. Verify the remote path type and "
            "read permissions on the server."
        )
    return RemoteConnectionOperationError(
        error_code=normalized_error.error_code,
        message=message,
    )


def _format_connection_test_error(
    *,
    config: RemoteConnectionConfigInput,
    error: RemoteConnectionOperationError,
) -> str:
    return (
        f"SSH connection test failed for {config.connection_type} "
        f"{config.host}:{config.port} at remote path '{config.remote_path}'. "
        f"Cause ({error.error_code}): {error}"
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
        entry_mode = int(getattr(entry, "st_mode", 0) or 0)
        if stat.S_ISDIR(entry_mode):
            yield from _walk_sftp_directory(
                sftp_client=sftp_client,
                base_remote_path=base_remote_path,
                current_remote_path=remote_path,
                progress_callback=progress_callback,
            )
            continue
        if not stat.S_ISREG(entry_mode):
            _emit_progress(
                progress_callback,
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message=(
                        f"Skipping remote path {remote_path} because it is not a regular file."
                    ),
                    command_text=f"SFTP SKIP {remote_path}",
                ),
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
