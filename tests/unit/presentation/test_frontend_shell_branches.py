"""Additional branch coverage for frontend shell orchestration."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.presentation.contracts import FrontendServices
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.router import RouteName
from polyglot_site_translator.presentation.view_models import (
    ProjectDetailViewModel,
    ProjectEditorStateViewModel,
    ProjectSummaryViewModel,
    RemoteConnectionTestResultViewModel,
    SettingsStateViewModel,
    SiteEditorViewModel,
    build_default_app_settings,
)
from tests.support.frontend_doubles import (
    InMemoryProjectCatalogService,
    InMemoryProjectRegistryManagementService,
    InMemorySettingsService,
    StubProjectWorkflowService,
    build_seeded_services,
)


class ResetFailingSettingsService(InMemorySettingsService):
    """Settings fake that fails on reset for branch coverage."""

    def reset_settings(self) -> SettingsStateViewModel:
        msg = "Settings defaults are temporarily unavailable."
        raise ControlledServiceError(msg)


class FailingCatalogService:
    """Catalog fake that fails on both list and detail requests."""

    def list_projects(self) -> list[ProjectSummaryViewModel]:
        msg = "SQLite site registry is temporarily unavailable."
        raise ControlledServiceError(msg)

    def get_project_detail(self, project_id: str) -> ProjectDetailViewModel:
        msg = f"SQLite site registry is temporarily unavailable for {project_id}."
        raise ControlledServiceError(msg)


class FailingRegistryService:
    """Registry fake that fails on create/edit workflows."""

    def build_create_project_editor(self) -> ProjectEditorStateViewModel:
        msg = "Create workflow unavailable."
        raise ControlledServiceError(msg)

    def build_edit_project_editor(self, project_id: str) -> ProjectEditorStateViewModel:
        msg = f"Edit workflow unavailable for {project_id}."
        raise ControlledServiceError(msg)

    def create_project(self, editor: SiteEditorViewModel) -> ProjectDetailViewModel:
        msg = f"Project could not be created for {editor.name}."
        raise ControlledServiceError(msg)

    def update_project(
        self,
        project_id: str,
        editor: SiteEditorViewModel,
    ) -> ProjectDetailViewModel:
        msg = f"Project could not be updated for {project_id}."
        raise ControlledServiceError(msg)

    def test_remote_connection(
        self,
        editor: SiteEditorViewModel,
    ) -> RemoteConnectionTestResultViewModel:
        msg = f"Remote connection test unavailable for {editor.name}."
        raise ControlledServiceError(msg)

    def preview_project_editor(
        self,
        editor: SiteEditorViewModel,
        *,
        mode: str,
    ) -> ProjectEditorStateViewModel:
        msg = f"Project editor preview unavailable for {mode}:{editor.name}."
        raise ControlledServiceError(msg)


def test_open_application_menu_marks_navigation_state_as_open() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_application_menu()

    assert shell.navigation_menu.is_open is True


def test_open_route_from_menu_dispatches_supported_routes() -> None:
    shell = create_frontend_shell(build_seeded_services())
    shell.open_route_from_menu("dashboard")
    assert shell.router.current.name.value == "dashboard"

    shell = create_frontend_shell(build_seeded_services())
    shell.open_route_from_menu("projects")
    assert shell.router.current.name.value == "projects"

    shell = create_frontend_shell(build_seeded_services())
    shell.open_projects()
    shell.select_project("wp-site")
    shell.open_route_from_menu("settings")
    assert shell.router.current.name.value == "settings"

    shell = create_frontend_shell(build_seeded_services())
    shell.open_projects()
    shell.select_project("wp-site")
    shell.open_route_from_menu("sync")
    assert shell.router.current.name.value == "sync"

    shell = create_frontend_shell(build_seeded_services())
    shell.open_projects()
    shell.select_project("wp-site")
    shell.open_route_from_menu("audit")
    assert shell.router.current.name.value == "audit"

    shell = create_frontend_shell(build_seeded_services())
    shell.open_projects()
    shell.select_project("wp-site")
    shell.open_route_from_menu("po-processing")
    assert shell.router.current.name.value == "po-processing"


def test_open_route_from_menu_rejects_unknown_routes() -> None:
    shell = create_frontend_shell(build_seeded_services())

    with pytest.raises(ValueError, match="Unsupported route key: reports"):
        shell.open_route_from_menu("reports")


def test_settings_validators_reject_invalid_values() -> None:
    shell = create_frontend_shell(build_seeded_services())
    shell.open_settings()

    with pytest.raises(ValueError, match="Unsupported theme mode: neon"):
        shell.set_settings_theme_mode("neon")

    with pytest.raises(ValueError, match=r"Window dimensions must be positive integers\."):
        shell.set_settings_window_size(width=0, height=720)

    with pytest.raises(ValueError, match="Unsupported UI language: fr"):
        shell.set_settings_ui_language("fr")


def test_update_settings_draft_keeps_selected_settings_section() -> None:
    shell = create_frontend_shell(build_seeded_services())
    shell.open_settings()
    shell.select_settings_section("translation")

    shell.update_settings_draft(
        replace(
            build_default_app_settings(),
            theme_mode="dark",
            window_width=1440,
            window_height=900,
        )
    )

    assert shell.settings_state is not None
    assert shell.settings_state.selected_section_key == "translation"
    assert shell.settings_state.status == "editing"


def test_restore_default_settings_failure_keeps_failed_state() -> None:
    seeded_services = build_seeded_services()
    services = FrontendServices(
        catalog=seeded_services.catalog,
        workflows=seeded_services.workflows,
        settings=ResetFailingSettingsService(_saved_settings=build_default_app_settings()),
        registry=InMemoryProjectRegistryManagementService(
            catalog=cast(InMemoryProjectCatalogService, seeded_services.catalog),
        ),
    )
    shell = create_frontend_shell(services)
    shell.open_settings()

    shell.restore_default_settings()

    assert shell.settings_state is not None
    assert shell.settings_state.status == "failed"
    assert shell.latest_error == "Settings defaults are temporarily unavailable."


def test_project_context_falls_back_to_loaded_detail_when_route_has_no_project_id() -> None:
    shell = create_frontend_shell(build_seeded_services())
    shell.open_projects()
    shell.select_project("wp-site")
    shell.open_dashboard()

    shell.start_sync()

    assert shell.router.current.name is RouteName.SYNC
    assert shell.router.current.project_id == "wp-site"


def test_project_context_is_required_before_running_workflows() -> None:
    shell = create_frontend_shell(build_seeded_services())

    with pytest.raises(
        ValueError,
        match=r"A project must be selected before running workflows\.",
    ):
        shell.start_sync()


def test_settings_state_is_required_before_editing() -> None:
    shell = create_frontend_shell(build_seeded_services())

    with pytest.raises(ValueError, match=r"Settings must be loaded before editing them\."):
        shell.toggle_remember_last_screen()


def test_has_project_context_is_false_without_detail_or_route_project() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_dashboard()

    assert shell.navigation_menu.sections[1].items[0].is_enabled is False


def test_fake_catalog_raises_lookup_error_for_unknown_project() -> None:
    catalog = InMemoryProjectCatalogService(
        projects=build_seeded_services().catalog.list_projects()
    )

    with pytest.raises(LookupError, match="Unknown project id: missing-site"):
        catalog.get_project_detail("missing-site")


def test_project_workflow_fake_can_sync_non_wp_site_without_failure() -> None:
    workflow = StubProjectWorkflowService(fail_sync=True)

    sync_state = workflow.start_sync("dj-admin")

    assert sync_state.status == "completed"


def test_shell_wraps_project_catalog_failures_and_registry_failures() -> None:
    seeded_services = build_seeded_services()
    shell = create_frontend_shell(
        FrontendServices(
            catalog=FailingCatalogService(),
            workflows=seeded_services.workflows,
            settings=seeded_services.settings,
            registry=FailingRegistryService(),
        )
    )

    shell.open_projects()
    assert shell.projects_state.projects == []
    assert shell.latest_error == "SQLite site registry is temporarily unavailable."

    shell.select_project("missing-site")
    assert shell.project_detail_state is None
    assert shell.latest_error == "SQLite site registry is temporarily unavailable for missing-site."

    shell.open_project_editor_create()
    assert shell.project_editor_state is None
    assert shell.latest_error == "Create workflow unavailable."

    shell.open_project_editor_edit("wp-site")
    assert shell.project_editor_state is None
    assert shell.latest_error == "Edit workflow unavailable for wp-site."


def test_shell_handles_project_editor_failures_and_missing_editor_state() -> None:
    seeded_services = build_seeded_services()
    shell = create_frontend_shell(
        FrontendServices(
            catalog=seeded_services.catalog,
            workflows=seeded_services.workflows,
            settings=seeded_services.settings,
            registry=FailingRegistryService(),
        )
    )

    with pytest.raises(
        ValueError,
        match=r"Project editor state must be loaded before editing\.",
    ):
        shell.save_new_project(
            SiteEditorViewModel(
                site_id=None,
                name="New Site",
                framework_type="wordpress",
                local_path="/workspace/new-site",
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

    shell.project_editor_state = seeded_services.registry.build_create_project_editor()
    editor = shell.project_editor_state.editor
    shell.save_new_project(editor)
    assert shell.project_editor_state is not None
    assert shell.project_editor_state.status == "failed"
    assert shell.router.current.name is RouteName.PROJECT_EDITOR

    shell.project_editor_state = seeded_services.registry.build_edit_project_editor("wp-site")
    shell.save_project_edits("wp-site", shell.project_editor_state.editor)
    assert shell.project_editor_state is not None
    assert shell.project_editor_state.status == "failed"
    assert shell.router.current.project_id == "wp-site"


def test_shell_previews_project_editor_drafts_and_surfaces_failures() -> None:
    services = build_seeded_services()
    shell = create_frontend_shell(services)
    shell.open_project_editor_create()
    assert shell.project_editor_state is not None

    preview_editor = replace(
        shell.project_editor_state.editor,
        framework_type="django",
        use_adapter_sync_filters=True,
    )
    shell.preview_project_editor(preview_editor)

    assert shell.project_editor_state is not None
    assert shell.project_editor_state.editor.framework_type == "django"
    assert shell.project_editor_state.status == "editing"

    failing_shell = create_frontend_shell(
        FrontendServices(
            catalog=services.catalog,
            workflows=services.workflows,
            settings=services.settings,
            registry=FailingRegistryService(),
        )
    )
    failing_shell.project_editor_state = services.registry.build_create_project_editor()
    failing_shell.preview_project_editor(preview_editor)

    assert failing_shell.project_editor_state is not None
    assert failing_shell.project_editor_state.status == "failed"
    assert "Project editor preview unavailable" in str(
        failing_shell.project_editor_state.status_message
    )
