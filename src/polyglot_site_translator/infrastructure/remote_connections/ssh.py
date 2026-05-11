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
    RemoteConnectionDependencyError,
    RemoteConnectionDirectoryError,
    RemoteConnectionDownloadError,
    RemoteConnectionListingError,
    RemoteConnectionOperationError,
    RemoteConnectionTransportError,
    RemoteConnectionUploadError,
)


class SFTPRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for SFTP connectivity tests and downloads.

    Attributes:
        descriptor:
            Documented attribute exposed by this type.
    """

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.SFTP.value,
        display_name="SFTP",
        default_port=22,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Run a short-lived SFTP connectivity check.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return _test_ssh_connection(config, "Connected successfully using SFTP.")

    def open_session(
        self,
        config: RemoteConnectionConfig,
    ) -> _SshRemoteConnectionSession:
        """Build a reusable SFTP-backed remote session.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return _SshRemoteConnectionSession(config=config, transport_label="SFTP")


class SCPRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for SCP connectivity tests over SSH.

    Attributes:
        descriptor:
            Documented attribute exposed by this type.
    """

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.SCP.value,
        display_name="SCP",
        default_port=22,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Run a short-lived SCP-over-SSH connectivity check.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return _test_ssh_connection(config, "Connected successfully using SCP.")

    def open_session(
        self,
        config: RemoteConnectionConfig,
    ) -> _SshRemoteConnectionSession:
        """Build a reusable SCP-backed remote session.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return _SshRemoteConnectionSession(config=config, transport_label="SCP")


class _SshRemoteConnectionSession(BaseRemoteConnectionSession):
    """Reusable SSH-backed session for SFTP/SCP listing and downloads.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self,
        *,
        config: RemoteConnectionConfig,
        transport_label: str,
    ) -> None:
        """Initialize this object and store its runtime dependencies.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            transport_label:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(config)
        self._transport_label = transport_label
        self._ssh_client: Any | None = None
        self._sftp_client: Any | None = None

    def _connect(self, progress_callback: SyncProgressCallback | None) -> None:
        """Handle connect.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            _normalize_ssh_error:
                Raised when this callable hits the corresponding error path.
        """
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
        except _ssh_runtime_error_types() as error:
            self._reset_after_failed_connect()
            raise _normalize_ssh_error(
                error,
                default_code="ssh_connection_failed",
            ) from error

    def _iter_remote_files(
        self,
        progress_callback: SyncProgressCallback | None,
    ) -> Iterator[RemoteSyncFile]:
        """Iterate through remote files.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
            _normalize_ssh_error:
                Raised when this callable hits the corresponding error path.
        """
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
        except _ssh_runtime_error_types() as error:
            raise _normalize_ssh_error(
                error, default_code="remote_listing_failed"
            ) from error

    def _download_file(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None,
    ) -> bytes:
        """Handle download file.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
            _normalize_ssh_operation_error:
                Raised when this callable hits the corresponding error path.
        """
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
        except _ssh_runtime_error_types() as error:
            raise _normalize_ssh_operation_error(
                error,
                default_code="download_failed",
                operation="download remote file",
                remote_path=remote_path,
            ) from error

    def _ensure_remote_directory(
        self,
        remote_path: str,
        progress_callback: SyncProgressCallback | None,
    ) -> int:
        """Handle ensure remote directory.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
            _normalize_ssh_operation_error:
                Raised when this callable hits the corresponding error path.
        """
        if self._sftp_client is None:
            msg = "SFTP client is not open."
            raise RemoteConnectionOperationError(
                error_code="remote_session_not_open",
                message=msg,
            )
        normalized_path = posixpath.normpath(remote_path)
        if normalized_path == "/":
            return 0
        created_segments = 0
        current_path = ""
        for segment in [part for part in normalized_path.split("/") if part]:
            current_path = (
                f"{current_path}/{segment}" if current_path else f"/{segment}"
            )
            try:
                self._sftp_client.stat(current_path)
            except _ssh_runtime_error_types():
                try:
                    _emit_progress(
                        progress_callback,
                        SyncProgressEvent(
                            stage=SyncProgressStage.PREPARING_REMOTE,
                            message=f"Creating remote directory {current_path}.",
                            command_text=(
                                f"{self._transport_label} MKDIR {current_path}"
                            ),
                        ),
                    )
                    self._sftp_client.mkdir(current_path)
                    created_segments += 1
                except _ssh_runtime_error_types() as error:
                    raise _normalize_ssh_operation_error(
                        error,
                        default_code="remote_directory_failed",
                        operation="create remote directory",
                        remote_path=current_path,
                    ) from error
        return created_segments

    def _upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: SyncProgressCallback | None,
    ) -> None:
        """Handle upload file.

        Args:
            self:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            contents:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
            _normalize_ssh_operation_error:
                Raised when this callable hits the corresponding error path.
        """
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
                    stage=SyncProgressStage.UPLOADING_FILE,
                    message=f"Uploading local file into {remote_path}.",
                    command_text=f"{self._transport_label} PUT {remote_path}",
                ),
            )
            remote_file = self._sftp_client.file(remote_path, mode="wb")
            try:
                remote_file.write(contents)
            finally:
                remote_file.close()
        except _ssh_runtime_error_types() as error:
            raise _normalize_ssh_operation_error(
                error,
                default_code="upload_failed",
                operation="upload local file",
                remote_path=remote_path,
            ) from error

    def _close(self, progress_callback: SyncProgressCallback | None) -> None:
        """Handle close.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
        """Reset after failed connect.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        _close_sftp_client(self._sftp_client)
        _close_ssh_client(self._ssh_client)
        self._sftp_client = None
        self._ssh_client = None


def _test_ssh_connection(
    config: RemoteConnectionConfigInput,
    success_message: str,
) -> RemoteConnectionTestResult:
    """Handle test ssh connection.

    Args:
        config:
            Value supplied to this callable.
        success_message:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    ssh_client: Any | None = None
    sftp_client: Any | None = None
    try:
        ssh_client = _connect_ssh_client(config)
        sftp_client = ssh_client.open_sftp()
        sftp_client.chdir(config.remote_path)
    except RemoteConnectionDependencyError as error:
        return RemoteConnectionTestResult(
            success=False,
            connection_type=config.connection_type,
            host=config.host,
            port=config.port,
            message=str(error),
            error_code=error.error_code,
        )
    except _ssh_runtime_error_types() as error:
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
    finally:
        _close_sftp_client(sftp_client)
        _close_ssh_client(ssh_client)
    return RemoteConnectionTestResult(
        success=True,
        connection_type=config.connection_type,
        host=config.host,
        port=config.port,
        message=success_message,
        error_code=None,
    )


def _build_ssh_client() -> Any:
    """Build ssh client.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        RemoteConnectionDependencyError:
            Raised when this callable hits the corresponding error path.
    """
    try:
        paramiko = import_module("paramiko")
    except ModuleNotFoundError as error:
        msg = "Paramiko is required for SSH-based remote connections."
        raise RemoteConnectionDependencyError(
            error_code="missing_dependency",
            message=msg,
        ) from error
    return paramiko.SSHClient()


def _connect_ssh_client(
    config: RemoteConnectionConfig | RemoteConnectionConfigInput,
) -> Any:
    """Handle connect ssh client.

    Args:
        config:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        RemoteConnectionDependencyError:
            Raised when this callable hits the corresponding error path.
        _normalize_ssh_error:
            Raised when this callable hits the corresponding error path.
    """
    try:
        ssh_client = _build_ssh_client()
    except ModuleNotFoundError as error:
        msg = "Paramiko is required for SSH-based remote connections."
        raise RemoteConnectionDependencyError(
            error_code="missing_dependency",
            message=msg,
        ) from error
    ssh_exception_type: type[BaseException] = OSError
    paramiko_module: Any | None = None
    paramiko_module = _load_paramiko_module_if_available()
    if paramiko_module is not None:
        ssh_exception_type = cast(type[BaseException], paramiko_module.SSHException)
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
    except ModuleNotFoundError as error:
        ssh_client.close()
        msg = "Paramiko is required for SSH-based remote connections."
        raise RemoteConnectionDependencyError(
            error_code="missing_dependency",
            message=msg,
        ) from error
    except (OSError, TimeoutError, EOFError, ssh_exception_type) as error:
        ssh_client.close()
        raise _normalize_ssh_error(
            error, default_code="ssh_connection_failed"
        ) from error
    return ssh_client


def _load_paramiko_module_if_available() -> Any | None:
    """Load paramiko module if available.

    Returns:
        value:
            Structured value returned by this callable.
    """
    try:
        return import_module("paramiko")
    except ModuleNotFoundError:
        return None


def _ssh_runtime_error_types() -> tuple[type[BaseException], ...]:
    """Handle ssh runtime error types.

    Returns:
        value:
            Structured value returned by this callable.
    """
    paramiko_module = _load_paramiko_module_if_available()
    if paramiko_module is None:
        return (OSError, TimeoutError, EOFError)
    return (
        OSError,
        TimeoutError,
        EOFError,
        cast(type[BaseException], paramiko_module.SSHException),
    )


def _configure_host_key_policy(
    *,
    ssh_client: Any,
    config: RemoteConnectionConfig | RemoteConnectionConfigInput,
    paramiko_module: Any | None,
) -> None:
    """Handle configure host key policy.

    Args:
        ssh_client:
            Value supplied to this callable.
        config:
            Value supplied to this callable.
        paramiko_module:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    ssh_client.load_system_host_keys()
    if config.flags.verify_host:
        return
    if paramiko_module is None:
        paramiko_module = import_module("paramiko")
    known_hosts_path = _ensure_user_known_hosts_file()
    ssh_client.load_host_keys(str(known_hosts_path))
    ssh_client.set_missing_host_key_policy(paramiko_module.AutoAddPolicy())


def _ensure_user_known_hosts_file() -> Path:
    """Handle ensure user known hosts file.

    Returns:
        value:
            Structured value returned by this callable.
    """
    known_hosts_path = Path.home() / ".ssh" / "known_hosts"
    known_hosts_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    known_hosts_path.touch(mode=0o600, exist_ok=True)
    return known_hosts_path


def _iter_ssh_files(
    config: RemoteConnectionConfig,
    progress_callback: SyncProgressCallback | None = None,
) -> Iterator[RemoteSyncFile]:
    """Iterate through ssh files.

    Args:
        config:
            Value supplied to this callable.
        progress_callback:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        _normalize_ssh_error:
            Raised when this callable hits the corresponding error path.
    """
    _emit_progress(
        progress_callback,
        SyncProgressEvent(
            stage=SyncProgressStage.LISTING_REMOTE,
            message=f"Connecting to {config.host}:{config.port} for remote listing.",
            command_text=f"SSH CONNECT {config.host}:{config.port}",
        ),
    )
    ssh_client = _connect_ssh_client(config)
    try:
        sftp_client = ssh_client.open_sftp()
    except _ssh_runtime_error_types() as error:
        ssh_client.close()
        raise _normalize_ssh_error(
            error, default_code="ssh_connection_failed"
        ) from error
    try:
        normalized_root = posixpath.normpath(config.remote_path)
        yield from _walk_sftp_directory(
            sftp_client=sftp_client,
            base_remote_path=normalized_root,
            current_remote_path=normalized_root,
            progress_callback=progress_callback,
        )
    except _ssh_runtime_error_types() as error:
        raise _normalize_ssh_error(
            error, default_code="remote_listing_failed"
        ) from error
    finally:
        sftp_client.close()
        ssh_client.close()


def _download_ssh_file(
    config: RemoteConnectionConfig,
    remote_path: str,
    progress_callback: SyncProgressCallback | None,
    transport_label: str,
) -> bytes:
    """Handle download ssh file.

    Args:
        config:
            Value supplied to this callable.
        remote_path:
            Value supplied to this callable.
        progress_callback:
            Value supplied to this callable.
        transport_label:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        _normalize_ssh_error:
            Raised when this callable hits the corresponding error path.
        _normalize_ssh_operation_error:
            Raised when this callable hits the corresponding error path.
    """
    _emit_progress(
        progress_callback,
        SyncProgressEvent(
            stage=SyncProgressStage.DOWNLOADING_FILE,
            message=f"Connecting to {config.host}:{config.port} for file download.",
            command_text=f"SSH CONNECT {config.host}:{config.port}",
        ),
    )
    ssh_client = _connect_ssh_client(config)
    try:
        sftp_client = ssh_client.open_sftp()
    except _ssh_runtime_error_types() as error:
        ssh_client.close()
        raise _normalize_ssh_error(
            error, default_code="ssh_connection_failed"
        ) from error
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
    except _ssh_runtime_error_types() as error:
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
    """Close sftp client.

    Args:
        sftp_client:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if sftp_client is None:
        return
    try:
        sftp_client.close()
    except OSError:
        return
    except AttributeError:
        return


def _close_ssh_client(ssh_client: Any | None) -> None:
    """Close ssh client.

    Args:
        ssh_client:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Normalize ssh error.

    Args:
        error:
            Value supplied to this callable.
        default_code:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    elif _matches_any(
        normalized_message, ["channel", "connection reset", "broken pipe"]
    ):
        error_code = "transport_io_failed"
    error_type = _ssh_error_type_for(error_code=error_code, default_code=default_code)
    return error_type(
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
    """Normalize ssh operation error.

    Args:
        error:
            Value supplied to this callable.
        default_code:
            Value supplied to this callable.
        operation:
            Value supplied to this callable.
        remote_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    normalized_error = _normalize_ssh_error(error, default_code=default_code)
    reason = str(normalized_error).strip()
    message = f"Failed to {operation} '{remote_path}'. SSH/SFTP reported: {reason}."
    if reason.lower() == "failure":
        message = (
            f"Failed to {operation} '{remote_path}'. The server returned a "
            "generic SFTP failure without details. The path may be a "
            "directory, symlink, special file, or a file blocked by server "
            "permissions. Verify the remote path type and "
            "read permissions on the server."
        )
    error_type = _ssh_error_type_for(
        error_code=normalized_error.error_code,
        default_code=default_code,
    )
    return error_type(
        error_code=normalized_error.error_code,
        message=message,
    )


def _ssh_error_type_for(
    *,
    error_code: str,
    default_code: str,
) -> type[RemoteConnectionOperationError]:
    """Handle ssh error type for.

    Args:
        error_code:
            Value supplied to this callable.
        default_code:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    error_type: type[RemoteConnectionOperationError] = RemoteConnectionOperationError
    if error_code == "missing_dependency":
        error_type = RemoteConnectionDependencyError
    elif default_code == "remote_listing_failed":
        error_type = RemoteConnectionListingError
    elif default_code == "download_failed":
        error_type = RemoteConnectionDownloadError
    elif default_code == "remote_directory_failed":
        error_type = RemoteConnectionDirectoryError
    elif default_code == "upload_failed":
        error_type = RemoteConnectionUploadError
    elif (
        error_code
        in {
            "dns_resolution_failed",
            "connection_timeout",
            "connection_refused",
            "authentication_failed",
            "unknown_ssh_host_key",
            "host_key_failed",
            "transport_io_failed",
        }
        or default_code == "ssh_connection_failed"
    ):
        error_type = RemoteConnectionTransportError
    return error_type


def _format_connection_test_error(
    *,
    config: RemoteConnectionConfigInput,
    error: RemoteConnectionOperationError,
) -> str:
    """Format connection test error.

    Args:
        config:
            Value supplied to this callable.
        error:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return (
        f"SSH connection test failed for {config.connection_type} "
        f"{config.host}:{config.port} at remote path '{config.remote_path}'. "
        f"Cause ({error.error_code}): {error}"
    )


def _matches_any(message: str, patterns: list[str]) -> bool:
    """Handle matches any.

    Args:
        message:
            Value supplied to this callable.
        patterns:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return any(pattern in message for pattern in patterns)


def _walk_sftp_directory(
    *,
    sftp_client: Any,
    base_remote_path: str,
    current_remote_path: str,
    progress_callback: SyncProgressCallback | None = None,
) -> Iterator[RemoteSyncFile]:
    """Walk sftp directory.

    Args:
        sftp_client:
            Value supplied to this callable.
        base_remote_path:
            Value supplied to this callable.
        current_remote_path:
            Value supplied to this callable.
        progress_callback:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
                        f"Skipping remote path {remote_path} because it is not "
                        "a regular file."
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
    """Handle join remote path.

    Args:
        base_path:
            Value supplied to this callable.
        name:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if base_path == "/":
        return f"/{name}"
    return posixpath.join(base_path, name)


def _emit_progress(
    progress_callback: SyncProgressCallback | None,
    event: SyncProgressEvent,
) -> None:
    """Emit progress.

    Args:
        progress_callback:
            Value supplied to this callable.
        event:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if progress_callback is None:
        return
    progress_callback(event)
