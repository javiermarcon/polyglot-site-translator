"""Integration tests for the real sync flows."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
import time

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionSessionState,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.domain.sync.models import (
    RemoteSyncFile,
    SyncProgressEvent,
    SyncProgressStage,
)
from polyglot_site_translator.domain.sync.scope import ResolvedSyncScope
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.presentation.kivy.screens.sync import SyncScreen
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel
from polyglot_site_translator.services.framework_sync_scope import (
    FrameworkSyncScopeService,
)
from polyglot_site_translator.services.project_sync import ProjectSyncService
from polyglot_site_translator.services.remote_connections import RemoteConnectionService


class _FailingFrameworkSyncScopeService:
    def resolve_for_site(self, site: RegisteredSite) -> ResolvedSyncScope:
        del site
        msg = "broken sync scope"
        raise OSError(msg)


@dataclass(frozen=True)
class StubSyncProvider:
    """Remote provider stub used by the integration runtime."""

    descriptor: RemoteConnectionTypeDescriptor = field(
        default_factory=lambda: RemoteConnectionTypeDescriptor(
            connection_type="sftp",
            display_name="SFTP",
            default_port=22,
        )
    )

    def open_session(self, config: RemoteConnectionConfig) -> _StubSyncSession:
        return _StubSyncSession(config=config)

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
        *,
        max_files: int = 1000,
    ) -> list[RemoteSyncFile]:
        session = self.open_session(config)
        try:
            return list(session.iter_remote_files(progress_callback))[:max_files]
        finally:
            session.close(progress_callback)

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        session = self.open_session(config)
        try:
            yield from session.iter_remote_files(progress_callback)
        finally:
            session.close(progress_callback)

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> bytes:
        session = self.open_session(config)
        try:
            return session.download_file(remote_path, progress_callback)
        finally:
            session.close(progress_callback)

    def ensure_remote_directory(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> int:
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
        session = self.open_session(config)
        try:
            session.upload_file(remote_path, contents, progress_callback)
        finally:
            session.close(progress_callback)

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        return RemoteConnectionTestResult(
            success=True,
            connection_type=config.connection_type,
            host=config.host,
            port=config.port,
            message="Connected successfully using the sync test provider.",
            error_code=None,
        )


def _build_project_sync_service(
    remote_registry: RemoteConnectionRegistry,
) -> ProjectSyncService:
    return ProjectSyncService(
        registry=remote_registry,
        framework_sync_scope_service=FrameworkSyncScopeService(
            registry=FrameworkAdapterRegistry.discover_installed()
        ),
    )


@dataclass
class _StubSyncSession:
    config: RemoteConnectionConfig
    state: RemoteConnectionSessionState = RemoteConnectionSessionState.OPEN
    _connect_emitted: bool = False

    def _emit_connect_if_needed(
        self,
        progress_callback: Callable[[SyncProgressEvent], None] | None,
    ) -> None:
        if self._connect_emitted or progress_callback is None:
            return
        progress_callback(
            SyncProgressEvent(
                stage=SyncProgressStage.LISTING_REMOTE,
                message="Connecting through the sync integration stub session.",
                command_text=f"SFTP CONNECT {self.config.host}:{self.config.port}",
            )
        )
        self._connect_emitted = True

    def iter_remote_files(
        self,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message="Listing remote files through the sync integration stub.",
                    command_text=f"SFTP LIST {self.config.remote_path}",
                )
            )
        if self.config.host == "broken.example.test":
            msg = "Remote listing failed."
            raise OSError(msg)
        if self.config.host == "filtered.example.test":
            yield RemoteSyncFile(
                remote_path="/srv/app/wp-content/themes/theme/style.css",
                relative_path="wp-content/themes/theme/style.css",
                size_bytes=16,
            )
            yield RemoteSyncFile(
                remote_path="/srv/app/readme.html",
                relative_path="readme.html",
                size_bytes=14,
            )
            return
        yield RemoteSyncFile(
            remote_path="/srv/app/locale/es.po",
            relative_path="locale/es.po",
            size_bytes=16,
        )
        yield RemoteSyncFile(
            remote_path="/srv/app/templates/home.html",
            relative_path="templates/home.html",
            size_bytes=14,
        )

    def download_file(
        self,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> bytes:
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message=f"Downloading {remote_path} through the sync integration stub.",
                    command_text=f"SFTP GET {remote_path}",
                )
            )
        payloads = {
            "/srv/app/locale/es.po": b'msgid "hello"\n',
            "/srv/app/templates/home.html": b"<h1>Hello</h1>\n",
            "/srv/app/wp-content/themes/theme/style.css": b"body{}\n",
            "/srv/app/readme.html": b"readme\n",
        }
        return payloads[remote_path]

    def ensure_remote_directory(
        self,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> int:
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.PREPARING_REMOTE,
                    message=f"Preparing remote directory {remote_path}.",
                    command_text=f"SFTP MKDIR {remote_path}",
                )
            )
        return 1

    def upload_file(
        self,
        remote_path: str,
        contents: bytes,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> None:
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.UPLOADING_FILE,
                    message=f"Uploading {remote_path} through the sync integration stub.",
                    command_text=f"SFTP PUT {remote_path}",
                )
            )

    def close(
        self,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> None:
        self.state = RemoteConnectionSessionState.CLOSED
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message="Closing the sync integration stub session.",
                    command_text=f"SFTP CLOSE {self.config.host}:{self.config.port}",
                )
            )


def test_real_sync_flow_downloads_files_into_the_project_workspace(tmp_path: Path) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=_build_project_sync_service(remote_registry),
        )
    )
    shell = app._shell
    local_root = tmp_path / "workspace" / "marketing-site"

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            connection_type="sftp",
            remote_host="example.test",
            remote_port="22",
            remote_username="deploy",
            remote_password="secret",
            remote_path="/srv/app",
            is_active=True,
        )
    )

    shell.open_projects()
    created_project = shell.projects_state.projects[0]
    shell.select_project(created_project.id)
    shell.start_sync()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "completed"
    assert shell.sync_state.files_synced == 2
    assert shell.sync_state.error_code is None
    assert (local_root / "locale" / "es.po").read_bytes() == b'msgid "hello"\n'
    assert (local_root / "templates" / "home.html").read_bytes() == b"<h1>Hello</h1>\n"


def test_real_sync_flow_uses_filtered_mode_when_the_project_preference_enables_it(
    tmp_path: Path,
) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=_build_project_sync_service(remote_registry),
        )
    )
    shell = app._shell
    local_root = tmp_path / "workspace" / "filtered-site"

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Filtered Site",
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            connection_type="sftp",
            remote_host="filtered.example.test",
            remote_port="22",
            remote_username="deploy",
            remote_password="secret",
            remote_path="/srv/app",
            is_active=True,
            use_adapter_sync_filters=True,
        )
    )

    shell.open_projects()
    created_project = shell.projects_state.projects[0]
    shell.select_project(created_project.id)
    shell.start_sync()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "completed"
    assert shell.sync_state.files_synced == 1
    assert (local_root / "wp-content" / "themes" / "theme" / "style.css").exists() is True
    assert (local_root / "readme.html").exists() is False


def test_real_sync_flow_surfaces_scope_resolution_failures_without_crashing(
    tmp_path: Path,
) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=ProjectSyncService(
                registry=remote_registry,
                framework_sync_scope_service=_FailingFrameworkSyncScopeService(),
            ),
        )
    )
    shell = app._shell
    local_root = tmp_path / "workspace" / "filtered-site"

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Filtered Site",
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            connection_type="sftp",
            remote_host="filtered.example.test",
            remote_port="22",
            remote_username="deploy",
            remote_password="secret",
            remote_path="/srv/app",
            is_active=True,
            use_adapter_sync_filters=True,
        )
    )

    shell.open_projects()
    created_project = shell.projects_state.projects[0]
    shell.select_project(created_project.id)
    shell.start_sync()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "failed"
    assert shell.sync_state.error_code == "sync_scope_resolution_failed"
    assert "broken sync scope" in shell.sync_state.summary


def test_sync_screen_renders_real_sync_results(tmp_path: Path) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=_build_project_sync_service(remote_registry),
        )
    )
    root = app.build()
    shell = root.get_screen("dashboard")._shell
    local_root = tmp_path / "workspace" / "marketing-site"
    sync_screen = root.get_screen("sync")
    assert isinstance(sync_screen, SyncScreen)

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            connection_type="sftp",
            remote_host="example.test",
            remote_port="22",
            remote_username="deploy",
            remote_password="secret",
            remote_path="/srv/app",
            is_active=True,
        )
    )
    shell.open_projects()
    created_project = shell.projects_state.projects[0]
    shell.select_project(created_project.id)
    shell.start_sync()

    sync_screen.refresh()

    assert "Status: completed" in sync_screen._summary_label.text
    assert "Files: 2" in sync_screen._summary_label.text


def test_sync_screen_renders_structured_errors(tmp_path: Path) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=_build_project_sync_service(remote_registry),
        )
    )
    root = app.build()
    shell = root.get_screen("dashboard")._shell
    local_root = tmp_path / "workspace" / "marketing-site"
    sync_screen = root.get_screen("sync")
    assert isinstance(sync_screen, SyncScreen)

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Broken Site",
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            connection_type="sftp",
            remote_host="broken.example.test",
            remote_port="22",
            remote_username="deploy",
            remote_password="secret",
            remote_path="/srv/app",
            is_active=True,
        )
    )
    shell.open_projects()
    created_project = shell.projects_state.projects[0]
    shell.select_project(created_project.id)
    shell.start_sync()

    sync_screen.refresh()

    assert "Status: failed" in sync_screen._summary_label.text
    assert "Error Code: remote_listing_failed" in sync_screen._summary_label.text


def test_project_detail_sync_action_opens_a_progress_window_with_command_log(
    tmp_path: Path,
) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=_build_project_sync_service(remote_registry),
        )
    )
    root = app.build()
    detail_screen = root.get_screen("project_detail")
    shell = detail_screen._shell
    local_root = tmp_path / "workspace" / "marketing-site"

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            connection_type="sftp",
            remote_host="example.test",
            remote_port="22",
            remote_username="deploy",
            remote_password="secret",
            remote_path="/srv/app",
            is_active=True,
        )
    )
    shell.open_projects()
    created_project = shell.projects_state.projects[0]
    shell.select_project(created_project.id)
    root.current = "project_detail"

    detail_screen._start_sync()

    assert root.current == "project_detail"
    assert detail_screen._sync_progress_popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        detail_screen._sync_progress_popup.refresh()
        command_log_text = detail_screen._sync_progress_popup._command_log_label.text
        if (
            "SFTP LIST /srv/app" in command_log_text
            and "SFTP GET /srv/app/locale/es.po" in command_log_text
        ):
            break
        time.sleep(0.01)

    command_log_text = detail_screen._sync_progress_popup._command_log_label.text
    assert "SFTP LIST /srv/app" in command_log_text
    assert "SFTP GET /srv/app/locale/es.po" in command_log_text


def test_project_detail_sync_action_reuses_a_single_remote_session(
    tmp_path: Path,
) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=_build_project_sync_service(remote_registry),
        )
    )
    root = app.build()
    detail_screen = root.get_screen("project_detail")
    shell = detail_screen._shell
    local_root = tmp_path / "workspace" / "marketing-site"

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            connection_type="sftp",
            remote_host="example.test",
            remote_port="22",
            remote_username="deploy",
            remote_password="secret",
            remote_path="/srv/app",
            is_active=True,
        )
    )
    shell.open_projects()
    created_project = shell.projects_state.projects[0]
    shell.select_project(created_project.id)
    root.current = "project_detail"

    detail_screen._start_sync()

    assert detail_screen._sync_progress_popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        detail_screen._sync_progress_popup.refresh()
        command_log_text = detail_screen._sync_progress_popup._command_log_label.text
        if "SFTP CLOSE example.test:22" in command_log_text:
            break
        time.sleep(0.01)

    command_log_text = detail_screen._sync_progress_popup._command_log_label.text
    assert command_log_text.count("SFTP CONNECT example.test:22") == 1
    assert command_log_text.count("SFTP CLOSE example.test:22") == 1


def test_project_detail_progress_window_keeps_only_the_latest_configured_commands(
    tmp_path: Path,
) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    initial_state = settings_service.load_settings()
    settings_service.save_settings(replace(initial_state.app_settings, sync_progress_log_limit=2))
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=_build_project_sync_service(remote_registry),
        )
    )
    root = app.build()
    detail_screen = root.get_screen("project_detail")
    shell = detail_screen._shell
    local_root = tmp_path / "workspace" / "marketing-site"

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            connection_type="sftp",
            remote_host="example.test",
            remote_port="22",
            remote_username="deploy",
            remote_password="secret",
            remote_path="/srv/app",
            is_active=True,
        )
    )
    shell.open_projects()
    created_project = shell.projects_state.projects[0]
    shell.select_project(created_project.id)
    root.current = "project_detail"

    detail_screen._start_sync()

    assert detail_screen._sync_progress_popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        detail_screen._sync_progress_popup.refresh()
        command_lines = [
            line
            for line in detail_screen._sync_progress_popup._command_log_label.text.splitlines()
            if line.strip()
        ]
        if len(command_lines) == 2 and "SFTP CLOSE example.test:22" in command_lines:
            break
        time.sleep(0.01)

    command_lines = [
        line
        for line in detail_screen._sync_progress_popup._command_log_label.text.splitlines()
        if line.strip()
    ]
    assert command_lines == [
        f"LOCAL WRITE {local_root / 'templates' / 'home.html'}",
        "SFTP CLOSE example.test:22",
    ]


def test_real_sync_flow_uploads_local_files_into_the_remote_workspace(tmp_path: Path) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=_build_project_sync_service(remote_registry),
        )
    )
    shell = app._shell
    local_root = tmp_path / "workspace" / "marketing-site"
    (local_root / "locale").mkdir(parents=True)
    (local_root / "templates").mkdir(parents=True)
    (local_root / "locale" / "es.po").write_bytes(b'msgid "hola"\n')
    (local_root / "templates" / "home.html").write_bytes(b"<h1>Hola</h1>\n")

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            connection_type="sftp",
            remote_host="example.test",
            remote_port="22",
            remote_username="deploy",
            remote_password="secret",
            remote_path="/srv/app",
            is_active=True,
        )
    )

    shell.open_projects()
    created_project = shell.projects_state.projects[0]
    shell.select_project(created_project.id)
    shell.start_sync_to_remote()

    assert shell.sync_state is not None
    assert shell.sync_state.status == "completed"
    assert shell.sync_state.files_synced == 2
