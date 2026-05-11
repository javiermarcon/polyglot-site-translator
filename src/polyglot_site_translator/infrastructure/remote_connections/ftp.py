"""FTP and FTPS remote connection providers."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from ftplib import FTP, FTP_TLS, all_errors
from io import BytesIO
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
    BaseRemoteConnectionSession,
    RemoteConnectionDirectoryError,
    RemoteConnectionDownloadError,
    RemoteConnectionListingError,
    RemoteConnectionOperationError,
    RemoteConnectionTransportError,
    RemoteConnectionUploadError,
)

_ConnectFunction = Callable[
    [FTP, RemoteConnectionConfig | RemoteConnectionConfigInput],
    None,
]
_FTP_CLOSE_ERRORS = (*all_errors, AttributeError, OSError)


class FTPRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for plain FTP connectivity tests and downloads.

    Attributes:
        descriptor:
            Documented attribute exposed by this type.
    """

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.FTP.value,
        display_name="FTP",
        default_port=21,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Run a short-lived FTP connectivity check against the provided remote root.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        client = self._build_client()
        try:
            _connect_ftp_client(client, config)
            client.cwd(config.remote_path)
        except all_errors as error:
            normalized_error = _normalize_ftp_error(
                error,
                default_code="ftp_connection_failed",
            )
            return _failure_result(
                config,
                _format_connection_test_error(
                    config=config,
                    transport_label="FTP",
                    error=normalized_error,
                ),
                normalized_error.error_code,
            )
        finally:
            _close_ftp_client(client)
        return _success_result(config, "Connected successfully using FTP.")

    def open_session(
        self, config: RemoteConnectionConfig
    ) -> _FtpRemoteConnectionSession:
        """Build a reusable FTP session for multi-file sync work.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return _FtpRemoteConnectionSession(
            config=config,
            client_factory=self._build_client,
            connect_fn=_connect_ftp_client,
            connect_error_code="ftp_connection_failed",
            transport_label="FTP",
        )

    def _build_client(self) -> FTP:
        """Build client.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return FTP()


class ExplicitFTPSRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for explicit FTPS connectivity tests and downloads.

    Attributes:
        descriptor:
            Documented attribute exposed by this type.
    """

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.FTPS_EXPLICIT.value,
        display_name="FTPS Explicit",
        default_port=21,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Run a short-lived explicit FTPS connectivity check.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        client = self._build_client()
        try:
            _connect_explicit_ftps_client(client, config)
            client.cwd(config.remote_path)
        except all_errors as error:
            normalized_error = _normalize_ftp_error(
                error,
                default_code="ftps_explicit_connection_failed",
            )
            return _failure_result(
                config,
                _format_connection_test_error(
                    config=config,
                    transport_label="FTPS explicit",
                    error=normalized_error,
                ),
                normalized_error.error_code,
            )
        finally:
            _close_ftp_client(client)
        return _success_result(config, "Connected successfully using explicit FTPS.")

    def open_session(
        self, config: RemoteConnectionConfig
    ) -> _FtpRemoteConnectionSession:
        """Build a reusable explicit-FTPS session for multi-file sync work.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return _FtpRemoteConnectionSession(
            config=config,
            client_factory=self._build_client,
            connect_fn=_connect_explicit_ftps_client,
            connect_error_code="ftps_explicit_connection_failed",
            transport_label="FTPS",
        )

    def _build_client(self) -> FTP_TLS:
        """Build client.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return FTP_TLS()


class ImplicitFtpTls(FTP_TLS):
    """Minimal implicit FTPS client for connectivity checks.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def connect(
        self,
        host: str = "",
        port: int = 0,
        timeout: float | None = None,
        source_address: tuple[str, int] | None = None,
    ) -> str:
        """Open an implicit TLS socket before completing the FTP handshake.

        Args:
            self:
                Value supplied to this callable.
            host:
                Value supplied to this callable.
            port:
                Value supplied to this callable.
            timeout:
                Value supplied to this callable.
            source_address:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.host = host
        self.port = port
        if timeout is not None:
            self.timeout = int(timeout)
        self.source_address = source_address
        self.sock = socket.create_connection((host, port), timeout, source_address)
        self.af = self.sock.family
        self.sock = self.context.wrap_socket(self.sock, server_hostname=host)
        self.file = self.sock.makefile("r", encoding=self.encoding)
        return self.getresp()


class ImplicitFTPSRemoteConnectionProvider(BaseRemoteConnectionProvider):
    """Provider for implicit FTPS connectivity tests and downloads.

    Attributes:
        descriptor:
            Documented attribute exposed by this type.
    """

    descriptor = RemoteConnectionTypeDescriptor(
        connection_type=BuiltinRemoteConnectionType.FTPS_IMPLICIT.value,
        display_name="FTPS Implicit",
        default_port=990,
    )

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Run a short-lived implicit FTPS connectivity check.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        client = self._build_client()
        try:
            _connect_implicit_ftps_client(client, config)
            client.cwd(config.remote_path)
        except all_errors as error:
            normalized_error = _normalize_ftp_error(
                error,
                default_code="ftps_implicit_connection_failed",
            )
            return _failure_result(
                config,
                _format_connection_test_error(
                    config=config,
                    transport_label="FTPS implicit",
                    error=normalized_error,
                ),
                normalized_error.error_code,
            )
        finally:
            _close_ftp_client(client)
        return _success_result(config, "Connected successfully using implicit FTPS.")

    def open_session(
        self, config: RemoteConnectionConfig
    ) -> _FtpRemoteConnectionSession:
        """Build a reusable implicit-FTPS session for multi-file sync work.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return _FtpRemoteConnectionSession(
            config=config,
            client_factory=self._build_client,
            connect_fn=_connect_implicit_ftps_client,
            connect_error_code="ftps_implicit_connection_failed",
            transport_label="FTPS",
        )

    @staticmethod
    def _build_client() -> ImplicitFtpTls:
        """Build client.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return ImplicitFtpTls(context=ssl.create_default_context())


class _FtpRemoteConnectionSession(BaseRemoteConnectionSession):
    """Reusable FTP/FTPS session for listing and downloading multiple files.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self,
        *,
        config: RemoteConnectionConfig,
        client_factory: Callable[[], FTP],
        connect_fn: _ConnectFunction,
        connect_error_code: str,
        transport_label: str,
    ) -> None:
        """Initialize this object and store its runtime dependencies.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            client_factory:
                Value supplied to this callable.
            connect_fn:
                Value supplied to this callable.
            connect_error_code:
                Value supplied to this callable.
            transport_label:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        super().__init__(config)
        self._client_factory = client_factory
        self._connect_fn = connect_fn
        self._connect_error_code = connect_error_code
        self._transport_label = transport_label
        self._client = self._client_factory()

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
            _normalize_ftp_error:
                Raised when this callable hits the corresponding error path.
        """
        try:
            _emit_progress(
                progress_callback,
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message=(
                        f"Connecting to {self._config.host}:{self._config.port} "
                        "for remote sync."
                    ),
                    command_text=(
                        f"{self._transport_label} CONNECT "
                        f"{self._config.host}:{self._config.port}"
                    ),
                ),
            )
            self._connect_fn(self._client, self._config)
        except all_errors as error:
            raise _normalize_ftp_error(
                error,
                default_code=self._connect_error_code,
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
            _normalize_ftp_error:
                Raised when this callable hits the corresponding error path.
        """
        normalized_root = _normalize_remote_path(self._config.remote_path)
        try:
            yield from _walk_ftp_directory(
                client=self._client,
                base_remote_path=normalized_root,
                current_remote_path=normalized_root,
                progress_callback=progress_callback,
            )
        except RemoteConnectionListingError:
            raise
        except all_errors as error:
            raise _normalize_ftp_error(
                error,
                default_code="remote_listing_failed",
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
            _normalize_ftp_error:
                Raised when this callable hits the corresponding error path.
        """
        chunks: list[bytes] = []
        try:
            _emit_progress(
                progress_callback,
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message=f"Downloading remote file {remote_path}.",
                    command_text=f"{self._transport_label} RETR {remote_path}",
                ),
            )
            self._client.retrbinary(f"RETR {remote_path}", chunks.append)
        except all_errors as error:
            raise _normalize_ftp_error(error, default_code="download_failed") from error
        return b"".join(chunks)

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
            _normalize_ftp_error:
                Raised when this callable hits the corresponding error path.
        """
        normalized_path = _normalize_remote_path(remote_path)
        if normalized_path == "/":
            return 0
        created_segments = 0
        current_path = ""
        for segment in [part for part in normalized_path.split("/") if part]:
            current_path = (
                f"{current_path}/{segment}" if current_path else f"/{segment}"
            )
            try:
                self._client.cwd(current_path)
            except all_errors:
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
                    self._client.mkd(current_path)
                    created_segments += 1
                    self._client.cwd(current_path)
                except all_errors as error:
                    raise _normalize_ftp_error(
                        error,
                        default_code="remote_directory_failed",
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
            _normalize_ftp_error:
                Raised when this callable hits the corresponding error path.
        """
        try:
            _emit_progress(
                progress_callback,
                SyncProgressEvent(
                    stage=SyncProgressStage.UPLOADING_FILE,
                    message=f"Uploading local file into {remote_path}.",
                    command_text=f"{self._transport_label} STOR {remote_path}",
                ),
            )
            self._client.storbinary(f"STOR {remote_path}", BytesIO(contents))
        except all_errors as error:
            raise _normalize_ftp_error(error, default_code="upload_failed") from error

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
                message=f"Closing {self._transport_label} remote sync session.",
                command_text=(
                    f"{self._transport_label} CLOSE "
                    f"{self._config.host}:{self._config.port}"
                ),
            ),
        )
        _close_ftp_client(self._client)

    def _reset_after_failed_connect(self) -> None:
        """Reset after failed connect.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        _close_ftp_client(self._client)
        self._client = self._client_factory()


def _connect_ftp_client(
    client: FTP,
    config: RemoteConnectionConfig | RemoteConnectionConfigInput,
) -> None:
    """Handle connect ftp client.

    Args:
        client:
            Value supplied to this callable.
        config:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    client.connect(host=config.host, port=config.port, timeout=10)
    client.login(user=config.username, passwd=config.password)


def _connect_explicit_ftps_client(
    client: FTP,
    config: RemoteConnectionConfig | RemoteConnectionConfigInput,
) -> None:
    """Handle connect explicit ftps client.

    Args:
        client:
            Value supplied to this callable.
        config:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_client = cast(FTP_TLS, client)
    typed_client.connect(host=config.host, port=config.port, timeout=10)
    typed_client.auth()
    typed_client.login(user=config.username, passwd=config.password)
    typed_client.prot_p()


def _connect_implicit_ftps_client(
    client: FTP,
    config: RemoteConnectionConfig | RemoteConnectionConfigInput,
) -> None:
    """Handle connect implicit ftps client.

    Args:
        client:
            Value supplied to this callable.
        config:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_client = cast(ImplicitFtpTls, client)
    typed_client.connect(host=config.host, port=config.port, timeout=10)
    typed_client.login(user=config.username, passwd=config.password)
    typed_client.prot_p()


def _walk_ftp_directory(
    *,
    client: FTP,
    base_remote_path: str,
    current_remote_path: str,
    progress_callback: SyncProgressCallback | None = None,
) -> Iterator[RemoteSyncFile]:
    """Walk ftp directory.

    Args:
        client:
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

    Raises:
        RemoteConnectionListingError:
            Raised when this callable hits the corresponding error path.
    """
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
            yield from _walk_ftp_directory(
                client=client,
                base_remote_path=base_remote_path,
                current_remote_path=remote_path,
                progress_callback=progress_callback,
            )
            continue
        if facts.get("type") != "file":
            continue
        try:
            size_bytes = int(facts.get("size", "0"))
        except ValueError as error:
            msg = (
                f"FTP remote listing returned an invalid size for '{remote_path}': "
                f"{facts.get('size')!r}."
            )
            raise RemoteConnectionListingError(
                error_code="remote_listing_malformed",
                message=msg,
            ) from error
        yield RemoteSyncFile(
            remote_path=remote_path,
            relative_path=posixpath.relpath(remote_path, base_remote_path),
            size_bytes=size_bytes,
        )


def _normalize_remote_path(remote_path: str) -> str:
    """Normalize remote path.

    Args:
        remote_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    normalized_path = posixpath.normpath(remote_path)
    if normalized_path == ".":
        return "/"
    return normalized_path


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


def _close_ftp_client(client: FTP) -> None:
    """Close ftp client.

    Args:
        client:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    try:
        client.quit()
    except all_errors:
        _close_ftp_socket(client)
    except AttributeError:
        _close_ftp_socket(client)
    except OSError:
        _close_ftp_socket(client)


def _close_ftp_socket(client: FTP) -> None:
    """Close ftp socket.

    Args:
        client:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    try:
        client.close()
    except all_errors:
        return
    except AttributeError:
        return
    except OSError:
        return


def _normalize_ftp_error(
    error: BaseException,
    *,
    default_code: str,
) -> RemoteConnectionOperationError:
    """Normalize ftp error.

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
        ["530", "login failed", "authentication failed", "not logged in"],
    ):
        error_code = "authentication_failed"
    elif _matches_any(
        normalized_message,
        [
            "cwd failed",
            "can't cwd",
            "failed to change directory",
            "no such file",
            "not found",
            "missing remote path",
        ],
    ):
        error_code = "remote_path_not_found"
    elif _matches_any(
        normalized_message,
        ["ssl", "tls", "certificate", "handshake", "prot_p", "auth failed"],
    ):
        error_code = "tls_handshake_failed"
    elif "permission denied" in normalized_message:
        error_code = "remote_permission_denied"
    error_type = _ftp_error_type_for(error_code=error_code, default_code=default_code)
    return error_type(
        error_code=error_code,
        message=error_message,
    )


def _ftp_error_type_for(
    *,
    error_code: str,
    default_code: str,
) -> type[RemoteConnectionOperationError]:
    """Handle ftp error type for.

    Args:
        error_code:
            Value supplied to this callable.
        default_code:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if error_code in {
        "dns_resolution_failed",
        "connection_timeout",
        "connection_refused",
        "authentication_failed",
        "tls_handshake_failed",
    } or default_code.endswith("_connection_failed"):
        return RemoteConnectionTransportError
    if default_code == "remote_listing_failed":
        return RemoteConnectionListingError
    if default_code == "download_failed":
        return RemoteConnectionDownloadError
    if default_code == "remote_directory_failed":
        return RemoteConnectionDirectoryError
    if default_code == "upload_failed":
        return RemoteConnectionUploadError
    return RemoteConnectionOperationError


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


def _success_result(
    config: RemoteConnectionConfigInput,
    message: str,
) -> RemoteConnectionTestResult:
    """Handle success result.

    Args:
        config:
            Value supplied to this callable.
        message:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
    """Handle failure result.

    Args:
        config:
            Value supplied to this callable.
        message:
            Value supplied to this callable.
        error_code:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return RemoteConnectionTestResult(
        success=False,
        connection_type=config.connection_type,
        host=config.host,
        port=config.port,
        message=message,
        error_code=error_code,
    )


def _format_connection_test_error(
    *,
    config: RemoteConnectionConfigInput,
    transport_label: str,
    error: RemoteConnectionOperationError,
) -> str:
    """Format connection test error.

    Args:
        config:
            Value supplied to this callable.
        transport_label:
            Value supplied to this callable.
        error:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return (
        f"{transport_label} connection test failed for {config.connection_type} "
        f"{config.host}:{config.port} at remote path '{config.remote_path}'. "
        f"Cause ({error.error_code}): {error}"
    )


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
