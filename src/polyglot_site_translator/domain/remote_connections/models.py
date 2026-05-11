"""Typed models for remote connection configuration and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from polyglot_site_translator.domain.sync.scope import ProjectSyncRuleOverride

NO_REMOTE_CONNECTION_VALUE = "none"


class BuiltinRemoteConnectionType(StrEnum):
    """Builtin remote connection types supported by the application.

    Attributes:
        FTP: Documented attribute exposed by this type.
        FTPS_EXPLICIT: Documented attribute exposed by this type.
        FTPS_IMPLICIT: Documented attribute exposed by this type.
        SFTP: Documented attribute exposed by this type.
        SCP: Documented attribute exposed by this type.
    """

    FTP = "ftp"
    FTPS_EXPLICIT = "ftps_explicit"
    FTPS_IMPLICIT = "ftps_implicit"
    SFTP = "sftp"
    SCP = "scp"


class RemoteConnectionSessionState(StrEnum):
    """Lifecycle states for a reusable remote session.

    Attributes:
        CLOSED: Documented attribute exposed by this type.
        OPEN: Documented attribute exposed by this type.
        FAILED: Documented attribute exposed by this type.
    """

    CLOSED = "closed"
    OPEN = "open"
    FAILED = "failed"


@dataclass(frozen=True)
class RemoteConnectionFlags:
    """Optional remote connection flags persisted with the connection config.

    Attributes:
        passive_mode (bool): Documented attribute exposed by this type.
        verify_host (bool): Documented attribute exposed by this type.
        use_adapter_sync_filters (bool): Documented attribute exposed by this type.
        sync_rule_overrides (tuple[ProjectSyncRuleOverride, ...]): Documented attribute exposed by
    this
        type.
    """

    passive_mode: bool = True
    verify_host: bool = True
    use_adapter_sync_filters: bool = False
    sync_rule_overrides: tuple[ProjectSyncRuleOverride, ...] = ()


@dataclass(frozen=True)
class RemoteConnectionTypeDescriptor:
    """Typed descriptor surfaced to selectors and registries.

    Attributes:
        connection_type (str): Documented attribute exposed by this type.
        display_name (str): Documented attribute exposed by this type.
        default_port (int): Documented attribute exposed by this type.
    """

    connection_type: str
    display_name: str
    default_port: int


@dataclass(frozen=True)
class RemoteConnectionConfigInput:
    """Validated input payload for remote connection create/update workflows.

    Attributes:
        connection_type (str): Documented attribute exposed by this type.
        host (str): Documented attribute exposed by this type.
        port (int): Documented attribute exposed by this type.
        username (str): Documented attribute exposed by this type.
        password (str): Documented attribute exposed by this type.
        remote_path (str): Documented attribute exposed by this type.
        flags (RemoteConnectionFlags): Documented attribute exposed by this type.
    """

    connection_type: str
    host: str
    port: int
    username: str
    password: str
    remote_path: str
    flags: RemoteConnectionFlags = field(default_factory=RemoteConnectionFlags)


@dataclass(frozen=True)
class RemoteConnectionConfig:
    """Persisted remote connection linked to a site project.

    Attributes:
        id (str): Documented attribute exposed by this type.
        site_project_id (str): Documented attribute exposed by this type.
        connection_type (str): Documented attribute exposed by this type.
        host (str): Documented attribute exposed by this type.
        port (int): Documented attribute exposed by this type.
        username (str): Documented attribute exposed by this type.
        password (str): Documented attribute exposed by this type.
        remote_path (str): Documented attribute exposed by this type.
        flags (RemoteConnectionFlags): Documented attribute exposed by this type.
    """

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
    """Structured result returned by remote connection test operations.

    Attributes:
        success (bool): Documented attribute exposed by this type.
        connection_type (str): Documented attribute exposed by this type.
        host (str): Documented attribute exposed by this type.
        port (int): Documented attribute exposed by this type.
        message (str): Documented attribute exposed by this type.
        error_code (str | None): Documented attribute exposed by this type.
    """

    success: bool
    connection_type: str
    host: str
    port: int
    message: str
    error_code: str | None


def no_remote_connection_descriptor() -> RemoteConnectionTypeDescriptor:
    """Return the typed descriptor used by the UI for optional remote access.

    Returns:
        RemoteConnectionTypeDescriptor: Structured value returned by this callable.
    """
    return RemoteConnectionTypeDescriptor(
        connection_type=NO_REMOTE_CONNECTION_VALUE,
        display_name="No Remote Connection",
        default_port=0,
    )
