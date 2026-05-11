"""BDD steps for real sync workflows."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
import tempfile
import time
from typing import Any, Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

from polyglot_site_translator.adapters.framework_registry import (
    FrameworkAdapterRegistry,
)
from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionSessionState,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import (
    RemoteSyncFile,
    SyncProgressEvent,
    SyncProgressStage,
)
from polyglot_site_translator.infrastructure.remote_connections.base import (
    RemoteConnectionOperationError,
)
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.settings import (
    build_default_settings_service,
)
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.project_detail import (
    ProjectDetailScreen,
)
from polyglot_site_translator.presentation.kivy.screens.sync import SyncScreen
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel
from polyglot_site_translator.services.framework_sync_scope import (
    FrameworkSyncScopeService,
)
from polyglot_site_translator.services.project_sync import ProjectSyncService
from polyglot_site_translator.services.remote_connections import RemoteConnectionService

StepFunction = TypeVar("StepFunction", bound=Callable[..., object])

given = cast(
    Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.given
)
when = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.when)
then = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.then)


@dataclass
class ScenarioSyncSession:
    """BDD helper for ScenarioSyncSession.

    Attributes:
        config:
            Documented attribute exposed by this type.
        provider:
            Documented attribute exposed by this type.
        state:
            Documented attribute exposed by this type.
        _connect_emitted:
            Documented attribute exposed by this type.
    """

    config: RemoteConnectionConfig
    provider: ScenarioSyncProvider
    state: RemoteConnectionSessionState = RemoteConnectionSessionState.OPEN
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
                message="Connecting through the behave sync provider session.",
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
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message=(
                        "Listing remote files through the behave sync provider session."
                    ),
                    command_text=f"SFTP LIST {self.config.remote_path}",
                )
            )
        host = self.config.host
        if host in self.provider.failing_hosts_with_error_codes:
            error_code, message = self.provider.failing_hosts_with_error_codes[host]
            raise RemoteConnectionOperationError(
                error_code=error_code,
                message=message,
            )
        if host in self.provider.failing_hosts:
            msg = self.provider.failing_hosts[host]
            raise OSError(msg)
        return iter(self.provider.remote_files_by_host.get(host, []))

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
        """
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message=(
                        f"Downloading {remote_path} through the behave sync session."
                    ),
                    command_text=f"SFTP GET {remote_path}",
                )
            )
        return self.provider.file_contents_by_path[remote_path]

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
        """
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.PREPARING_REMOTE,
                    message=f"Preparing remote directory {remote_path}.",
                    command_text=f"SFTP MKDIR {remote_path}",
                )
            )
        self.provider.created_remote_directories.append(remote_path)
        return 1

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
        if progress_callback is not None:
            self._emit_connect_if_needed(progress_callback)
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.UPLOADING_FILE,
                    message=f"Uploading {remote_path} through the behave sync session.",
                    command_text=f"SFTP PUT {remote_path}",
                )
            )
        host = self.config.host
        if host in self.provider.upload_failing_hosts:
            msg = self.provider.upload_failing_hosts[host]
            raise OSError(msg)
        self.provider.uploaded_file_contents[remote_path] = contents

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
        """
        self.state = RemoteConnectionSessionState.CLOSED
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message="Closing the behave sync provider session.",
                    command_text=f"SFTP CLOSE {self.config.host}:{self.config.port}",
                )
            )


@dataclass
class ScenarioSyncProvider:
    """BDD helper for ScenarioSyncProvider.

    Attributes:
        descriptor:
            Documented attribute exposed by this type.
        remote_files_by_host:
            Documented attribute exposed by this type.
        file_contents_by_path:
            Documented attribute exposed by this type.
        failing_hosts:
            Documented attribute exposed by this type.
        failing_hosts_with_error_codes:
            Documented attribute exposed by this type.
        uploaded_file_contents:
            Documented attribute exposed by this type.
        upload_failing_hosts:
            Documented attribute exposed by this type.
        created_remote_directories:
            Documented attribute exposed by this type.
    """

    descriptor: RemoteConnectionTypeDescriptor = field(
        default_factory=lambda: RemoteConnectionTypeDescriptor(
            connection_type="sftp",
            display_name="SFTP",
            default_port=22,
        )
    )
    remote_files_by_host: dict[str, list[RemoteSyncFile]] = field(default_factory=dict)
    file_contents_by_path: dict[str, bytes] = field(default_factory=dict)
    failing_hosts: dict[str, str] = field(default_factory=dict)
    failing_hosts_with_error_codes: dict[str, tuple[str, str]] = field(
        default_factory=dict
    )
    uploaded_file_contents: dict[str, bytes] = field(default_factory=dict)
    upload_failing_hosts: dict[str, str] = field(default_factory=dict)
    created_remote_directories: list[str] = field(default_factory=list)

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
        """
        return RemoteConnectionTestResult(
            success=True,
            connection_type=config.connection_type,
            host=config.host,
            port=config.port,
            message="Connected successfully using the behave sync provider.",
            error_code=None,
        )

    def open_session(self, config: RemoteConnectionConfig) -> ScenarioSyncSession:
        """Handle open session.

        Args:
            self:
                Value supplied to this callable.
            config:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return ScenarioSyncSession(config=config, provider=self)

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
            RemoteConnectionOperationError:
                Raised when this callable hits the corresponding error path.
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.LISTING_REMOTE,
                    message="Listing remote files through the behave sync provider.",
                    command_text=f"SFTP LIST {config.remote_path}",
                )
            )
        host = config.host
        if host in self.failing_hosts_with_error_codes:
            error_code, message = self.failing_hosts_with_error_codes[host]
            raise RemoteConnectionOperationError(
                error_code=error_code,
                message=message,
            )
        if host in self.failing_hosts:
            msg = self.failing_hosts[host]
            raise OSError(msg)
        return list(self.remote_files_by_host.get(host, []))[:max_files]

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
        """
        if progress_callback is not None:
            progress_callback(
                SyncProgressEvent(
                    stage=SyncProgressStage.DOWNLOADING_FILE,
                    message=(
                        f"Downloading {remote_path} through the behave sync provider."
                    ),
                    command_text=f"SFTP GET {remote_path}",
                )
            )
        return self.file_contents_by_path[remote_path]

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


class BehaveSyncContext(Protocol):
    """BDD helper for BehaveSyncContext.

    Attributes:
        shell:
            Documented attribute exposed by this type.
        sync_provider:
            Documented attribute exposed by this type.
        sync_root:
            Documented attribute exposed by this type.
        settings_temp_dir:
            Documented attribute exposed by this type.
        project_ids:
            Documented attribute exposed by this type.
        sync_screen:
            Documented attribute exposed by this type.
        detail_screen:
            Documented attribute exposed by this type.
    """

    shell: FrontendShell
    sync_provider: ScenarioSyncProvider
    sync_root: Any
    settings_temp_dir: tempfile.TemporaryDirectory[str]
    project_ids: dict[str, str]
    sync_screen: SyncScreen
    detail_screen: ProjectDetailScreen


@dataclass(frozen=True)
class ProjectSetupSpec:
    """BDD helper for ProjectSetupSpec.

    Attributes:
        project_key:
            Documented attribute exposed by this type.
        local_directory_name:
            Documented attribute exposed by this type.
        connection_type:
            Documented attribute exposed by this type.
        remote_host:
            Documented attribute exposed by this type.
        framework_type:
            Documented attribute exposed by this type.
        use_adapter_sync_filters:
            Documented attribute exposed by this type.
    """

    project_key: str
    local_directory_name: str
    connection_type: str
    remote_host: str
    framework_type: str = "wordpress"
    use_adapter_sync_filters: bool = False


class _FailingFrameworkSyncScopeService:
    """BDD helper for FailingFrameworkSyncScopeService.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    @staticmethod
    def resolve_for_site(site: Any) -> Any:
        """Handle resolve for site.

        Args:
            site:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        msg = "broken sync scope"
        raise OSError(msg)


def _context(context: object) -> BehaveSyncContext:
    """Handle context.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return cast(BehaveSyncContext, context)


@given("the frontend shell is wired with a real sync workflow")
def step_real_sync_shell(context: object) -> None:
    """Run the BDD step for real sync shell.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.settings_temp_dir = tempfile.TemporaryDirectory()
    typed_context.sync_provider = ScenarioSyncProvider()
    typed_context.project_ids = {}
    settings_service = build_default_settings_service(
        config_dir=Path(typed_context.settings_temp_dir.name)
    )
    registry = RemoteConnectionRegistry.default_registry(
        providers=[typed_context.sync_provider]
    )
    framework_registry = FrameworkAdapterRegistry.discover_installed()
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=registry),
            project_sync_service=ProjectSyncService(
                registry=registry,
                framework_sync_scope_service=FrameworkSyncScopeService(
                    registry=framework_registry
                ),
            ),
        )
    )
    typed_context.sync_root = app.build()
    typed_context.shell = app._shell
    typed_context.sync_screen = cast(
        SyncScreen, typed_context.sync_root.get_screen("sync")
    )
    typed_context.detail_screen = cast(
        ProjectDetailScreen,
        typed_context.sync_root.get_screen("project_detail"),
    )


@given(
    "the frontend shell is wired with a real sync workflow "
    "and failing adapter sync scope resolution"
)
def step_real_sync_shell_with_failing_scope_resolution(context: object) -> None:
    """Run the BDD step for real sync shell with failing scope resolution.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.settings_temp_dir = tempfile.TemporaryDirectory()
    typed_context.sync_provider = ScenarioSyncProvider()
    typed_context.project_ids = {}
    settings_service = build_default_settings_service(
        config_dir=Path(typed_context.settings_temp_dir.name)
    )
    registry = RemoteConnectionRegistry.default_registry(
        providers=[typed_context.sync_provider]
    )
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=registry),
            project_sync_service=ProjectSyncService(
                registry=registry,
                framework_sync_scope_service=_FailingFrameworkSyncScopeService(),
            ),
        )
    )
    typed_context.sync_root = app.build()
    typed_context.shell = app._shell
    typed_context.sync_screen = cast(
        SyncScreen, typed_context.sync_root.get_screen("sync")
    )
    typed_context.detail_screen = cast(
        ProjectDetailScreen,
        typed_context.sync_root.get_screen("project_detail"),
    )


@given("the sync command log limit is {limit:d} operations")
def step_set_sync_command_log_limit(context: object, limit: int) -> None:
    """Run the BDD step for set sync command log limit.

    Args:
        context:
            Value supplied to this callable.
        limit:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.shell.open_settings()
    assert typed_context.shell.settings_state is not None
    typed_context.shell.update_settings_draft(
        replace(
            typed_context.shell.settings_state.app_settings,
            sync_progress_log_limit=limit,
        )
    )
    typed_context.shell.save_settings()


@given('the registered project "{project_key}" has remote files available')
def step_project_has_remote_files(context: object, project_key: str) -> None:
    """Run the BDD step for project has remote files.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.sync_provider.remote_files_by_host["marketing.example.test"] = [
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
    typed_context.sync_provider.file_contents_by_path.update(
        {
            "/srv/app/locale/es.po": b'msgid "hello"\n',
            "/srv/app/templates/home.html": b"<h1>Hello</h1>\n",
        }
    )
    _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="marketing-site",
            connection_type="sftp",
            remote_host="marketing.example.test",
        ),
    )


@given('the registered project "{project_key}" has local files available for upload')
def step_project_has_local_files_for_upload(context: object, project_key: str) -> None:
    """Run the BDD step for project has local files for upload.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    local_root = _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="marketing-site-upload",
            connection_type="sftp",
            remote_host="upload.example.test",
        ),
    )
    (local_root / "locale").mkdir(parents=True, exist_ok=True)
    (local_root / "templates").mkdir(parents=True, exist_ok=True)
    (local_root / "locale" / "es.po").write_text('msgid "hola"\n', encoding="utf-8")
    (local_root / "templates" / "home.html").write_text(
        "<h1>Hola</h1>\n", encoding="utf-8"
    )


@given(
    'the registered project "{project_key}" has django remote files with excluded paths'
)
def step_project_has_django_remote_files_with_exclusions(
    context: object,
    project_key: str,
) -> None:
    """Run the BDD step for project has django remote files with exclusions.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.sync_provider.remote_files_by_host["django-filtered.example.test"] = [
        RemoteSyncFile(
            remote_path="/srv/app/locale/es.po",
            relative_path="locale/es.po",
            size_bytes=16,
        ),
        RemoteSyncFile(
            remote_path="/srv/app/__pycache__/settings.cpython-312.pyc",
            relative_path="__pycache__/settings.cpython-312.pyc",
            size_bytes=14,
        ),
    ]
    typed_context.sync_provider.file_contents_by_path.update(
        {
            "/srv/app/locale/es.po": b'msgid "hello"\n',
            "/srv/app/__pycache__/settings.cpython-312.pyc": b"compiled",
        }
    )
    _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="django-filtered-sync-site",
            connection_type="sftp",
            remote_host="django-filtered.example.test",
            framework_type="django",
            use_adapter_sync_filters=True,
        ),
    )


@given(
    'the registered project "{project_key}" has django local files with excluded paths'
)
def step_project_has_django_local_files_with_exclusions(
    context: object,
    project_key: str,
) -> None:
    """Run the BDD step for project has django local files with exclusions.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    local_root = _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="django-upload-site",
            connection_type="sftp",
            remote_host="django-upload.example.test",
            framework_type="django",
            use_adapter_sync_filters=True,
        ),
    )
    (local_root / "locale").mkdir(parents=True, exist_ok=True)
    (local_root / "__pycache__").mkdir(parents=True, exist_ok=True)
    (local_root / "locale" / "es.po").write_text('msgid "hola"\n', encoding="utf-8")
    (local_root / "__pycache__" / "settings.cpython-312.pyc").write_bytes(b"compiled")


@given(
    'the registered project "{project_key}" has mixed remote files and '
    "adapter sync filters enabled"
)
def step_project_has_filtered_remote_files(context: object, project_key: str) -> None:
    """Run the BDD step for project has filtered remote files.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.sync_provider.remote_files_by_host["filtered.example.test"] = [
        RemoteSyncFile(
            remote_path="/srv/app/wp-content/themes/theme/style.css",
            relative_path="wp-content/themes/theme/style.css",
            size_bytes=16,
        ),
        RemoteSyncFile(
            remote_path="/srv/app/readme.html",
            relative_path="readme.html",
            size_bytes=14,
        ),
    ]
    typed_context.sync_provider.file_contents_by_path.update(
        {
            "/srv/app/wp-content/themes/theme/style.css": b"body{}\n",
            "/srv/app/readme.html": b"readme\n",
        }
    )
    _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="filtered-sync-site",
            connection_type="sftp",
            remote_host="filtered.example.test",
            use_adapter_sync_filters=True,
        ),
    )


@given(
    'the registered project "{project_key}" has mixed remote files and '
    "adapter sync filters disabled"
)
def step_project_has_full_remote_files(context: object, project_key: str) -> None:
    """Run the BDD step for project has full remote files.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.sync_provider.remote_files_by_host["full.example.test"] = [
        RemoteSyncFile(
            remote_path="/srv/app/wp-content/themes/theme/style.css",
            relative_path="wp-content/themes/theme/style.css",
            size_bytes=16,
        ),
        RemoteSyncFile(
            remote_path="/srv/app/readme.html",
            relative_path="readme.html",
            size_bytes=14,
        ),
    ]
    typed_context.sync_provider.file_contents_by_path.update(
        {
            "/srv/app/wp-content/themes/theme/style.css": b"body{}\n",
            "/srv/app/readme.html": b"readme\n",
        }
    )
    _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="full-sync-site",
            connection_type="sftp",
            remote_host="full.example.test",
            use_adapter_sync_filters=False,
        ),
    )


@given('the registered project "{project_key}" has no remote connection')
def step_project_without_remote_connection(context: object, project_key: str) -> None:
    """Run the BDD step for project without remote connection.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="local-only-site",
            connection_type="none",
            remote_host="",
        ),
    )


@given('the registered project "{project_key}" fails while listing the remote files')
def step_project_listing_failure(context: object, project_key: str) -> None:
    """Run the BDD step for project listing failure.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.sync_provider.failing_hosts["broken.example.test"] = (
        "Could not list remote files."
    )
    _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="broken-remote-site",
            connection_type="sftp",
            remote_host="broken.example.test",
        ),
    )


@given(
    'the registered project "{project_key}" fails because the SSH host key is unknown'
)
def step_project_unknown_ssh_host_key(context: object, project_key: str) -> None:
    """Run the BDD step for project unknown ssh host key.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.sync_provider.failing_hosts_with_error_codes[
        "unknown-ssh.example.test"
    ] = (
        "unknown_ssh_host_key",
        "Server 'unknown-ssh.example.test' not found in known_hosts",
    )
    _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="unknown-ssh-host-site",
            connection_type="sftp",
            remote_host="unknown-ssh.example.test",
        ),
    )


@given('the registered project "{project_key}" has an empty remote source')
def step_project_empty_remote(context: object, project_key: str) -> None:
    """Run the BDD step for project empty remote.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.sync_provider.remote_files_by_host["empty.example.test"] = []
    _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="empty-remote-site",
            connection_type="sftp",
            remote_host="empty.example.test",
        ),
    )


@given('the registered project "{project_key}" fails while uploading local files')
def step_project_upload_failure(context: object, project_key: str) -> None:
    """Run the BDD step for project upload failure.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.sync_provider.upload_failing_hosts["upload-broken.example.test"] = (
        "Upload failed for /srv/app/locale/es.po."
    )
    local_root = _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="broken-upload-site",
            connection_type="sftp",
            remote_host="upload-broken.example.test",
        ),
    )
    (local_root / "locale").mkdir(parents=True, exist_ok=True)
    (local_root / "locale" / "es.po").write_text('msgid "hola"\n', encoding="utf-8")


@given('the registered project "{project_key}" has an empty local source')
def step_project_empty_local_source(context: object, project_key: str) -> None:
    """Run the BDD step for project empty local source.

    Args:
        context:
            Value supplied to this callable.
        project_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    local_root = _create_project(
        typed_context,
        ProjectSetupSpec(
            project_key=project_key,
            local_directory_name="empty-local-site",
            connection_type="sftp",
            remote_host="empty-upload.example.test",
        ),
    )
    local_root.mkdir(parents=True, exist_ok=True)


@then("the sync panel reports {downloaded_files:d} downloaded files")
def step_assert_downloaded_files(context: object, downloaded_files: int) -> None:
    """Run the BDD step for assert downloaded files.

    Args:
        context:
            Value supplied to this callable.
        downloaded_files:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    assert typed_context.shell.sync_state is not None
    assert typed_context.shell.sync_state.files_synced == downloaded_files


@then('the sync panel reports the sync error code "{error_code}"')
def step_assert_sync_error_code(context: object, error_code: str) -> None:
    """Run the BDD step for assert sync error code.

    Args:
        context:
            Value supplied to this callable.
        error_code:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    assert typed_context.shell.sync_state is not None
    assert typed_context.shell.sync_state.error_code == error_code


@then("the sync screen shows the downloaded file count")
def step_assert_sync_screen(context: object) -> None:
    """Run the BDD step for assert sync screen.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.sync_screen.refresh()
    assert "Files: 2" in typed_context.sync_screen._summary_label.text


@then("the sync panel reports {uploaded_files:d} uploaded files")
def step_assert_uploaded_files(context: object, uploaded_files: int) -> None:
    """Run the BDD step for assert uploaded files.

    Args:
        context:
            Value supplied to this callable.
        uploaded_files:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context(context)
    assert typed_context.shell.sync_state is not None
    if typed_context.shell.sync_state.files_synced != uploaded_files:
        raise AssertionError


@then("the sync screen shows the uploaded file count")
def step_assert_sync_screen_uploaded_files(context: object) -> None:
    """Run the BDD step for assert sync screen uploaded files.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context(context)
    typed_context.sync_screen.refresh()
    if "Files: 2" not in typed_context.sync_screen._summary_label.text:
        raise AssertionError


@when("the operator starts the sync workflow from the project detail screen")
def step_start_sync_from_detail_screen(context: object) -> None:
    """Run the BDD step for start sync from detail screen.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.sync_root.current = "project_detail"
    typed_context.detail_screen._start_sync()


@when("the operator starts the local to remote sync workflow")
def step_start_local_to_remote_sync(context: object) -> None:
    """Run the BDD step for start local to remote sync.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    typed_context.shell.start_sync_to_remote()


@then("the sync progress window is open")
def step_assert_sync_progress_window_open(context: object) -> None:
    """Run the BDD step for assert sync progress window open.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    assert typed_context.detail_screen._sync_progress_popup is not None


@then("the sync progress window lists the remote sync commands")
def step_assert_sync_progress_window_commands(context: object) -> None:
    """Run the BDD step for assert sync progress window commands.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        popup.refresh()
        if "SFTP LIST /srv/app" in popup._command_log_label.text:
            break
        time.sleep(0.01)
    assert "SFTP LIST /srv/app" in popup._command_log_label.text


@then("the sync progress window shows file download commands while sync is running")
def step_assert_sync_progress_window_download_commands(context: object) -> None:
    """Run the BDD step for assert sync progress window download commands.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        popup.refresh()
        if "SFTP GET /srv/app/locale/es.po" in popup._command_log_label.text:
            break
        time.sleep(0.01)
    if "SFTP GET /srv/app/locale/es.po" not in popup._command_log_label.text:
        raise AssertionError


@then("the sync progress window shows a failed status")
def step_assert_sync_progress_window_failed_status(context: object) -> None:
    """Run the BDD step for assert sync progress window failed status.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        popup.refresh()
        if popup._status_label.text == "Status: failed":
            break
        time.sleep(0.01)
    if popup._status_label.text != "Status: failed":
        raise AssertionError


@then("the sync progress window shows the sync error message")
def step_assert_sync_progress_window_error_message(context: object) -> None:
    """Run the BDD step for assert sync progress window error message.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    expected_message = (
        "Failed to list remote files for project 'Broken Remote Site' from "
        "sftp broken.example.test:22 at remote path '/srv/app'. "
        "Cause: Could not list remote files."
    )
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        popup.refresh()
        if expected_message in popup._message_label.text:
            break
        time.sleep(0.01)
    if expected_message not in popup._message_label.text:
        raise AssertionError


@then("the sync progress window offers the SSH host-key trust action")
def step_assert_sync_progress_window_host_key_trust_action(context: object) -> None:
    """Run the BDD step for assert sync progress window host key trust action.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        popup.refresh()
        if not popup._trust_host_key_button.disabled:
            break
        time.sleep(0.01)
    if popup._trust_host_key_button.opacity != 1:
        raise AssertionError
    if popup._trust_host_key_button.disabled is not False:
        raise AssertionError


@then("the sync progress window keeps only the last {limit:d} operations")
def step_assert_sync_progress_window_limit(context: object, limit: int) -> None:
    """Run the BDD step for assert sync progress window limit.

    Args:
        context:
            Value supplied to this callable.
        limit:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    assert typed_context.shell.project_detail_state is not None
    deadline = time.monotonic() + 1
    local_root = Path(typed_context.shell.project_detail_state.project.local_path)
    while time.monotonic() < deadline:
        popup.refresh()
        command_lines = [
            line for line in popup._command_log_label.text.splitlines() if line.strip()
        ]
        if (
            len(command_lines) == limit
            and "SFTP CLOSE marketing.example.test:22" in command_lines
        ):
            break
        time.sleep(0.01)
    command_lines = [
        line for line in popup._command_log_label.text.splitlines() if line.strip()
    ]
    assert len(command_lines) == limit
    if "SFTP LIST /srv/app" in command_lines:
        raise AssertionError
    if f"LOCAL WRITE {local_root / 'templates' / 'home.html'}" not in command_lines:
        raise AssertionError
    if "SFTP CLOSE marketing.example.test:22" not in command_lines:
        raise AssertionError


@then("the sync progress window shows a single remote connect command")
def step_assert_single_remote_connect(context: object) -> None:
    """Run the BDD step for assert single remote connect.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        popup.refresh()
        if (
            popup._command_log_label.text.count(
                "SFTP CONNECT marketing.example.test:22"
            )
            == 1
        ):
            break
        time.sleep(0.01)
    if (
        popup._command_log_label.text.count("SFTP CONNECT marketing.example.test:22")
        != 1
    ):
        raise AssertionError


@then("the sync progress window shows a single remote close command")
def step_assert_single_remote_close(context: object) -> None:
    """Run the BDD step for assert single remote close.

    Args:
        context:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        popup.refresh()
        if (
            popup._command_log_label.text.count("SFTP CLOSE marketing.example.test:22")
            == 1
        ):
            break
        time.sleep(0.01)
    if popup._command_log_label.text.count("SFTP CLOSE marketing.example.test:22") != 1:
        raise AssertionError


def _create_project(
    context: BehaveSyncContext,
    spec: ProjectSetupSpec,
) -> Path:
    """Handle create project.

    Args:
        context:
            Value supplied to this callable.
        spec:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    local_root = (
        Path(context.settings_temp_dir.name) / "workspace" / spec.local_directory_name
    )
    context.shell.open_project_editor_create()
    context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name=spec.project_key.replace("-", " ").title(),
            framework_type=spec.framework_type,
            local_path=str(local_root),
            default_locale="en_US",
            connection_type=spec.connection_type,
            remote_host=spec.remote_host,
            remote_port="22" if spec.connection_type == "sftp" else "",
            remote_username="deploy" if spec.connection_type == "sftp" else "",
            remote_password="secret" if spec.connection_type == "sftp" else "",
            remote_path="/srv/app" if spec.connection_type == "sftp" else "",
            is_active=True,
            use_adapter_sync_filters=spec.use_adapter_sync_filters,
        )
    )
    context.shell.open_projects()
    created_project = context.shell.projects_state.projects[-1]
    context.project_ids[spec.project_key] = created_project.id
    return local_root


@when('the operator opens the synced detail for project "{project_id}"')
def step_open_project_detail(context: object, project_id: str) -> None:
    """Run the BDD step for open project detail.

    Args:
        context:
            Value supplied to this callable.
        project_id:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    typed_context = _context(context)
    resolved_project_id = typed_context.project_ids.get(project_id, project_id)
    typed_context.shell.open_projects()
    typed_context.shell.select_project(resolved_project_id)
