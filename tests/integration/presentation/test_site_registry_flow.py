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


def test_editing_a_site_persists_remote_connection_configuration(tmp_path: Path) -> None:
    isolated_config_dir = tmp_path / "isolated-config"
    settings_service = build_default_settings_service(config_dir=isolated_config_dir)
    services = build_default_frontend_services(settings_service=settings_service)
    shell = create_kivy_app(services=services)._shell

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
    created_project = shell.projects_state.projects[0]
    shell.open_project_editor_edit(created_project.id)
    assert shell.project_editor_state is not None
    assert shell.project_editor_state.editor.connection_type == "ftp"
    assert shell.project_editor_state.editor.remote_host == "ftp.example.com"

    shell.save_project_edits(
        created_project.id,
        SiteEditorViewModel(
            site_id=created_project.id,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site-v2",
            default_locale="en_US",
            connection_type="ftp",
            remote_host="ftp-v2.example.com",
            remote_port="21",
            remote_username="deployer",
            remote_password="super-secret-v2",
            remote_path="/public_html/v2",
            is_active=True,
        ),
    )

    shell.open_project_editor_edit(created_project.id)

    assert shell.project_editor_state is not None
    assert shell.project_editor_state.editor.local_path == "/workspace/marketing-site-v2"
    assert shell.project_editor_state.editor.connection_type == "ftp"
    assert shell.project_editor_state.editor.remote_host == "ftp-v2.example.com"
    assert shell.project_editor_state.editor.remote_port == "21"
    assert shell.project_editor_state.editor.remote_username == "deployer"
    assert shell.project_editor_state.editor.remote_password == "super-secret-v2"
    assert shell.project_editor_state.editor.remote_path == "/public_html/v2"


def test_site_registry_flow_normalizes_and_persists_default_locale_lists(tmp_path: Path) -> None:
    isolated_config_dir = tmp_path / "isolated-config"
    settings_service = build_default_settings_service(config_dir=isolated_config_dir)
    services = build_default_frontend_services(settings_service=settings_service)
    shell = create_kivy_app(services=services)._shell

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
            default_locale="es_ES, es_AR",
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
    assert "Locale: es_ES,es_AR" in shell.project_detail_state.configuration_summary

    shell.open_projects()
    created_project = shell.projects_state.projects[0]
    shell.open_project_editor_edit(created_project.id)

    assert shell.project_editor_state is not None
    assert shell.project_editor_state.editor.default_locale == "es_ES,es_AR"


def test_site_registry_flow_rejects_invalid_default_locale_lists(tmp_path: Path) -> None:
    isolated_config_dir = tmp_path / "isolated-config"
    settings_service = build_default_settings_service(config_dir=isolated_config_dir)
    services = build_default_frontend_services(settings_service=settings_service)
    shell = create_kivy_app(services=services)._shell

    shell.open_project_editor_create()
    shell.save_new_project(
        SiteEditorViewModel(
            site_id=None,
            name="Marketing Site",
            framework_type="wordpress",
            local_path="/workspace/marketing-site",
            default_locale="asad@",
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="super-secret",
            remote_path="/public_html",
            is_active=True,
        )
    )

    assert shell.project_detail_state is None
    assert shell.project_editor_state is not None
    assert shell.project_editor_state.status == "failed"
    assert (
        shell.project_editor_state.status_message
        == "Default locale must be a valid locale or a comma-separated list of valid "
        "locales. Invalid values: asad@."
    )


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
