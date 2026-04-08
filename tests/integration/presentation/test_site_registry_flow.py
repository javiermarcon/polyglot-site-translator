"""Integration tests for the real SQLite-backed site registry flow."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.app import create_kivy_app
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.presentation.fakes import build_default_frontend_services
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel


def test_projects_flow_uses_the_real_sqlite_site_registry(tmp_path: Path) -> None:
    isolated_config_dir = tmp_path / "isolated-config"
    settings_service = build_default_settings_service(config_dir=isolated_config_dir)
    services = build_default_frontend_services(settings_service=settings_service)
    shell = create_kivy_app(services=services)._shell

    shell.open_projects()
    assert shell.projects_state.projects == []

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
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

    shell.open_projects()
    assert [project.name for project in shell.projects_state.projects] == ["Marketing Site"]

    created_project = shell.projects_state.projects[0]
    shell.select_project(created_project.id)
    assert shell.project_detail_state is not None
    assert shell.project_detail_state.project.local_path == "/workspace/marketing-site"


def test_settings_flow_persists_database_directory_and_filename(tmp_path: Path) -> None:
    isolated_config_dir = tmp_path / "isolated-config"
    settings_service = build_default_settings_service(config_dir=isolated_config_dir)
    services = build_default_frontend_services(settings_service=settings_service)
    shell = create_kivy_app(services=services)._shell

    shell.open_settings()
    shell.set_settings_database_directory("/tmp/polyglot-db")
    shell.set_settings_database_filename("registry.sqlite3")
    shell.save_settings()
    shell.open_settings()

    assert shell.settings_state is not None
    assert shell.settings_state.app_settings.database_directory == "/tmp/polyglot-db"
    assert shell.settings_state.app_settings.database_filename == "registry.sqlite3"
