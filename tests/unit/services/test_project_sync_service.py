"""Unit tests for project sync orchestration."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import pytest

from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionFlags,
    RemoteConnectionSessionState,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteProject,
)
from polyglot_site_translator.domain.sync.errors import SyncConfigurationError
from polyglot_site_translator.domain.sync.models import (
    LocalSyncFile,
    RemoteSyncFile,
    SyncDirection,
    SyncProgressEvent,
    SyncProgressStage,
    SyncResult,
    SyncSummary,
)
from polyglot_site_translator.domain.sync.scope import (
    ResolvedSyncRule,
    ResolvedSyncScope,
    SyncFilterSpec,
    SyncFilterType,
    SyncRuleBehavior,
    SyncRuleSource,
    SyncScopeStatus,
)
from polyglot_site_translator.infrastructure.remote_connections.base import (
    RemoteConnectionOperationError,
)
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.sync_local import LocalSyncWorkspace
import polyglot_site_translator.services.project_sync as project_sync_module
from polyglot_site_translator.services.project_sync import (
    ProjectSyncService,
    _join_remote_sync_path,
)


@dataclass
class StubFrameworkSyncScopeService:
    """Test helper for StubFrameworkSyncScopeService.

    Attributes:
        resolved_scope:
            Documented attribute exposed by this type.
        calls:
            Documented attribute exposed by this type.
    """

    resolved_scope: ResolvedSyncScope
    calls: list[str] = field(default_factory=list)

    def resolve_for_site(self, site: RegisteredSite) -> ResolvedSyncScope:
        """Handle resolve for site.

        Args:
            self:
                Value supplied to this callable.
            site:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self.calls.append(site.id)
        return self.resolved_scope


@dataclass
class FailingFrameworkSyncScopeService:
    """Test helper for FailingFrameworkSyncScopeService.

    Attributes:
        error:
            Documented attribute exposed by this type.
    """

    error: OSError | SyncConfigurationError

    def resolve_for_site(self, site: RegisteredSite) -> ResolvedSyncScope:
        """Handle resolve for site.

        Args:
            self:
                Value supplied to this callable.
            site:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            error:
                Raised when this callable hits the corresponding error path.
        """
        raise self.error


@dataclass
class StubSyncSession:
    """Test helper for StubSyncSession.

    Attributes:
        config:
            Documented attribute exposed by this type.
        provider:
            Documented attribute exposed by this type.
        state:
            Documented attribute exposed by this type.
        close_calls:
            Documented attribute exposed by this type.
        _connect_emitted:
            Documented attribute exposed by this type.
    """

    config: RemoteConnectionConfig
    provider: StubSyncProvider
    state: RemoteConnectionSessionState = RemoteConnectionSessionState.OPEN
    close_calls: int = 0
    _connect_emitted: bool = False

    def _emit_connect_if_needed(
        self,
        progress_callback: Callable[[SyncProgressEvent], None] | None,
    ) -> None:
        """Handle emit connect if needed.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if self._connect_emitted or progress_callback is None:
            return
        progress_callback(
            SyncProgressEvent(
                stage=SyncProgressStage.LISTING_REMOTE,
                message="Connecting through the sync test stub session.",
                command_text=f"SFTP CONNECT {self.config.host}:{self.config.port}",
            )
        )
        self._connect_emitted = True

    def iter_remote_files(
        self,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Handle iter remote files.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ModuleNotFoundError:
                Raised when this callable hits the corresponding error path.
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.provider.session_events.append("iter")
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message="Listing remote files through the sync test stub session.",
                    command_text=f"SFTP LIST {self.config.remote_path}",
                )
            )
        if self.provider.missing_dependency_on_list:
            msg = "paramiko"
            raise ModuleNotFoundError(msg)
        if self.provider.fail_on_list:
            msg = "Could not list remote files."
            raise OSError(msg)
        if self.provider.iter_remote_files_impl is not None:
            return self.provider.iter_remote_files_impl(self.config, progress_callback)
        return iter(self.provider.remote_files)

    def download_file(
        self,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
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
            ModuleNotFoundError:
                Raised when this callable hits the corresponding error path.
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.provider.session_events.append(f"download:{remote_path}")
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message=(
                        f"Downloading {remote_path} through the sync test stub session."
                    ),
                    command_text=f"SFTP GET {remote_path}",
                )
            )
        if self.provider.missing_dependency_on_download == remote_path:
            msg = "paramiko"
            raise ModuleNotFoundError(msg)
        if self.provider.download_file_impl is not None:
            return self.provider.download_file_impl(
                self.config,
                remote_path,
                progress_callback,
            )
        if self.provider.fail_on_download == remote_path:
            msg = f"Download failed for {remote_path}."
            raise OSError(msg)
        return self.provider.downloaded_bytes[remote_path]

    def ensure_remote_directory(
        self,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
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
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.provider.session_events.append(f"mkdir:{remote_path}")
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.PREPARING_REMOTE,
                    message=f"Preparing remote directory {remote_path}.",
                    command_text=f"SFTP MKDIR {remote_path}",
                )
            )
        if self.provider.fail_on_mkdir == remote_path:
            msg = f"Failed to create remote directory {remote_path}."
            raise OSError(msg)
        if self.provider.ensure_remote_directory_impl is not None:
            return self.provider.ensure_remote_directory_impl(
                self.config,
                remote_path,
                progress_callback,
            )
        return 1 if remote_path in self.provider.remote_directories_created else 0

    def upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
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
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        self.provider.session_events.append(f"upload:{remote_path}")
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.UPLOADING_FILE,
                    message=(
                        f"Uploading {remote_path} through the sync test stub session."
                    ),
                    command_text=f"SFTP PUT {remote_path}",
                )
            )
        if self.provider.fail_on_upload == remote_path:
            msg = f"Upload failed for {remote_path}."
            raise OSError(msg)
        if self.provider.upload_file_impl is not None:
            self.provider.upload_file_impl(
                self.config,
                remote_path,
                contents,
                progress_callback,
            )
            return
        self.provider.uploaded_bytes[remote_path] = contents

    def close(
        self,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> None:
        """Handle close.

        Args:
            self:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            close_error:
                Raised when this callable hits the corresponding error path.
        """
        self.provider.session_events.append("close")
        self.close_calls += 1
        self.state = RemoteConnectionSessionState.CLOSED
        if self.provider.close_error is not None:
            raise self.provider.close_error
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message="Closing the sync test stub session.",
                    command_text=f"SFTP CLOSE {self.config.host}:{self.config.port}",
                )
            )


@dataclass
class StubSyncProvider:
    """Test helper for StubSyncProvider.

    Attributes:
        descriptor:
            Documented attribute exposed by this type.
        remote_files:
            Documented attribute exposed by this type.
        downloaded_bytes:
            Documented attribute exposed by this type.
        fail_on_list:
            Documented attribute exposed by this type.
        fail_on_download:
            Documented attribute exposed by this type.
        missing_dependency_on_list:
            Documented attribute exposed by this type.
        missing_dependency_on_download:
            Documented attribute exposed by this type.
        fail_on_mkdir:
            Documented attribute exposed by this type.
        fail_on_upload:
            Documented attribute exposed by this type.
        iter_remote_files_impl:
            Documented attribute exposed by this type.
        download_file_impl:
            Documented attribute exposed by this type.
        ensure_remote_directory_impl:
            Documented attribute exposed by this type.
        upload_file_impl:
            Documented attribute exposed by this type.
        open_session_error:
            Documented attribute exposed by this type.
        close_error:
            Documented attribute exposed by this type.
        open_session_calls:
            Documented attribute exposed by this type.
        session_events:
            Documented attribute exposed by this type.
        opened_sessions:
            Documented attribute exposed by this type.
        uploaded_bytes:
            Documented attribute exposed by this type.
        remote_directories_created:
            Documented attribute exposed by this type.
    """

    descriptor: RemoteConnectionTypeDescriptor = field(
        default_factory=lambda: RemoteConnectionTypeDescriptor(
            connection_type="sftp",
            display_name="SFTP",
            default_port=22,
        )
    )
    remote_files: list[RemoteSyncFile] = field(default_factory=list)
    downloaded_bytes: dict[str, bytes] = field(default_factory=dict)
    fail_on_list: bool = False
    fail_on_download: str | None = None
    missing_dependency_on_list: bool = False
    missing_dependency_on_download: str | None = None
    fail_on_mkdir: str | None = None
    fail_on_upload: str | None = None
    iter_remote_files_impl: (
        Callable[
            [RemoteConnectionConfig, Callable[[SyncProgressEvent], None] | None],
            Iterable[RemoteSyncFile],
        ]
        | None
    ) = None
    download_file_impl: (
        Callable[
            [RemoteConnectionConfig, str, Callable[[SyncProgressEvent], None] | None],
            bytes,
        ]
        | None
    ) = None
    ensure_remote_directory_impl: (
        Callable[
            [RemoteConnectionConfig, str, Callable[[SyncProgressEvent], None] | None],
            int,
        ]
        | None
    ) = None
    upload_file_impl: (
        Callable[
            [
                RemoteConnectionConfig,
                str,
                bytes,
                Callable[[SyncProgressEvent], None] | None,
            ],
            None,
        ]
        | None
    ) = None
    open_session_error: RemoteConnectionOperationError | None = None
    close_error: OSError | None = None
    open_session_calls: int = 0
    session_events: list[str] = field(default_factory=list)
    opened_sessions: list[StubSyncSession] = field(default_factory=list)
    uploaded_bytes: dict[str, bytes] = field(default_factory=dict)
    remote_directories_created: set[str] = field(default_factory=set)

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        """Verify connection.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            AssertionError:
                Raised when this callable hits the corresponding error path.
        """
        msg = f"test_connection not used in this sync test for {config.connection_type}"
        raise AssertionError(msg)

    def open_session(self, config: RemoteConnectionConfig) -> StubSyncSession:
        """Handle open session.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            open_session_error:
                Raised when this callable hits the corresponding error path.
        """
        self.open_session_calls += 1
        if self.open_session_error is not None:
            raise self.open_session_error
        session = StubSyncSession(config=config, provider=self)
        self.opened_sessions.append(session)
        return session

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
        *,
        max_files: int = 1000,
    ) -> list[RemoteSyncFile]:
        """Handle list remote files.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.
            max_files:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ModuleNotFoundError:
                Raised when this callable hits the corresponding error path.
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message="Listing remote files through the sync test stub.",
                    command_text=f"SFTP LIST {config.remote_path}",
                )
            )
        if self.missing_dependency_on_list:
            msg = "paramiko"
            raise ModuleNotFoundError(msg)
        if self.fail_on_list:
            msg = "Could not list remote files."
            raise OSError(msg)
        return list(self.remote_files)[:max_files]

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Handle iter remote files.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if self.iter_remote_files_impl is not None:
            return self.iter_remote_files_impl(config, progress_callback)
        return iter(self.list_remote_files(config, progress_callback))

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> bytes:
        """Handle download file.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ModuleNotFoundError:
                Raised when this callable hits the corresponding error path.
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message=f"Downloading {remote_path} through the sync test stub.",
                    command_text=f"SFTP GET {remote_path}",
                )
            )
        if self.missing_dependency_on_download == remote_path:
            msg = "paramiko"
            raise ModuleNotFoundError(msg)
        if self.fail_on_download == remote_path:
            msg = f"Download failed for {remote_path}."
            raise OSError(msg)
        return self.downloaded_bytes[remote_path]

    def ensure_remote_directory(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> int:
        """Handle ensure remote directory.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        session = self.open_session(config)
        try:
            return session.ensure_remote_directory(remote_path, progress_callback)
        finally:
            session.close(progress_callback)

    def upload_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        contents: bytes,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> None:
        """Handle upload file.

        Args:
            self:
                Value supplied to this callable.
            config:
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
        """
        session = self.open_session(config)
        try:
            session.upload_file(remote_path, contents, progress_callback)
        finally:
            session.close(progress_callback)


_DEFAULT_REMOTE = object()


def test_project_sync_service_downloads_remote_files_into_the_local_workspace(
    tmp_path: Path,
) -> None:
    """Verify project sync service downloads remote files into the local workspace.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    provider = StubSyncProvider(
        remote_files=[
            RemoteSyncFile(
                remote_path="/srv/app/locale/es.po",
                relative_path="locale/es.po",
                size_bytes=10,
            ),
            RemoteSyncFile(
                remote_path="/srv/app/templates/home.html",
                relative_path="templates/home.html",
                size_bytes=20,
            ),
        ],
        downloaded_bytes={
            "/srv/app/locale/es.po": b'msgid "hello"\n',
            "/srv/app/templates/home.html": b"<h1>Hello</h1>\n",
        },
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_remote_to_local(_build_site(local_root=local_root))

    assert result.success is True
    assert result.summary.files_discovered == 2
    assert result.summary.files_downloaded == 2
    assert (local_root / "locale" / "es.po").read_bytes() == b'msgid "hello"\n'
    assert (local_root / "templates" / "home.html").read_bytes() == b"<h1>Hello</h1>\n"


def test_project_sync_service_reports_progress_commands_for_remote_execution(
    tmp_path: Path,
) -> None:
    """Verify project sync service reports progress commands for remote execution.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    provider = StubSyncProvider(
        remote_files=[
            RemoteSyncFile(
                remote_path="/srv/app/locale/es.po",
                relative_path="locale/es.po",
                size_bytes=10,
            )
        ],
        downloaded_bytes={"/srv/app/locale/es.po": b'msgid "hello"\n'},
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )
    events: list[SyncProgressEvent] = []

    result = service.sync_remote_to_local(
        _build_site(local_root=local_root),
        progress_callback=events.append,
    )

    assert result.success is True
    assert [
        event.command_text for event in events if event.command_text is not None
    ] == [
        f"LOCAL MKDIR {local_root}",
        "SFTP CONNECT example.test:22",
        "SFTP LIST /srv/app",
        "SFTP GET /srv/app/locale/es.po",
        f"LOCAL WRITE {local_root / 'locale' / 'es.po'}",
        "SFTP CLOSE example.test:22",
    ]
    assert events[-1].stage is SyncProgressStage.COMPLETED


def test_project_sync_service_reuses_a_single_remote_session_for_a_multi_file_sync(
    tmp_path: Path,
) -> None:
    """Verify project sync service reuses a single remote session for a multi file sync.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    provider = StubSyncProvider(
        remote_files=[
            RemoteSyncFile(
                remote_path="/srv/app/locale/es.po",
                relative_path="locale/es.po",
                size_bytes=10,
            ),
            RemoteSyncFile(
                remote_path="/srv/app/templates/home.html",
                relative_path="templates/home.html",
                size_bytes=20,
            ),
        ],
        downloaded_bytes={
            "/srv/app/locale/es.po": b'msgid "hello"\n',
            "/srv/app/templates/home.html": b"<h1>Hello</h1>\n",
        },
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_remote_to_local(_build_site(local_root=local_root))

    assert result.success is True
    assert provider.open_session_calls == 1
    assert provider.session_events == [
        "iter",
        "download:/srv/app/locale/es.po",
        "download:/srv/app/templates/home.html",
        "close",
    ]
    assert len(provider.opened_sessions) == 1
    assert provider.opened_sessions[0].state is RemoteConnectionSessionState.CLOSED
    assert provider.opened_sessions[0].close_calls == 1


def test_project_sync_service_downloads_files_while_remote_listing_is_still_in_progress(
    tmp_path: Path,
) -> None:
    """Verify project sync service downloads files while remote listing is still in.

    progress.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    provider = StubSyncProvider(
        downloaded_bytes={
            "/srv/app/locale/es.po": b'msgid "hello"\n',
            "/srv/app/templates/home.html": b"<h1>Hello</h1>\n",
        },
    )
    observed_writes: list[bool] = []

    def _iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Handle iter remote files.

        Args:
            config:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message=(
                        "Listing remote files through the streaming sync test stub."
                    ),
                    command_text=f"SFTP LIST {config.remote_path}",
                )
            )
        yield RemoteSyncFile(
            remote_path="/srv/app/locale/es.po",
            relative_path="locale/es.po",
            size_bytes=10,
        )
        observed_writes.append((local_root / "locale" / "es.po").exists())
        yield RemoteSyncFile(
            remote_path="/srv/app/templates/home.html",
            relative_path="templates/home.html",
            size_bytes=20,
        )

    provider.iter_remote_files_impl = _iter_remote_files
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_remote_to_local(_build_site(local_root=local_root))

    assert result.success is True
    assert observed_writes == [True]
    assert (local_root / "locale" / "es.po").read_bytes() == b'msgid "hello"\n'
    assert (local_root / "templates" / "home.html").read_bytes() == b"<h1>Hello</h1>\n"


def test_project_sync_service_rejects_sites_without_remote_connections(
    tmp_path: Path,
) -> None:
    """Verify project sync service rejects sites without remote connections.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        )
    )

    result = service.sync_remote_to_local(
        _build_site(local_root=tmp_path, remote_connection=None)
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "missing_remote_connection"


def test_project_sync_service_returns_success_for_empty_remote_sources(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns success for empty remote sources.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider(remote_files=[], downloaded_bytes={})]
        )
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is True
    assert result.summary.files_discovered == 0
    assert result.summary.files_downloaded == 0


def test_project_sync_service_filters_remote_to_local_sync_with_a_resolved_scope(
    tmp_path: Path,
) -> None:
    """Verify project sync service filters remote to local sync with a resolved scope.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    provider = StubSyncProvider(
        remote_files=[
            RemoteSyncFile(
                remote_path="/srv/app/locale/es.po",
                relative_path="locale/es.po",
                size_bytes=10,
            ),
            RemoteSyncFile(
                remote_path="/srv/app/templates/home.html",
                relative_path="templates/home.html",
                size_bytes=20,
            ),
        ],
        downloaded_bytes={
            "/srv/app/locale/es.po": b'msgid "hello"\n',
            "/srv/app/templates/home.html": b"<h1>Hello</h1>\n",
        },
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_remote_to_local(
        _build_site(local_root=local_root),
        resolved_scope=ResolvedSyncScope(
            framework_type="django",
            adapter_name="django_adapter",
            status=SyncScopeStatus.FILTERED,
            filters=(
                SyncFilterSpec(
                    relative_path="locale",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="Django locale catalogs.",
                ),
            ),
            message="Django sync filters were resolved.",
        ),
    )

    assert result.success is True
    assert result.summary.files_discovered == 1
    assert result.summary.files_downloaded == 1
    assert (local_root / "locale" / "es.po").exists() is True
    assert (local_root / "templates" / "home.html").exists() is False


def test_project_sync_service_filters_local_to_remote_sync_with_a_resolved_scope(
    tmp_path: Path,
) -> None:
    """Verify project sync service filters local to remote sync with a resolved scope.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "templates").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_text('msgid "hello"\n', encoding="utf-8")
    (local_root / "templates" / "home.html").write_text(
        "<h1>Hello</h1>\n", encoding="utf-8"
    )
    provider = StubSyncProvider()
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_local_to_remote(
        _build_site(local_root=local_root),
        resolved_scope=ResolvedSyncScope(
            framework_type="django",
            adapter_name="django_adapter",
            status=SyncScopeStatus.FILTERED,
            filters=(
                SyncFilterSpec(
                    relative_path="locale",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="Django locale catalogs.",
                ),
            ),
            message="Django sync filters were resolved.",
        ),
    )

    assert result.success is True
    assert result.summary.files_discovered == 1
    assert result.summary.files_uploaded == 1
    assert "/srv/app/locale/es.po" in provider.uploaded_bytes
    assert "/srv/app/templates/home.html" not in provider.uploaded_bytes


def test_project_sync_service_uses_the_persisted_filtered_sync_preference(
    tmp_path: Path,
) -> None:
    """Verify project sync service uses the persisted filtered sync preference.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    provider = StubSyncProvider(
        remote_files=[
            RemoteSyncFile(
                remote_path="/srv/app/wp-content/themes/theme/style.css",
                relative_path="wp-content/themes/theme/style.css",
                size_bytes=10,
            ),
            RemoteSyncFile(
                remote_path="/srv/app/readme.html",
                relative_path="readme.html",
                size_bytes=20,
            ),
        ],
        downloaded_bytes={
            "/srv/app/wp-content/themes/theme/style.css": b"body{}\n",
            "/srv/app/readme.html": b"readme\n",
        },
    )
    scope_service = StubFrameworkSyncScopeService(
        resolved_scope=ResolvedSyncScope(
            framework_type="wordpress",
            adapter_name="wordpress_adapter",
            status=SyncScopeStatus.FILTERED,
            filters=(
                SyncFilterSpec(
                    relative_path="wp-content/themes",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="WordPress theme sources.",
                ),
            ),
            message="WordPress sync filters were resolved.",
        )
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider]),
        framework_sync_scope_service=scope_service,
    )

    result = service.sync_remote_to_local(
        _build_site(
            local_root=local_root,
            remote_connection=RemoteConnectionConfig(
                id="remote-site-123",
                site_project_id="site-123",
                connection_type="sftp",
                host="example.test",
                port=22,
                username="deploy",
                password="secret",
                remote_path="/srv/app",
                flags=RemoteConnectionFlags(use_adapter_sync_filters=True),
            ),
        )
    )

    assert result.success is True
    assert result.summary.files_downloaded == 1
    assert scope_service.calls == ["site-123"]


def test_project_sync_service_applies_django_exclusions_during_download(
    tmp_path: Path,
) -> None:
    """Verify project sync service applies django exclusions during download.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    provider = StubSyncProvider(
        remote_files=[
            RemoteSyncFile(
                remote_path="/srv/app/locale/es.po",
                relative_path="locale/es.po",
                size_bytes=10,
            ),
            RemoteSyncFile(
                remote_path="/srv/app/__pycache__/settings.cpython-312.pyc",
                relative_path="__pycache__/settings.cpython-312.pyc",
                size_bytes=20,
            ),
        ],
        downloaded_bytes={
            "/srv/app/locale/es.po": b'msgid "hello"\n',
            "/srv/app/__pycache__/settings.cpython-312.pyc": b"compiled",
        },
    )
    scope_service = StubFrameworkSyncScopeService(
        resolved_scope=ResolvedSyncScope(
            framework_type="django",
            adapter_name="django_adapter",
            status=SyncScopeStatus.FILTERED,
            filters=(
                SyncFilterSpec(
                    relative_path="locale",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="Django locale catalogs.",
                ),
            ),
            excludes=(
                SyncFilterSpec(
                    relative_path="__pycache__",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="Python bytecode cache.",
                ),
            ),
            message="Resolved Django sync scope.",
        )
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider]),
        framework_sync_scope_service=scope_service,
    )

    result = service.sync_remote_to_local(
        _build_site(
            local_root=local_root,
            framework_type="django",
            remote_connection=RemoteConnectionConfig(
                id="remote-site-123",
                site_project_id="site-123",
                connection_type="sftp",
                host="example.test",
                port=22,
                username="deploy",
                password="secret",
                remote_path="/srv/app",
                flags=RemoteConnectionFlags(use_adapter_sync_filters=True),
            ),
        )
    )

    assert result.success is True
    assert result.summary.files_downloaded == 1
    assert (local_root / "locale" / "es.po").exists() is True
    assert (local_root / "__pycache__" / "settings.cpython-312.pyc").exists() is False


def test_project_sync_service_uses_full_sync_project_01c5(
    tmp_path: Path,
) -> None:
    """Verify project sync service uses full sync when the project preference disables.

    filters.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    provider = StubSyncProvider(
        remote_files=[
            RemoteSyncFile(
                remote_path="/srv/app/wp-content/themes/theme/style.css",
                relative_path="wp-content/themes/theme/style.css",
                size_bytes=10,
            ),
            RemoteSyncFile(
                remote_path="/srv/app/readme.html",
                relative_path="readme.html",
                size_bytes=20,
            ),
        ],
        downloaded_bytes={
            "/srv/app/wp-content/themes/theme/style.css": b"body{}\n",
            "/srv/app/readme.html": b"readme\n",
        },
    )
    scope_service = StubFrameworkSyncScopeService(
        resolved_scope=ResolvedSyncScope(
            framework_type="wordpress",
            adapter_name="wordpress_adapter",
            status=SyncScopeStatus.FILTERED,
            filters=(
                SyncFilterSpec(
                    relative_path="wp-content/themes",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="WordPress theme sources.",
                ),
            ),
            message="WordPress sync filters were resolved.",
        )
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider]),
        framework_sync_scope_service=scope_service,
    )

    result = service.sync_remote_to_local(_build_site(local_root=local_root))

    assert result.success is True
    assert result.summary.files_downloaded == 2
    assert scope_service.calls == []


def test_project_sync_service_uses_the_persisted_filtered_sync_preference_for_uploads(
    tmp_path: Path,
) -> None:
    """Verify project sync service uses the persisted filtered sync preference for.

    uploads.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "wp-content" / "themes" / "theme").mkdir(parents=True)
    (local_root / "wp-content" / "themes" / "theme" / "style.css").write_text(
        "body{}\n",
        encoding="utf-8",
    )
    (local_root / "readme.html").write_text("readme\n", encoding="utf-8")
    scope_service = StubFrameworkSyncScopeService(
        resolved_scope=ResolvedSyncScope(
            framework_type="wordpress",
            adapter_name="wordpress_adapter",
            status=SyncScopeStatus.FILTERED,
            filters=(
                SyncFilterSpec(
                    relative_path="wp-content/themes",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="WordPress theme sources.",
                ),
            ),
            message="WordPress sync filters were resolved.",
        )
    )
    provider = StubSyncProvider()
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider]),
        framework_sync_scope_service=scope_service,
    )

    result = service.sync_local_to_remote(
        _build_site(
            local_root=local_root,
            remote_connection=RemoteConnectionConfig(
                id="remote-site-123",
                site_project_id="site-123",
                connection_type="sftp",
                host="example.test",
                port=22,
                username="deploy",
                password="secret",
                remote_path="/srv/app",
                flags=RemoteConnectionFlags(use_adapter_sync_filters=True),
            ),
        )
    )

    assert result.success is True
    assert result.summary.files_uploaded == 1
    assert "/srv/app/wp-content/themes/theme/style.css" in provider.uploaded_bytes
    assert "/srv/app/readme.html" not in provider.uploaded_bytes
    assert scope_service.calls == ["site-123"]


def test_project_sync_service_applies_django_exclusions_during_upload(
    tmp_path: Path,
) -> None:
    """Verify project sync service applies django exclusions during upload.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "__pycache__").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_text('msgid "hello"\n', encoding="utf-8")
    (local_root / "__pycache__" / "settings.cpython-312.pyc").write_bytes(b"compiled")
    scope_service = StubFrameworkSyncScopeService(
        resolved_scope=ResolvedSyncScope(
            framework_type="django",
            adapter_name="django_adapter",
            status=SyncScopeStatus.FILTERED,
            filters=(
                SyncFilterSpec(
                    relative_path="locale",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="Django locale catalogs.",
                ),
            ),
            excludes=(
                SyncFilterSpec(
                    relative_path="__pycache__",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="Python bytecode cache.",
                ),
            ),
            message="Resolved Django sync scope.",
        )
    )
    provider = StubSyncProvider()
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider]),
        framework_sync_scope_service=scope_service,
    )

    result = service.sync_local_to_remote(
        _build_site(
            local_root=local_root,
            framework_type="django",
            remote_connection=RemoteConnectionConfig(
                id="remote-site-123",
                site_project_id="site-123",
                connection_type="sftp",
                host="example.test",
                port=22,
                username="deploy",
                password="secret",
                remote_path="/srv/app",
                flags=RemoteConnectionFlags(use_adapter_sync_filters=True),
            ),
        )
    )

    assert result.success is True
    assert result.summary.files_uploaded == 1
    assert "/srv/app/locale/es.po" in provider.uploaded_bytes
    assert (
        "/srv/app/__pycache__/settings.cpython-312.pyc" not in provider.uploaded_bytes
    )


def test_project_sync_service_returns_controll_error_f_90d3(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled error when filtered sync scope.

    is….

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    scope_service = StubFrameworkSyncScopeService(
        resolved_scope=ResolvedSyncScope(
            framework_type="unknown",
            adapter_name=None,
            status=SyncScopeStatus.FRAMEWORK_UNRESOLVED,
            filters=(),
            message="The project does not expose a supported framework type.",
        )
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        ),
        framework_sync_scope_service=scope_service,
    )

    result = service.sync_remote_to_local(
        _build_site(
            local_root=tmp_path,
            remote_connection=RemoteConnectionConfig(
                id="remote-site-123",
                site_project_id="site-123",
                connection_type="sftp",
                host="example.test",
                port=22,
                username="deploy",
                password="secret",
                remote_path="/srv/app",
                flags=RemoteConnectionFlags(use_adapter_sync_filters=True),
            ),
        )
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "sync_scope_unavailable"


def test_project_sync_service_returns_controll_error_f_c84a(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled error when filtered sync scope….

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        ),
        framework_sync_scope_service=FailingFrameworkSyncScopeService(
            error=OSError("gitignore read failed")
        ),
    )

    result = service.sync_remote_to_local(
        _build_site(
            local_root=tmp_path,
            remote_connection=RemoteConnectionConfig(
                id="remote-site-123",
                site_project_id="site-123",
                connection_type="sftp",
                host="example.test",
                port=22,
                username="deploy",
                password="secret",
                remote_path="/srv/app",
                flags=RemoteConnectionFlags(use_adapter_sync_filters=True),
            ),
        )
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "sync_scope_resolution_failed"
    assert "gitignore read failed" in result.error.message


def test_project_sync_service_returns_controll_result__6b8d(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result when incremental listing.

    fails.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        OSError:
            Raised when this callable hits the corresponding error path.
    """
    provider = StubSyncProvider(
        downloaded_bytes={"/srv/app/locale/es.po": b'msgid "hello"\n'},
    )

    def _iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Handle iter remote files.

        Args:
            config:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        yield RemoteSyncFile(
            remote_path="/srv/app/locale/es.po",
            relative_path="locale/es.po",
            size_bytes=10,
        )
        msg = f"Could not continue listing {config.remote_path}."
        raise OSError(msg)

    provider.iter_remote_files_impl = _iter_remote_files
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "remote_listing_failed"
    assert result.summary.files_discovered == 1
    assert result.summary.files_downloaded == 1


def test_project_sync_service_returns_controll_result__a9b7(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result when incremental listing.

    hits….

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        ModuleNotFoundError:
            Raised when this callable hits the corresponding error path.
    """
    provider = StubSyncProvider(
        downloaded_bytes={"/srv/app/locale/es.po": b'msgid "hello"\n'},
    )

    def _iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Handle iter remote files.

        Args:
            config:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ModuleNotFoundError:
                Raised when this callable hits the corresponding error path.
        """
        yield RemoteSyncFile(
            remote_path="/srv/app/locale/es.po",
            relative_path="locale/es.po",
            size_bytes=10,
        )
        msg = "paramiko"
        raise ModuleNotFoundError(msg)

    provider.iter_remote_files_impl = _iter_remote_files
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "missing_dependency"
    assert result.summary.files_discovered == 1
    assert result.summary.files_downloaded == 1


def test_project_sync_service_returns_a_controlled_result_when_listing_fails(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result when listing fails.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider(fail_on_list=True)]
        )
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "remote_listing_failed"
    assert result.error.message == (
        "Failed to list remote files for project 'Marketing Site' from sftp "
        "example.test:22 at remote path '/srv/app'. Cause: Could not list remote files."
    )


def test_project_sync_service_preserves_specific_remote_listing_error_codes(
    tmp_path: Path,
) -> None:
    """Verify project sync service preserves specific remote listing error codes.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        RemoteConnectionOperationError:
            Raised when this callable hits the corresponding error path.
    """
    provider = StubSyncProvider()

    def _iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Handle iter remote files.

        Args:
            config:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
        """
        raise RemoteConnectionOperationError(
            error_code="dns_resolution_failed",
            message="Temporary failure in name resolution",
        )

    provider.iter_remote_files_impl = _iter_remote_files
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "dns_resolution_failed"
    assert result.error.message == "Temporary failure in name resolution"


def test_project_sync_service_returns_a_controlled_result_when_a_download_fails(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result when a download fails.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[
                StubSyncProvider(
                    remote_files=[
                        RemoteSyncFile(
                            remote_path="/srv/app/locale/es.po",
                            relative_path="locale/es.po",
                            size_bytes=10,
                        )
                    ],
                    downloaded_bytes={"/srv/app/locale/es.po": b"ignored"},
                    fail_on_download="/srv/app/locale/es.po",
                )
            ]
        )
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "download_failed"
    assert result.error.message == (
        "Failed to download remote file '/srv/app/locale/es.po' into local path "
        f"'{tmp_path / 'locale' / 'es.po'}'. Cause: Download failed for "
        "/srv/app/locale/es.po."
    )


def test_project_sync_service_preserves_specific_download_error_codes(
    tmp_path: Path,
) -> None:
    """Verify project sync service preserves specific download error codes.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        RemoteConnectionOperationError:
            Raised when this callable hits the corresponding error path.
    """
    remote_path = "/srv/app/locale/es.po"
    provider = StubSyncProvider(
        remote_files=[
            RemoteSyncFile(
                remote_path=remote_path,
                relative_path="locale/es.po",
                size_bytes=10,
            )
        ],
        downloaded_bytes={remote_path: b"ignored"},
    )

    def _download_file(
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> bytes:
        """Handle download file.

        Args:
            config:
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
        """
        raise RemoteConnectionOperationError(
            error_code="authentication_failed",
            message="Authentication failed",
        )

    provider.download_file_impl = _download_file
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "authentication_failed"
    assert result.error.message == "Authentication failed"
    assert result.error.remote_path == remote_path


def test_project_sync_service_emit_failure_ignores_success_results() -> None:
    """Verify project sync service emit failure ignores success results.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        )
    )
    events: list[SyncProgressEvent] = []

    service._emit_failure(
        events.append,
        SyncResult(
            direction=SyncDirection.REMOTE_TO_LOCAL,
            success=True,
            project_id="site-1",
            connection_type="sftp",
            local_path="/tmp/project-sync",
            summary=SyncSummary(
                files_discovered=0,
                files_downloaded=0,
                directories_created=0,
                bytes_downloaded=0,
            ),
            error=None,
        ),
    )

    assert events == []


def test_project_sync_service_returns_a_controlled_result_when_local_workspace_fails(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result when local workspace.

    fails.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        ),
        local_workspace=cast(LocalSyncWorkspace, _FailingWorkspace()),
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "local_workspace_failed"
    assert result.error.message == (
        f"Failed to prepare local workspace '{tmp_path}' for project 'Marketing Site'. "
        "Cause: workspace unavailable"
    )


def test_project_sync_service_returns_a_controlled_result_for_unsupported_connections(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result for unsupported.

    connections.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        )
    )

    result = service.sync_remote_to_local(
        _build_site(
            local_root=tmp_path,
            remote_connection=RemoteConnectionConfig(
                id="remote-site-123",
                site_project_id="site-123",
                connection_type="ftp",
                host="example.test",
                port=21,
                username="deploy",
                password="secret",
                remote_path="/srv/app",
            ),
        )
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "unsupported_connection_type"


def test_project_sync_service_returns_missing_dependency_when_listing_requires_it(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns missing dependency when listing requires it.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider(missing_dependency_on_list=True)]
        )
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "missing_dependency"


def test_project_sync_service_returns_missing_dependency_when_download_requires_it(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns missing dependency when download requires it.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    remote_path = "/srv/app/locale/es.po"
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[
                StubSyncProvider(
                    remote_files=[
                        RemoteSyncFile(
                            remote_path=remote_path,
                            relative_path="locale/es.po",
                            size_bytes=10,
                        )
                    ],
                    downloaded_bytes={remote_path: b"ignored"},
                    missing_dependency_on_download=remote_path,
                )
            ]
        )
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "missing_dependency"
    assert result.error.remote_path == remote_path


def test_project_sync_service_returns_controlled_error_when_session_open_fails(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns controlled error when session open fails.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    provider = StubSyncProvider(
        open_session_error=RemoteConnectionOperationError(
            error_code="connection_timeout",
            message="Connection timed out.",
        )
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "connection_timeout"


def test_project_sync_service_emits_failure_when_local_to_remote_scope_resolution_fails(
    tmp_path: Path,
) -> None:
    """Verify project sync service emits failure when local to remote scope resolution.

    fails.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    local_root.mkdir(parents=True)
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        ),
        framework_sync_scope_service=None,
    )
    events: list[SyncProgressEvent] = []

    result = service.sync_local_to_remote(
        _build_site(
            local_root=local_root,
            remote_connection=RemoteConnectionConfig(
                id="remote-site-123",
                site_project_id="site-123",
                connection_type="sftp",
                host="example.test",
                port=22,
                username="deploy",
                password="secret",
                remote_path="/srv/app",
                flags=RemoteConnectionFlags(use_adapter_sync_filters=True),
            ),
        ),
        progress_callback=events.append,
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "sync_scope_resolution_not_configured"
    expected_message = (
        "Adapter-filtered sync is enabled for project 'Marketing Site', "
        "but framework sync scope resolution is not configured."
    )
    assert any(event.message == expected_message for event in events)


def test_project_sync_service_emits_provider_failure_for_local_to_remote_sync(
    tmp_path: Path,
) -> None:
    """Verify project sync service emits provider failure for local to remote sync.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    local_root.mkdir(parents=True)
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[])
    )
    events: list[SyncProgressEvent] = []

    result = service.sync_local_to_remote(
        _build_site(local_root=local_root),
        progress_callback=events.append,
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "unsupported_connection_type"
    assert events[-1].stage is SyncProgressStage.FAILED


def test_project_sync_service_handles_incremental_remote_listing_operation_errors(
    tmp_path: Path,
) -> None:
    """Verify project sync service handles incremental remote listing operation errors.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        RemoteConnectionOperationError:
            Raised when this callable hits the corresponding error path.
    """
    first_remote_file = RemoteSyncFile(
        remote_path="/srv/app/locale/es.po",
        relative_path="locale/es.po",
        size_bytes=10,
    )

    def _iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Handle iter remote files.

        Args:
            config:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
        """
        yield first_remote_file
        raise RemoteConnectionOperationError(
            error_code="transport_io_failed",
            message="Remote channel reset.",
        )

    provider = StubSyncProvider(
        downloaded_bytes={"/srv/app/locale/es.po": b"payload"},
        iter_remote_files_impl=_iter_remote_files,
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "transport_io_failed"
    assert result.summary.files_discovered == 1
    assert result.summary.files_downloaded == 1


def test_project_sync_service_reports_remote_session_close_operation_errors(
    tmp_path: Path,
) -> None:
    """Verify project sync service reports remote session close operation errors.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    provider = StubSyncProvider(
        remote_files=[],
        close_error=RemoteConnectionOperationError(
            error_code="close_failed",
            message="Close failed.",
        ),
    )
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )
    events: list[SyncProgressEvent] = []

    result = service.sync_remote_to_local(
        _build_site(local_root=tmp_path),
        progress_callback=events.append,
    )

    assert result.success is True
    assert any(
        event.message == "Remote session close failed: Close failed."
        for event in events
    )


def test_project_sync_service_reports_remote_session_close_os_errors(
    tmp_path: Path,
) -> None:
    """Verify project sync service reports remote session close os errors.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    provider = StubSyncProvider(remote_files=[], close_error=OSError("Socket closed."))
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )
    events: list[SyncProgressEvent] = []

    result = service.sync_remote_to_local(
        _build_site(local_root=tmp_path),
        progress_callback=events.append,
    )

    assert result.success is True
    assert any(
        event.message == "Remote session close failed: Socket closed."
        for event in events
    )


def test_project_sync_service_raises_if_provider_resolution_returns_none(
    tmp_path: Path,
) -> None:
    """Verify project sync service raises if provider resolution returns none.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        )
    )
    service._resolve_provider = (  # type: ignore[method-assign]
        lambda **_: (None, None)
    )

    with pytest.raises(
        AssertionError,
        match=(r"Remote sync provider resolution unexpectedly returned None\."),
    ):
        service.sync_remote_to_local(_build_site(local_root=tmp_path))


def test_project_sync_service_raises_if_local_upload_provider_resolution_returns_none(
    tmp_path: Path,
) -> None:
    """Verify project sync service raises if local upload provider resolution returns.

    none.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b"a")
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        )
    )
    service._resolve_provider = (  # type: ignore[method-assign]
        lambda **_: (None, None)
    )

    with pytest.raises(
        AssertionError,
        match=r"Remote sync provider resolution unexpectedly returned None\.",
    ):
        service.sync_local_to_remote(_build_site(local_root=local_root))


def test_project_sync_service_uploads_local_files_into_the_remote_workspace(
    tmp_path: Path,
) -> None:
    """Verify project sync service uploads local files into the remote workspace.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "templates").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b'msgid "hola"\n')
    (local_root / "templates" / "home.html").write_bytes(b"<h1>Hola</h1>\n")
    provider = StubSyncProvider()
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_local_to_remote(_build_site(local_root=local_root))

    assert result.success is True
    assert result.direction is SyncDirection.LOCAL_TO_REMOTE
    assert result.summary.files_discovered == 2
    assert result.summary.files_uploaded == 2
    assert provider.uploaded_bytes == {
        "/srv/app/locale/es.po": b'msgid "hola"\n',
        "/srv/app/templates/home.html": b"<h1>Hola</h1>\n",
    }


def test_project_sync_service_reports_progress_commands_for_local_to_remote_execution(
    tmp_path: Path,
) -> None:
    """Verify project sync service reports progress commands for local to remote.

    execution.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b'msgid "hola"\n')
    provider = StubSyncProvider()
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )
    events: list[SyncProgressEvent] = []

    result = service.sync_local_to_remote(
        _build_site(local_root=local_root),
        progress_callback=events.append,
    )

    assert result.success is True
    assert [
        event.command_text for event in events if event.command_text is not None
    ] == [
        f"LOCAL LIST {local_root}",
        "SFTP CONNECT example.test:22",
        "SFTP MKDIR /srv/app/locale",
        "SFTP PUT /srv/app/locale/es.po",
        "SFTP CLOSE example.test:22",
    ]


def test_project_sync_service_reuses_single_remote_ses_bc6b(
    tmp_path: Path,
) -> None:
    """Verify project sync service reuses a single remote session for a multi file.

    local.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "templates").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b"a")
    (local_root / "templates" / "home.html").write_bytes(b"b")
    provider = StubSyncProvider()
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_local_to_remote(_build_site(local_root=local_root))

    assert result.success is True
    assert provider.open_session_calls == 1
    assert provider.session_events == [
        "mkdir:/srv/app/locale",
        "upload:/srv/app/locale/es.po",
        "mkdir:/srv/app/templates",
        "upload:/srv/app/templates/home.html",
        "close",
    ]


def test_project_sync_service_rejects_local_to_remote_sync_without_remote_connections(
    tmp_path: Path,
) -> None:
    """Verify project sync service rejects local to remote sync without remote.

    connections.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        )
    )

    result = service.sync_local_to_remote(
        _build_site(local_root=tmp_path, remote_connection=None)
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "missing_remote_connection"


def test_project_sync_service_returns_success_for_empty_local_sources(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns success for empty local sources.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    local_root.mkdir(parents=True)
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        )
    )

    result = service.sync_local_to_remote(_build_site(local_root=local_root))

    assert result.success is True
    assert result.summary.files_discovered == 0
    assert result.summary.files_uploaded == 0


def test_project_sync_service_returns_a_controlled_result_when_local_listing_fails(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result when local listing fails.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    occupied_path = tmp_path / "not-a-directory"
    occupied_path.write_text("occupied", encoding="utf-8")
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider()]
        )
    )

    result = service.sync_local_to_remote(_build_site(local_root=occupied_path))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "local_workspace_failed"


def test_project_sync_service_returns_controll_result__5a5d(
    tmp_path: Path,
) -> None:
    """Verify project sync service reports local upload session open failures.

    open….

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b'msgid "hola"\n')
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[
                StubSyncProvider(
                    open_session_error=RemoteConnectionOperationError(
                        error_code="ssh_connection_failed",
                        message="Connection refused.",
                    )
                )
            ]
        )
    )

    result = service.sync_local_to_remote(_build_site(local_root=local_root))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "ssh_connection_failed"


def test_project_sync_service_returns_a_controlled_result_when_a_remote_upload_fails(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result when a remote upload.

    fails.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b'msgid "hola"\n')
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider(fail_on_upload="/srv/app/locale/es.po")]
        )
    )

    result = service.sync_local_to_remote(_build_site(local_root=local_root))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "upload_failed"


def test_project_sync_service_returns_controll_result__ef35(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result when structured remote.

    upload….

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        RemoteConnectionOperationError:
            Raised when this callable hits the corresponding error path.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b'msgid "hola"\n')
    provider = StubSyncProvider()

    def fail_upload(
        _config: RemoteConnectionConfig,
        remote_path: str,
        _contents: bytes,
        _progress_callback: Callable[[SyncProgressEvent], None] | None,
    ) -> None:
        """Handle fail upload.

        Args:
            _config:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            _contents:
                Value supplied to this callable.
            _progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
        """
        raise RemoteConnectionOperationError(
            error_code="upload_failed",
            message=f"Structured upload failure for {remote_path}.",
        )

    provider.upload_file_impl = fail_upload
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_local_to_remote(_build_site(local_root=local_root))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "upload_failed"


def test_project_sync_service_returns_controll_result__e426(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result when remote directory.

    creation….

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b'msgid "hola"\n')
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider(fail_on_mkdir="/srv/app/locale")]
        )
    )

    result = service.sync_local_to_remote(_build_site(local_root=local_root))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "remote_directory_failed"


def test_project_sync_service_returns_a_controlled_result_when_remote_directory_(
    tmp_path: Path,
) -> None:
    """Verify project sync service returns a controlled result when remote directory.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        RemoteConnectionOperationError:
            Raised when this callable hits the corresponding error path.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b'msgid "hola"\n')
    provider = StubSyncProvider()

    def fail_mkdir(
        _config: RemoteConnectionConfig,
        remote_path: str,
        _progress_callback: Callable[[SyncProgressEvent], None] | None,
    ) -> int:
        """Handle fail mkdir.

        Args:
            _config:
                Value supplied to this callable.
            remote_path:
                Value supplied to this callable.
            _progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
        """
        raise RemoteConnectionOperationError(
            error_code="remote_directory_failed",
            message=f"Structured mkdir failure for {remote_path}.",
        )

    provider.ensure_remote_directory_impl = fail_mkdir
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_local_to_remote(_build_site(local_root=local_root))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "remote_directory_failed"


def test_project_sync_service_skips_local_uploads_excluded_by_scope(
    tmp_path: Path,
) -> None:
    """Verify project sync service skips local uploads excluded by scope.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "templates").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b"a")
    (local_root / "templates" / "home.html").write_bytes(b"b")
    provider = StubSyncProvider()
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )

    result = service.sync_local_to_remote(
        _build_site(local_root=local_root),
        resolved_scope=ResolvedSyncScope(
            framework_type="wordpress",
            adapter_name="WordPress",
            status=SyncScopeStatus.FILTERED,
            filters=(
                ResolvedSyncRule(
                    rule_key="include-locale",
                    source=SyncRuleSource.PROJECT,
                    relative_path="locale",
                    filter_type=SyncFilterType.DIRECTORY,
                    behavior=SyncRuleBehavior.INCLUDE,
                    is_enabled=True,
                    description="Include locale only.",
                ).as_filter_spec(),
            ),
            message="Only locale files included.",
            catalog_rules=(
                ResolvedSyncRule(
                    rule_key="include-locale",
                    source=SyncRuleSource.PROJECT,
                    relative_path="locale",
                    filter_type=SyncFilterType.DIRECTORY,
                    behavior=SyncRuleBehavior.INCLUDE,
                    is_enabled=True,
                    description="Include locale only.",
                ),
            ),
        ),
    )

    assert result.success is True
    assert result.summary.files_discovered == 1
    assert provider.uploaded_bytes == {"/srv/app/locale/es.po": b"a"}


def test_project_sync_service_continues_when_scope_excludes_a_local_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify project sync service continues when scope excludes a local file.

    Args:
        monkeypatch:
            Value supplied to this callable.
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = tmp_path / "workspace" / "site"
    local_root.mkdir(parents=True)
    (local_root / "skip.txt").write_bytes(b"a")
    (local_root / "keep.txt").write_bytes(b"b")
    provider = StubSyncProvider()
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[provider])
    )
    scope_calls: list[str] = []

    monkeypatch.setattr(
        service,
        "_list_local_files",
        lambda **_kwargs: (
            LocalSyncFile(
                local_path=local_root / "skip.txt",
                relative_path="skip.txt",
                size_bytes=1,
            ),
            LocalSyncFile(
                local_path=local_root / "keep.txt",
                relative_path="keep.txt",
                size_bytes=1,
            ),
        ),
    )

    def _scope_includes(scope: ResolvedSyncScope | None, relative_path: str) -> bool:
        """Handle scope includes.

        Args:
            scope:
                Value supplied to this callable.
            relative_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        scope_calls.append(relative_path)
        return relative_path == "keep.txt"

    monkeypatch.setattr(project_sync_module, "_scope_includes", _scope_includes)

    result = service.sync_local_to_remote(
        _build_site(local_root=local_root),
        resolved_scope=ResolvedSyncScope(
            framework_type="wordpress",
            adapter_name="WordPress",
            status=SyncScopeStatus.FILTERED,
            filters=(),
            message="Skip one file.",
        ),
    )

    assert result.success is True
    assert result.summary.files_discovered == 1
    assert scope_calls == ["skip.txt", "keep.txt"]


def test_project_sync_service_joins_remote_sync_path_at_root() -> None:
    """Verify project sync service joins remote sync path at root.

    Returns:
        value:
            Structured value returned by this callable.
    """
    assert _join_remote_sync_path("/", "locale/es.po") == "/locale/es.po"


def _build_site(
    *,
    local_root: Path,
    framework_type: str = "wordpress",
    remote_connection: RemoteConnectionConfig | None | object = _DEFAULT_REMOTE,
) -> RegisteredSite:
    """Handle build site.

    Args:
        local_root:
            Value supplied to this callable.
        framework_type:
            Value supplied to this callable.
        remote_connection:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    resolved_remote_connection: RemoteConnectionConfig | None
    if remote_connection is _DEFAULT_REMOTE:
        resolved_remote_connection = RemoteConnectionConfig(
            id="remote-site-123",
            site_project_id="site-123",
            connection_type="sftp",
            host="example.test",
            port=22,
            username="deploy",
            password="secret",
            remote_path="/srv/app",
        )
    else:
        resolved_remote_connection = cast(
            RemoteConnectionConfig | None, remote_connection
        )
    return RegisteredSite(
        project=SiteProject(
            id="site-123",
            name="Marketing Site",
            framework_type=framework_type,
            local_path=str(local_root),
            default_locale="en_US",
            is_active=True,
        ),
        remote_connection=resolved_remote_connection,
    )


class _FailingWorkspace:
    """Test helper for FailingWorkspace.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def ensure_directory(self, path: Path) -> int:
        """Handle ensure directory.

        Args:
            self:
                Value supplied to this callable.
            path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        msg = "workspace unavailable"
        raise OSError(msg)

    def write_file(self, target_path: Path, contents: bytes) -> None:
        """Handle write file.

        Args:
            self:
                Value supplied to this callable.
            target_path:
                Value supplied to this callable.
            contents:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            AssertionError:
                Raised when this callable hits the corresponding error path.
        """
        msg = f"write_file should not be called for {target_path}"
        raise AssertionError(msg)
