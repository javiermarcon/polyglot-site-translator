"""Typed models for remote connection configuration and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

NO_REMOTE_CONNECTION_VALUE = "none"


class BuiltinRemoteConnectionType(StrEnum):
    """Builtin remote connection types supported by the application."""

    FTP = "ftp"
    FTPS_EXPLICIT = "ftps_explicit"
    FTPS_IMPLICIT = "ftps_implicit"
    SFTP = "sftp"
    SCP = "scp"


@dataclass(frozen=True)
class RemoteConnectionFlags:
    """Optional remote connection flags persisted with the connection config."""

    passive_mode: bool = True
    verify_host: bool = True


@dataclass(frozen=True)
class RemoteConnectionTypeDescriptor:
    """Typed descriptor surfaced to selectors and registries."""

    connection_type: str
    display_name: str
    default_port: int


@dataclass(frozen=True)
class RemoteConnectionConfigInput:
    """Validated input payload for remote connection create/update workflows."""

    connection_type: str
    host: str
    port: int
    username: str
    password: str
    remote_path: str
    flags: RemoteConnectionFlags = field(default_factory=RemoteConnectionFlags)


@dataclass(frozen=True)
class RemoteConnectionConfig:
    """Persisted remote connection linked to a site project."""

    id: str
    site_project_id: str
    connection_type: str
    host: str
    port: int
    username: str
    password: str
    remote_path: str
    flags: RemoteConnectionFlags = field(default_factory=RemoteConnectionFlags)


@dataclass(frozen=True)
class RemoteConnectionTestResult:
    """Structured result returned by remote connection test operations."""

    success: bool
    connection_type: str
    host: str
    port: int
    message: str
    error_code: str | None


def no_remote_connection_descriptor() -> RemoteConnectionTypeDescriptor:
    """Return the typed descriptor used by the UI for optional remote access."""
    return RemoteConnectionTypeDescriptor(
        connection_type=NO_REMOTE_CONNECTION_VALUE,
        display_name="No Remote Connection",
        default_port=0,
    )
