"""Unit tests for remote-to-local sync orchestration."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import pytest

from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionSessionState,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.domain.sync.models import (
    RemoteSyncFile,
    SyncDirection,
    SyncProgressEvent,
    SyncProgressStage,
    SyncResult,
    SyncSummary,
)
from polyglot_site_translator.infrastructure.remote_connections.base import (
    RemoteConnectionOperationError,
)
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.sync_local import LocalSyncWorkspace
from polyglot_site_translator.services.project_sync import ProjectSyncService


@dataclass
class StubSyncSession:
    config: RemoteConnectionConfig
    provider: StubSyncProvider
    state: RemoteConnectionSessionState = RemoteConnectionSessionState.OPEN
    close_calls: int = 0

    def iter_remote_files(
        self,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        self.provider.session_events.append("iter")
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message="Listing remote files through the sync test stub session.",
                    command_text=f"SFTP CONNECT {self.config.host}:{self.config.port}",
                )
            )
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
        self.provider.session_events.append(f"download:{remote_path}")
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message=f"Downloading {remote_path} through the sync test stub session.",
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

    def close(
        self,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> None:
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
    open_session_error: RemoteConnectionOperationError | None = None
    close_error: OSError | None = None
    open_session_calls: int = 0
    session_events: list[str] = field(default_factory=list)
    opened_sessions: list[StubSyncSession] = field(default_factory=list)

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        msg = f"test_connection not used in this sync test for {config.connection_type}"
        raise AssertionError(msg)

    def open_session(self, config: RemoteConnectionConfig) -> StubSyncSession:
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
        if self.iter_remote_files_impl is not None:
            return self.iter_remote_files_impl(config, progress_callback)
        return iter(self.list_remote_files(config, progress_callback))

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> bytes:
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


_DEFAULT_REMOTE = object()


def test_project_sync_service_downloads_remote_files_into_the_local_workspace(
    tmp_path: Path,
) -> None:
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
    assert [event.command_text for event in events if event.command_text is not None] == [
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
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message="Listing remote files through the streaming sync test stub.",
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


def test_project_sync_service_rejects_sites_without_remote_connections(tmp_path: Path) -> None:
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path, remote_connection=None))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "missing_remote_connection"


def test_project_sync_service_returns_success_for_empty_remote_sources(tmp_path: Path) -> None:
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[StubSyncProvider(remote_files=[], downloaded_bytes={})]
        )
    )

    result = service.sync_remote_to_local(_build_site(local_root=tmp_path))

    assert result.success is True
    assert result.summary.files_discovered == 0
    assert result.summary.files_downloaded == 0


def test_project_sync_service_returns_a_controlled_result_when_incremental_listing_fails(
    tmp_path: Path,
) -> None:
    provider = StubSyncProvider(
        downloaded_bytes={"/srv/app/locale/es.po": b'msgid "hello"\n'},
    )

    def _iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
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


def test_project_sync_service_returns_a_controlled_result_when_incremental_listing_hits_a_missing_dependency(  # noqa: E501
    tmp_path: Path,
) -> None:
    provider = StubSyncProvider(
        downloaded_bytes={"/srv/app/locale/es.po": b'msgid "hello"\n'},
    )

    def _iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
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
    provider = StubSyncProvider()

    def _iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
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
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
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
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()]),
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
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
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


def test_project_sync_service_handles_incremental_remote_listing_operation_errors(
    tmp_path: Path,
) -> None:
    first_remote_file = RemoteSyncFile(
        remote_path="/srv/app/locale/es.po",
        relative_path="locale/es.po",
        size_bytes=10,
    )

    def _iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
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
    assert any(event.message == "Remote session close failed: Close failed." for event in events)


def test_project_sync_service_reports_remote_session_close_os_errors(
    tmp_path: Path,
) -> None:
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
    assert any(event.message == "Remote session close failed: Socket closed." for event in events)


def test_project_sync_service_raises_if_provider_resolution_returns_none(
    tmp_path: Path,
) -> None:
    service = ProjectSyncService(
        registry=RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    )
    service._resolve_provider = (  # type: ignore[method-assign]
        lambda **_: (None, None)
    )

    with pytest.raises(
        AssertionError,
        match=(r"Remote sync provider resolution unexpectedly returned None\."),
    ):
        service.sync_remote_to_local(_build_site(local_root=tmp_path))


def _build_site(
    *,
    local_root: Path,
    remote_connection: RemoteConnectionConfig | None | object = _DEFAULT_REMOTE,
) -> RegisteredSite:
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
        resolved_remote_connection = cast(RemoteConnectionConfig | None, remote_connection)
    return RegisteredSite(
        project=SiteProject(
            id="site-123",
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            is_active=True,
        ),
        remote_connection=resolved_remote_connection,
    )


class _FailingWorkspace:
    def ensure_directory(self, path: Path) -> int:
        msg = "workspace unavailable"
        raise OSError(msg)

    def write_file(self, target_path: Path, contents: bytes) -> None:
        msg = f"write_file should not be called for {target_path}"
        raise AssertionError(msg)
