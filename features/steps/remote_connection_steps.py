"""BDD steps for remote connection workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

from polyglot_site_translator.bootstrap import create_frontend_shell
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
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel
from polyglot_site_translator.services.remote_connections import RemoteConnectionService

StepFunction = TypeVar("StepFunction", bound=Callable[..., object])

given = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.given)
when = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.when)
then = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.then)


@dataclass(frozen=True)
class StubRemoteConnectionProvider:
    """Provider stub used by BDD scenarios."""

    descriptor: RemoteConnectionTypeDescriptor
    result: RemoteConnectionTestResult

    def test_connection(
        self,
        config: RemoteConnectionConfigInput,
    ) -> RemoteConnectionTestResult:
        return RemoteConnectionTestResult(
            success=self.result.success,
            connection_type=config.connection_type,
            host=config.host,
            port=config.port,
            message=self.result.message,
            error_code=self.result.error_code,
        )

    def list_remote_files(
        self,
        config: RemoteConnectionConfig,
    ) -> list[RemoteSyncFile]:
        return []

    def download_file(
        self,
        config: RemoteConnectionConfig,
        remote_path: str,
    ) -> bytes:
        msg = f"download not used in this BDD provider for {remote_path}"
        raise AssertionError(msg)


class BehaveRemoteConnectionContext(Protocol):
    """Typed subset of behave context used by the remote connection feature."""

    shell: FrontendShell
    settings_temp_dir: tempfile.TemporaryDirectory[str]
    remote_connection_service: RemoteConnectionService
    editor_draft: SiteEditorViewModel


def _context(context: object) -> BehaveRemoteConnectionContext:
    return cast(BehaveRemoteConnectionContext, context)


def _rebuild_shell(context: BehaveRemoteConnectionContext) -> None:
    settings_service = build_default_settings_service(
        config_dir=Path(context.settings_temp_dir.name)
    )
    context.shell = create_frontend_shell(
        build_default_frontend_services(
            settings_service=settings_service,
            remote_connection_service=context.remote_connection_service,
        )
    )


@given("the frontend shell is wired with SQLite-backed remote connection services")
def step_remote_connection_shell(context: object) -> None:
    typed_context = _context(context)
    typed_context.settings_temp_dir = tempfile.TemporaryDirectory()
    typed_context.remote_connection_service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(providers=[])
    )
    _rebuild_shell(typed_context)


@given('remote connection tests succeed for "{connection_type}"')
def step_remote_connection_success(context: object, connection_type: str) -> None:
    typed_context = _context(context)
    typed_context.remote_connection_service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[
                StubRemoteConnectionProvider(
                    descriptor=RemoteConnectionTypeDescriptor(
                        connection_type=connection_type,
                        display_name=connection_type.upper(),
                        default_port=22 if connection_type in {"sftp", "scp"} else 21,
                    ),
                    result=RemoteConnectionTestResult(
                        success=True,
                        connection_type=connection_type,
                        host="example.com",
                        port=22 if connection_type in {"sftp", "scp"} else 21,
                        message="Connected successfully.",
                        error_code=None,
                    ),
                )
            ]
        )
    )
    _rebuild_shell(typed_context)


@given('remote connection tests fail for "{connection_type}" with code "{error_code}"')
def step_remote_connection_failure(
    context: object,
    connection_type: str,
    error_code: str,
) -> None:
    typed_context = _context(context)
    typed_context.remote_connection_service = RemoteConnectionService(
        registry=RemoteConnectionRegistry.default_registry(
            providers=[
                StubRemoteConnectionProvider(
                    descriptor=RemoteConnectionTypeDescriptor(
                        connection_type=connection_type,
                        display_name=connection_type.upper(),
                        default_port=21,
                    ),
                    result=RemoteConnectionTestResult(
                        success=False,
                        connection_type=connection_type,
                        host="example.com",
                        port=21,
                        message="Authentication failed.",
                        error_code=error_code,
                    ),
                )
            ]
        )
    )
    _rebuild_shell(typed_context)


@then('the remote connection selector includes the "No Remote Connection" option')
def step_assert_no_remote_option(context: object) -> None:
    typed_context = _context(context)
    typed_context.shell.open_project_editor_create()
    assert typed_context.shell.project_editor_state is not None
    assert typed_context.shell.project_editor_state.connection_type_options[0].label == (
        "No Remote Connection"
    )


@when("the operator submits a new project without remote connection")
def step_submit_without_remote(context: object) -> None:
    typed_context = _context(context)
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Local Project",
            framework_type="unknown",
            local_path="/workspace/local-project",
            default_locale="en_US",
            connection_type="none",
            remote_host="",
            remote_port="",
            remote_username="",
            remote_password="",
            remote_path="",
            is_active=True,
        )
    )


@then("the project detail shows that no remote connection is configured")
def step_assert_no_remote_summary(context: object) -> None:
    typed_context = _context(context)
    assert typed_context.shell.project_detail_state is not None
    assert (
        "Remote connection: None" in typed_context.shell.project_detail_state.configuration_summary
    )


@when('the operator fills a valid "{connection_type}" remote connection draft')
def step_fill_valid_remote_draft(context: object, connection_type: str) -> None:
    typed_context = _context(context)
    typed_context.editor_draft = SiteEditorViewModel(
        site_id=None,
        name="Remote Project",
        framework_type="unknown",
        local_path="/workspace/remote-project",
        default_locale="en_US",
        connection_type=connection_type,
        remote_host="example.com",
        remote_port="22" if connection_type in {"sftp", "scp"} else "21",
        remote_username="deploy",
        remote_password="super-secret",
        remote_path="/srv/app",
        is_active=True,
    )


@when("the operator runs the remote connection test from the editor")
def step_run_remote_connection_test(context: object) -> None:
    typed_context = _context(context)
    typed_context.shell.open_project_editor_create()
    typed_context.shell.test_project_connection(typed_context.editor_draft)


@then("the project editor shows a successful remote connection test result")
def step_assert_successful_remote_test(context: object) -> None:
    typed_context = _context(context)
    assert typed_context.shell.project_editor_state is not None
    assert typed_context.shell.project_editor_state.connection_test_result is not None
    assert typed_context.shell.project_editor_state.connection_test_result.success is True


@then("the project editor shows a failed remote connection test result")
def step_assert_failed_remote_test(context: object) -> None:
    typed_context = _context(context)
    assert typed_context.shell.project_editor_state is not None
    assert typed_context.shell.project_editor_state.connection_test_result is not None
    assert typed_context.shell.project_editor_state.connection_test_result.success is False
