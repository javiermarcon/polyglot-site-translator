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
    """Test helper for SuccessfulSFTPProvider.

    Attributes:
        descriptor (RemoteConnectionTypeDescriptor): Documented attribute exposed by this type.
    """

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
        """Verify connection.

        Args:
            config (RemoteConnectionConfigInput): Value supplied to this callable.

        Returns:
            RemoteConnectionTestResult: Structured value returned by this callable.
        """
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
        """Handle list remote files.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.
            progress_callback (Callable[[SyncProgressEvent], None] | None): Value supplied to this
        callable.
            max_files (int): Value supplied to this callable.

        Returns:
            list[RemoteSyncFile]: Structured value returned by this callable.
        """
        return []

    @staticmethod
    def iter_remote_files(
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
        """Handle iter remote files.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.
            progress_callback (Callable[[SyncProgressEvent], None] | None): Value supplied to this
        callable.

        Returns:
            Iterable[RemoteSyncFile]: Structured value returned by this callable.
        """
        return iter(())

    @staticmethod
    def open_session(config: RemoteConnectionConfig) -> Any:
        """Handle open session.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.

        Returns:
            Any: Structured value returned by this callable.

        Raises:
            AssertionError: Raised when this callable hits the corresponding error path.
        """
        msg = f"open_session not used in this test for {config.connection_type}"
        raise AssertionError(msg)

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> bytes:
        """Handle download file.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.
            remote_path (str): Value supplied to this callable.
            progress_callback (Callable[[SyncProgressEvent], None] | None): Value supplied to this
        callable.

        Returns:
            bytes: Structured value returned by this callable.

        Raises:
            AssertionError: Raised when this callable hits the corresponding error path.
        """
        msg = f"download not used in this test for {remote_path}"
        raise AssertionError(msg)

    @staticmethod
    def ensure_remote_directory(
        config: RemoteConnectionConfig,
        remote_path: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> int:
        """Handle ensure remote directory.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.
            remote_path (str): Value supplied to this callable.
            progress_callback (Callable[[SyncProgressEvent], None] | None): Value supplied to this
        callable.

        Returns:
            int: Structured value returned by this callable.

        Raises:
            AssertionError: Raised when this callable hits the corresponding error path.
        """
        msg = f"ensure_remote_directory not used in this test for {remote_path}"
        raise AssertionError(msg)

    @staticmethod
    def upload_file(
        config: RemoteConnectionConfig,
        remote_path: str,
        contents: bytes,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> None:
        """Handle upload file.

        Args:
            config (RemoteConnectionConfig): Value supplied to this callable.
            remote_path (str): Value supplied to this callable.
            contents (bytes): Value supplied to this callable.
            progress_callback (Callable[[SyncProgressEvent], None] | None): Value supplied to this
        callable.

        Returns:
            None: This callable does not return a value.

        Raises:
            AssertionError: Raised when this callable hits the corresponding error path.
        """
        msg = f"upload not used in this test for {remote_path}"
        raise AssertionError(msg)


def test_project_editor_exposes_dynamic_remote_connection_options(tmp_path: Path) -> None:
    """Verify project editor exposes dynamic remote connection options.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
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
    editor_screen._select_project_editor_section("remote")

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
    """Verify project editor runs connection tests and surfaces the result.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
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
    editor_screen._select_project_editor_section("remote")
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
    """Verify project editor persists remote connection data when editing site.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
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
    editor_screen._select_project_editor_section("translation")
    editor_screen._default_locale_input.text = "en_US"
    editor_screen._select_project_editor_section("remote")
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
    editor_screen._select_project_editor_section("remote")
    editor_screen._connection_type_spinner.text = "FTP"
    editor_screen._remote_host_input.text = "ftp-v2.example.com"
    editor_screen._remote_port_input.text = "21"
    editor_screen._remote_username_input.text = "deployer"
    editor_screen._remote_password_input.text = "super-secret-v2"
    editor_screen._remote_path_input.text = "/public_html/v2"
    editor_screen._save_editor()

    shell.open_project_editor_edit(project_id)
    editor_screen.refresh()
    editor_screen._select_project_editor_section("remote")

    assert shell.project_editor_state is not None
    assert shell.project_editor_state.editor.connection_type == "ftp"
    assert shell.project_editor_state.editor.remote_host == "ftp-v2.example.com"
    assert shell.project_editor_state.editor.remote_port == "21"
    assert shell.project_editor_state.editor.remote_username == "deployer"
    assert shell.project_editor_state.editor.remote_password == "super-secret-v2"
    assert shell.project_editor_state.editor.remote_path == "/public_html/v2"


def test_project_editor_persists_filtered_sync_preference_when_editing_site(
    tmp_path: Path,
) -> None:
    """Verify project editor persists filtered sync preference when editing site.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
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
    editor_screen._name_input.text = "Filtered Site"
    editor_screen._framework_spinner.text = "WordPress"
    editor_screen._local_path_input.text = "/workspace/filtered-site"
    editor_screen._select_project_editor_section("translation")
    editor_screen._default_locale_input.text = "en_US"
    editor_screen._select_project_editor_section("remote")
    editor_screen._connection_type_spinner.text = "FTP"
    editor_screen._remote_host_input.text = "ftp.example.com"
    editor_screen._remote_port_input.text = "21"
    editor_screen._remote_username_input.text = "deploy"
    editor_screen._remote_password_input.text = "super-secret"
    editor_screen._remote_path_input.text = "/public_html"
    editor_screen._select_project_editor_section("sync")
    editor_screen._use_adapter_sync_filters_switch.active = True
    editor_screen._save_editor()

    assert shell.project_detail_state is not None
    project_id = shell.project_detail_state.project.id
    shell.open_project_editor_edit(project_id)
    root.current = "project_editor"
    editor_screen.refresh()
    editor_screen._select_project_editor_section("sync")

    assert shell.project_editor_state is not None
    assert shell.project_editor_state.editor.use_adapter_sync_filters is True


def test_project_editor_persists_project_sync_rule_overrides(
    tmp_path: Path,
) -> None:
    """Verify project editor persists project sync rule overrides.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
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
    editor_screen._name_input.text = "Django Site"
    editor_screen._framework_spinner.text = "Django"
    editor_screen._local_path_input.text = "/workspace/django-site"
    editor_screen._select_project_editor_section("translation")
    editor_screen._default_locale_input.text = "en_US"
    editor_screen._select_project_editor_section("remote")
    editor_screen._connection_type_spinner.text = "FTP"
    editor_screen._remote_host_input.text = "ftp.example.com"
    editor_screen._remote_port_input.text = "21"
    editor_screen._remote_username_input.text = "deploy"
    editor_screen._remote_password_input.text = "super-secret"
    editor_screen._remote_path_input.text = "/public_html"
    editor_screen._select_project_editor_section("sync")
    editor_screen._use_adapter_sync_filters_switch.active = True
    editor_screen._refresh_sync_scope()
    assert shell.project_editor_state is not None
    cache_rule = next(
        item
        for item in shell.project_editor_state.editor.sync_rule_items
        if item.relative_path == "__pycache__"
    )
    editor_screen._toggle_sync_rule(shell.project_editor_state, cache_rule.rule_key, False)
    assert shell.project_editor_state is not None
    editor_screen._sync_rule_path_input.text = "locale_custom"
    editor_screen._sync_rule_description_input.text = "Project locale override"
    editor_screen._sync_rule_filter_type_spinner.text = "Directory"
    editor_screen._sync_rule_behavior_spinner.text = "Include"
    editor_screen._add_sync_rule(shell.project_editor_state)
    editor_screen._save_editor()

    assert shell.project_detail_state is not None
    project_id = shell.project_detail_state.project.id
    shell.open_project_editor_edit(project_id)
    root.current = "project_editor"
    editor_screen.refresh()
    editor_screen._select_project_editor_section("sync")

    assert shell.project_editor_state is not None
    assert "locale_custom" in [
        item.relative_path for item in shell.project_editor_state.editor.sync_rule_items
    ]
    reloaded_cache_rule = next(
        item
        for item in shell.project_editor_state.editor.sync_rule_items
        if item.relative_path == "__pycache__"
    )
    assert reloaded_cache_rule.is_enabled is False
