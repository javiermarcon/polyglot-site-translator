"""BDD steps for framework detection through the project flow."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tempfile
from typing import Protocol, TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel

StepFunction = TypeVar("StepFunction", bound=Callable[..., object])

given = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.given)
when = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.when)
then = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.then)


class BehaveFrameworkDetectionContext(Protocol):
    """Typed subset of behave context used by framework detection feature."""

    shell: FrontendShell
    project_temp_dir: tempfile.TemporaryDirectory[str]
    settings_temp_dir: tempfile.TemporaryDirectory[str]
    detected_project_path: Path


def _context_with_shell(context: object) -> BehaveFrameworkDetectionContext:
    return cast(BehaveFrameworkDetectionContext, context)


@given(
    "the frontend shell is wired with framework detection and SQLite-backed site registry services"
)
def step_sqlite_site_registry_shell(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.settings_temp_dir = tempfile.TemporaryDirectory()
    typed_context.project_temp_dir = tempfile.TemporaryDirectory()
    settings_service = build_default_settings_service(
        config_dir=Path(typed_context.settings_temp_dir.name)
    )
    typed_context.shell = create_frontend_shell(
        build_default_frontend_services(settings_service=settings_service)
    )


@given("a local WordPress project exists")
def step_local_wordpress_project(context: object) -> None:
    typed_context = _context_with_shell(context)
    project_path = Path(typed_context.project_temp_dir.name) / "wordpress-site"
    project_path.mkdir()
    (project_path / "wp-config.php").write_text("<?php\n", encoding="utf-8")
    (project_path / "wp-content").mkdir()
    (project_path / "wp-includes").mkdir()
    typed_context.detected_project_path = project_path


@given("a local Django project exists")
def step_local_django_project(context: object) -> None:
    typed_context = _context_with_shell(context)
    project_path = Path(typed_context.project_temp_dir.name) / "django-site"
    project_path.mkdir()
    (project_path / "manage.py").write_text("print('manage')\n", encoding="utf-8")
    config_dir = project_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.py").write_text("DEBUG = True\n", encoding="utf-8")
    (config_dir / "wsgi.py").write_text("application = object()\n", encoding="utf-8")
    typed_context.detected_project_path = project_path


@given("a local Flask project exists")
def step_local_flask_project(context: object) -> None:
    typed_context = _context_with_shell(context)
    project_path = Path(typed_context.project_temp_dir.name) / "flask-site"
    project_path.mkdir()
    (project_path / "app.py").write_text(
        "from flask import Flask\napp = Flask(__name__)\n",
        encoding="utf-8",
    )
    (project_path / "babel.cfg").write_text("[python: **.py]\n", encoding="utf-8")
    (project_path / "translations").mkdir()
    typed_context.detected_project_path = project_path


@given("a local generic project exists")
def step_local_generic_project(context: object) -> None:
    typed_context = _context_with_shell(context)
    project_path = Path(typed_context.project_temp_dir.name) / "generic-site"
    project_path.mkdir()
    (project_path / "README.txt").write_text("generic\n", encoding="utf-8")
    typed_context.detected_project_path = project_path


@given("a local project with partial WordPress evidence exists")
def step_local_partial_wordpress_project(context: object) -> None:
    typed_context = _context_with_shell(context)
    project_path = Path(typed_context.project_temp_dir.name) / "partial-wordpress-site"
    project_path.mkdir()
    (project_path / "wp-content").mkdir()
    typed_context.detected_project_path = project_path


@when("the operator registers the local project using the detected path")
def step_register_detected_path(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_create()
    typed_context.shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Detected Project",
            framework_type="customapp",
            local_path=str(typed_context.detected_project_path),
            default_locale="en_US",
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )


@when("the operator starts the audit workflow from the detected project")
def step_start_audit_for_detected_project(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.start_audit()


@when("the operator opens the create project workflow for framework selection")
def step_open_create_project_for_framework_selection(context: object) -> None:
    typed_context = _context_with_shell(context)
    typed_context.shell.open_project_editor_create()


@then('the project detail shows the detected framework "{framework_name}"')
def step_assert_detected_framework(context: object, framework_name: str) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_detail_state is not None
    if typed_context.shell.project_detail_state.project.framework != framework_name:
        raise AssertionError


@then("the project detail shows framework detection evidence")
def step_assert_detection_evidence(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_detail_state is not None
    if "Framework detection:" not in typed_context.shell.project_detail_state.metadata_summary:
        raise AssertionError


@then("the project detail shows that no framework was detected")
def step_assert_no_framework_detected(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_detail_state is not None
    if "No framework detected" not in typed_context.shell.project_detail_state.metadata_summary:
        raise AssertionError


@then("the stored project framework keeps the operator-provided value")
def step_assert_provided_framework_kept(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_detail_state is not None
    if typed_context.shell.project_detail_state.project.framework != "Customapp":
        raise AssertionError


@then("the project detail shows framework detection warnings")
def step_assert_detection_warnings(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_detail_state is not None
    metadata_summary = typed_context.shell.project_detail_state.metadata_summary.lower()
    if "partial wordpress evidence" not in metadata_summary:
        raise AssertionError


@then("the audit preview shows zero framework findings")
def step_assert_zero_framework_findings(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.audit_state is not None
    if typed_context.shell.audit_state.findings_count != 0:
        raise AssertionError


@then("the audit preview explains that no supported framework was detected")
def step_assert_no_framework_detected_in_audit(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.audit_state is not None
    if "No supported framework was detected" not in typed_context.shell.audit_state.findings_summary:
        raise AssertionError


@then("the framework combo shows the auto-discovered supported options")
def step_assert_framework_combo_options(context: object) -> None:
    typed_context = _context_with_shell(context)
    assert typed_context.shell.project_editor_state is not None
    if [
        option.label for option in typed_context.shell.project_editor_state.framework_options
    ] != ["Unknown", "Django", "Flask", "WordPress"]:
        raise AssertionError
