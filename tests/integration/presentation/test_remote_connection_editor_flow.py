"""Integration tests for remote connection editing and test actions."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from kivy.uix.spinner import Spinner

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import RemoteSyncFile, SyncProgressEvent
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.services.remote_connections import RemoteConnectionService


@dataclass(frozen=True)
class SuccessfulSFTPProvider:
    """Remote provider stub used by the integration test runtime."""

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
            message="Connected successfully using the test provider.",
            error_code=None,
        )

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
        *,
        max_files: int = 1000,
    ) -> list[RemoteSyncFile]:
        return []

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        return iter(())

    def open_session(self, config: RemoteConnectionConfig) -> Any:
        msg = f"open_session not used in this test for {config.connection_type}"
        raise AssertionError(msg)

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> bytes:
        msg = f"download not used in this test for {remote_path}"
        raise AssertionError(msg)


def test_project_editor_exposes_dynamic_remote_connection_options(tmp_path: Path) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path)
    app = cast(
        Any,
        create_kivy_app(
            services=build_default_frontend_services(settings_service=settings_service)
        ),
    )
    root = app.build()
    editor_screen = root.get_screen("project_editor")
    shell = editor_screen._shell

    shell.open_project_editor_create()
    root.current = "project_editor"
    editor_screen.refresh()

    assert editor_screen._connection_type_spinner is not None
    assert isinstance(editor_screen._connection_type_spinner, Spinner)
    assert tuple(editor_screen._connection_type_spinner.values) == (
        "No Remote Connection",
        "FTP",
        "FTPS Explicit",
        "FTPS Implicit",
        "SCP",
        "SFTP",
    )


def test_project_editor_runs_connection_tests_and_surfaces_the_result(tmp_path: Path) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path)
    remote_connection_service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(providers=[SuccessfulSFTPProvider()])
    )
    app = cast(
        Any,
        create_kivy_app(
            services=build_default_frontend_services(
                settings_service=settings_service,
                remote_connection_service=remote_connection_service,
            )
        ),
    )
    root = app.build()
    editor_screen = root.get_screen("project_editor")
    shell = editor_screen._shell

    shell.open_project_editor_create()
    root.current = "project_editor"
    editor_screen.refresh()
    test_button = cast(Any, editor_screen._test_connection_button)
    assert test_button is not None
    assert bool(test_button.disabled) is True
    editor_screen._connection_type_spinner.text = "SFTP"
    editor_screen._remote_host_input.text = "example.com"
    editor_screen._remote_port_input.text = "22"
    editor_screen._remote_username_input.text = "deploy"
    editor_screen._remote_password_input.text = "secret"
    editor_screen._remote_path_input.text = "/srv/app"

    assert bool(test_button.disabled) is False

    editor_screen._test_connection()

    assert shell.project_editor_state is not None
    assert shell.project_editor_state.connection_test_result is not None
    assert shell.project_editor_state.connection_test_result.success is True
    assert "Connected successfully" in shell.project_editor_state.connection_test_result.message


def test_project_editor_persists_remote_connection_data_when_editing_site(
    tmp_path: Path,
) -> None:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    app = cast(
        Any,
        create_kivy_app(
            services=build_default_frontend_services(settings_service=settings_service)
        ),
    )
    root = app.build()
    editor_screen = root.get_screen("project_editor")
    shell = editor_screen._shell

    shell.open_project_editor_create()
    root.current = "project_editor"
    editor_screen.refresh()
    editor_screen._name_input.text = "Marketing Site"
    editor_screen._framework_spinner.text = "WordPress"
    editor_screen._local_path_input.text = "/workspace/marketing-site"
    editor_screen._default_locale_input.text = "en_US"
    editor_screen._connection_type_spinner.text = "FTP"
    editor_screen._remote_host_input.text = "ftp.example.com"
    editor_screen._remote_port_input.text = "21"
    editor_screen._remote_username_input.text = "deploy"
    editor_screen._remote_password_input.text = "super-secret"
    editor_screen._remote_path_input.text = "/public_html"
    editor_screen._save_editor()

    assert shell.project_detail_state is not None
    project_id = shell.project_detail_state.project.id

    shell.open_project_editor_edit(project_id)
    root.current = "project_editor"
    editor_screen.refresh()
    editor_screen._connection_type_spinner.text = "FTP"
    editor_screen._remote_host_input.text = "ftp-v2.example.com"
    editor_screen._remote_port_input.text = "21"
    editor_screen._remote_username_input.text = "deployer"
    editor_screen._remote_password_input.text = "super-secret-v2"
    editor_screen._remote_path_input.text = "/public_html/v2"
    editor_screen._save_editor()

    shell.open_project_editor_edit(project_id)
    editor_screen.refresh()

    assert shell.project_editor_state is not None
    assert shell.project_editor_state.editor.connection_type == "ftp"
    assert shell.project_editor_state.editor.remote_host == "ftp-v2.example.com"
    assert shell.project_editor_state.editor.remote_port == "21"
    assert shell.project_editor_state.editor.remote_username == "deployer"
    assert shell.project_editor_state.editor.remote_password == "super-secret-v2"
    assert shell.project_editor_state.editor.remote_path == "/public_html/v2"
