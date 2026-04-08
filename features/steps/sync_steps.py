"""BDD steps for real remote-to-local sync workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
from typing import Any, Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.models import RemoteSyncFile
from polyglot_site_translator.infrastructure.remote_connections.registry import (
    RemoteConnectionRegistry,
)
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
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

    def list_remote_files(self, config: RemoteConnectionConfig) -> list[RemoteSyncFile]:
        host = config.host
        if host in self.failing_hosts:
            msg = self.failing_hosts[host]
            raise OSError(msg)
        return list(self.remote_files_by_host.get(host, []))

    def download_file(self, config: RemoteConnectionConfig, remote_path: str) -> bytes:
        return self.file_contents_by_path[remote_path]


class BehaveSyncContext(Protocol):
    """Typed behave context for sync scenarios."""

    shell: FrontendShell
    sync_provider: ScenarioSyncProvider
    sync_root: Any
    settings_temp_dir: tempfile.TemporaryDirectory[str]
    project_ids: dict[str, str]
    sync_screen: SyncScreen


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
