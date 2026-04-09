"""BDD steps for real remote-to-local sync workflows."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
import tempfile
import time
from typing import Any, Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

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
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.project_detail import (
    ProjectDetailScreen,
)
from polyglot_site_translator.presentation.kivy.screens.sync import SyncScreen
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel
from polyglot_site_translator.services.project_sync import ProjectSyncService
from polyglot_site_translator.services.remote_connections import RemoteConnectionService

StepFunction = TypeVar("StepFunction", bound=Callable[..., object])

given = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.given)
when = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.when)
then = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.then)


@dataclass
class ScenarioSyncProvider:
    """In-memory provider stub used by sync BDD scenarios."""

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

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        return RemoteConnectionTestResult(
            success=True,
            connection_type=config.connection_type,
            host=config.host,
            port=config.port,
            message="Connected successfully using the behave sync provider.",
            error_code=None,
        )

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
                    message="Listing remote files through the behave sync provider.",
                    command_text=f"SFTP LIST {config.remote_path}",
                )
            )
        host = config.host
        if host in self.failing_hosts:
            msg = self.failing_hosts[host]
            raise OSError(msg)
        return list(self.remote_files_by_host.get(host, []))[:max_files]

    def iter_remote_files(
        self,
        config: RemoteConnectionConfig,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> Iterable[RemoteSyncFile]:
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
                    message=f"Downloading {remote_path} through the behave sync provider.",
                    command_text=f"SFTP GET {remote_path}",
                )
            )
        return self.file_contents_by_path[remote_path]


class BehaveSyncContext(Protocol):
    """Typed behave context for sync scenarios."""

    shell: FrontendShell
    sync_provider: ScenarioSyncProvider
    sync_root: Any
    settings_temp_dir: tempfile.TemporaryDirectory[str]
    project_ids: dict[str, str]
    sync_screen: SyncScreen
    detail_screen: ProjectDetailScreen


def _context(context: object) -> BehaveSyncContext:
    return cast(BehaveSyncContext, context)


@given("the frontend shell is wired with a real sync workflow")
def step_real_sync_shell(context: object) -> None:
    typed_context = _context(context)
    typed_context.settings_temp_dir = tempfile.TemporaryDirectory()
    typed_context.sync_provider = ScenarioSyncProvider()
    typed_context.project_ids = {}
    settings_service = build_default_settings_service(
        config_dir=Path(typed_context.settings_temp_dir.name)
    )
    registry = RemoteConnectionRegistry.default_registry(providers=[typed_context.sync_provider])
    app = create_kivy_app(
        services=build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=RemoteConnectionService(registry=registry),
            project_sync_service=ProjectSyncService(registry=registry),
        )
    )
    typed_context.sync_root = app.build()
    typed_context.shell = app._shell
    typed_context.sync_screen = cast(SyncScreen, typed_context.sync_root.get_screen("sync"))
    typed_context.detail_screen = cast(
        ProjectDetailScreen,
        typed_context.sync_root.get_screen("project_detail"),
    )


@given("the sync command log limit is {limit:d} operations")
def step_set_sync_command_log_limit(context: object, limit: int) -> None:
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
        project_key=project_key,
        local_directory_name="marketing-site",
        connection_type="sftp",
        remote_host="marketing.example.test",
    )


@given('the registered project "{project_key}" has no remote connection')
def step_project_without_remote_connection(context: object, project_key: str) -> None:
    typed_context = _context(context)
    _create_project(
        typed_context,
        project_key=project_key,
        local_directory_name="local-only-site",
        connection_type="none",
        remote_host="",
    )


@given('the registered project "{project_key}" fails while listing the remote files')
def step_project_listing_failure(context: object, project_key: str) -> None:
    typed_context = _context(context)
    typed_context.sync_provider.failing_hosts["broken.example.test"] = (
        "Could not list remote files."
    )
    _create_project(
        typed_context,
        project_key=project_key,
        local_directory_name="broken-remote-site",
        connection_type="sftp",
        remote_host="broken.example.test",
    )


@given('the registered project "{project_key}" has an empty remote source')
def step_project_empty_remote(context: object, project_key: str) -> None:
    typed_context = _context(context)
    typed_context.sync_provider.remote_files_by_host["empty.example.test"] = []
    _create_project(
        typed_context,
        project_key=project_key,
        local_directory_name="empty-remote-site",
        connection_type="sftp",
        remote_host="empty.example.test",
    )


@then("the sync panel reports {downloaded_files:d} downloaded files")
def step_assert_downloaded_files(context: object, downloaded_files: int) -> None:
    typed_context = _context(context)
    assert typed_context.shell.sync_state is not None
    assert typed_context.shell.sync_state.files_synced == downloaded_files


@then('the sync panel reports the sync error code "{error_code}"')
def step_assert_sync_error_code(context: object, error_code: str) -> None:
    typed_context = _context(context)
    assert typed_context.shell.sync_state is not None
    assert typed_context.shell.sync_state.error_code == error_code


@then("the sync screen shows the downloaded file count")
def step_assert_sync_screen(context: object) -> None:
    typed_context = _context(context)
    typed_context.sync_screen.refresh()
    assert "Files: 2" in typed_context.sync_screen._summary_label.text


@when("the operator starts the sync workflow from the project detail screen")
def step_start_sync_from_detail_screen(context: object) -> None:
    typed_context = _context(context)
    typed_context.sync_root.current = "project_detail"
    typed_context.detail_screen._start_sync()


@then("the sync progress window is open")
def step_assert_sync_progress_window_open(context: object) -> None:
    typed_context = _context(context)
    assert typed_context.detail_screen._sync_progress_popup is not None


@then("the sync progress window lists the remote sync commands")
def step_assert_sync_progress_window_commands(context: object) -> None:
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
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        popup.refresh()
        if "SFTP GET /srv/app/locale/es.po" in popup._command_log_label.text:
            break
        time.sleep(0.01)
    assert "SFTP GET /srv/app/locale/es.po" in popup._command_log_label.text


@then("the sync progress window shows a failed status")
def step_assert_sync_progress_window_failed_status(context: object) -> None:
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        popup.refresh()
        if popup._status_label.text == "Status: failed":
            break
        time.sleep(0.01)
    assert popup._status_label.text == "Status: failed"


@then("the sync progress window shows the sync error message")
def step_assert_sync_progress_window_error_message(context: object) -> None:
    typed_context = _context(context)
    popup = typed_context.detail_screen._sync_progress_popup
    assert popup is not None
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        popup.refresh()
        if popup._message_label.text == "Could not list remote files.":
            break
        time.sleep(0.01)
    assert popup._message_label.text == "Could not list remote files."


@then("the sync progress window keeps only the last {limit:d} operations")
def step_assert_sync_progress_window_limit(context: object, limit: int) -> None:
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
            and f"LOCAL WRITE {local_root / 'templates' / 'home.html'}" in command_lines
        ):
            break
        time.sleep(0.01)
    command_lines = [line for line in popup._command_log_label.text.splitlines() if line.strip()]
    assert len(command_lines) == limit
    assert "SFTP LIST /srv/app" not in command_lines
    assert "SFTP GET /srv/app/templates/home.html" in command_lines
    assert f"LOCAL WRITE {local_root / 'templates' / 'home.html'}" in command_lines


def _create_project(
    context: BehaveSyncContext,
    *,
    project_key: str,
    local_directory_name: str,
    connection_type: str,
    remote_host: str,
) -> None:
    local_root = Path(context.settings_temp_dir.name) / "workspace" / local_directory_name
    context.shell.open_project_editor_create()
    context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name=project_key.replace("-", " ").title(),
            framework_type="wordpress",
            local_path=str(local_root),
            default_locale="en_US",
            connection_type=connection_type,
            remote_host=remote_host,
            remote_port="22" if connection_type == "sftp" else "",
            remote_username="deploy" if connection_type == "sftp" else "",
            remote_password="secret" if connection_type == "sftp" else "",
            remote_path="/srv/app" if connection_type == "sftp" else "",
            is_active=True,
        )
    )
    context.shell.open_projects()
    created_project = context.shell.projects_state.projects[-1]
    context.project_ids[project_key] = created_project.id


@when('the operator opens the synced detail for project "{project_id}"')
def step_open_project_detail(context: object, project_id: str) -> None:
    typed_context = _context(context)
    resolved_project_id = typed_context.project_ids.get(project_id, project_id)
    typed_context.shell.open_projects()
    typed_context.shell.select_project(resolved_project_id)
