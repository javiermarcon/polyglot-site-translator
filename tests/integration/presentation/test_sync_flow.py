"""Integration tests for the real remote-to-local sync flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import time

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import (
    RemoteSyncFile,
    SyncProgressEvent,
    SyncProgressStage,
)
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.presentation.kivy.screens.sync import SyncScreen
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel
from polyglot_site_translator.services.project_sync import ProjectSyncService
from polyglot_site_translator.services.remote_connections import RemoteConnectionService


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

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> list[RemoteSyncFile]:
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message="Listing remote files through the sync integration stub.",
                    command_text=f"SFTP LIST {config.remote_path}",
                )
            )
        if config.host == "broken.example.test":
            msg = "Remote listing failed."
            raise OSError(msg)
        return [
            RemoteSyncFile(
                remote_path="/srv/app/locale/es.po",
                relative_path="locale/es.po",
                size_bytes=16,
            ),
            RemoteSyncFile(
                remote_path="/srv/app/templates/home.html",
                relative_path="templates/home.html",
                size_bytes=14,
            ),
        ]

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
                    message=f"Downloading {remote_path} through the sync integration stub.",
                    command_text=f"SFTP GET {remote_path}",
                )
            )
        payloads = {
            "/srv/app/locale/es.po": b'msgid "hello"\n',
            "/srv/app/templates/home.html": b"<h1>Hello</h1>\n",
        }
        return payloads[remote_path]


def test_real_sync_flow_downloads_files_into_the_project_workspace(tmp_path: Path) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=ProjectSyncService(registry=remote_registry),
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


def test_sync_screen_renders_real_sync_results(tmp_path: Path) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    remote_registry = RemoteConnectionRegistry.default_registry(providers=[StubSyncProvider()])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=remote_registry),
            project_sync_service=ProjectSyncService(registry=remote_registry),
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
            project_sync_service=ProjectSyncService(registry=remote_registry),
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
            project_sync_service=ProjectSyncService(registry=remote_registry),
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
        if "SFTP LIST /srv/app" in detail_screen._sync_progress_popup._command_log_label.text:
            break
        time.sleep(0.01)

    assert "SFTP LIST /srv/app" in detail_screen._sync_progress_popup._command_log_label.text
