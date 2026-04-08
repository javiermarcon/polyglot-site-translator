"""Integration tests for framework detection through the project flow."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel


def test_project_flow_detects_wordpress_and_enriches_detail(tmp_path: Path) -> None:
    project_path = tmp_path / "wordpress-site"
    project_path.mkdir()
    (project_path / "wp-config.php").write_text("<?php\n", encoding="utf-8")
    (project_path / "wp-content").mkdir()
    (project_path / "wp-includes").mkdir()
    shell = _build_runtime_shell(tmp_path)

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="customapp",
            local_path=str(project_path),
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

    assert shell.project_detail_state is not None
    assert shell.project_detail_state.project.framework == "WordPress"
    assert "Framework detection:" in shell.project_detail_state.metadata_summary


def test_project_flow_reports_no_framework_detected_for_generic_paths(tmp_path: Path) -> None:
    project_path = tmp_path / "generic-site"
    project_path.mkdir()
    (project_path / "README.txt").write_text("generic project\n", encoding="utf-8")
    shell = _build_runtime_shell(tmp_path)

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Generic Site",
            framework_type="customapp",
            local_path=str(project_path),
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

    assert shell.project_detail_state is not None
    assert shell.project_detail_state.project.framework == "Customapp"
    assert "No framework detected" in shell.project_detail_state.metadata_summary


def test_framework_aware_audit_preview_reports_zero_findings_for_generic_paths(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "generic-site"
    project_path.mkdir()
    (project_path / "README.txt").write_text("generic project\n", encoding="utf-8")
    shell = _build_runtime_shell(tmp_path)

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Generic Site",
            framework_type="customapp",
            local_path=str(project_path),
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
    shell.start_audit()

    assert shell.audit_state is not None
    assert shell.audit_state.findings_count == 0
    assert "No supported framework was detected" in shell.audit_state.findings_summary


def _build_runtime_shell(tmp_path: Path) -> FrontendShell:
    settings_service = build_default_settings_service(config_dir=tmp_path / "config")
    services = build_default_frontend_services(settings_service=settings_service)
    return create_kivy_app(services=services)._shell
