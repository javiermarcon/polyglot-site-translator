"""Additional branch coverage for frontend shell orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any, cast

import pytest

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.domain.po_processing.models import POProcessingProgress
from polyglot_site_translator.domain.sync.models import SyncProgressEvent, SyncProgressStage
from polyglot_site_translator.presentation import frontend_shell as frontend_shell_module
from polyglot_site_translator.presentation.contracts import FrontendServices
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.router import RouteName
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    AuditSummaryViewModel,
    POProcessingSummaryViewModel,
    ProjectDetailViewModel,
    ProjectEditorStateViewModel,
    ProjectSummaryViewModel,
    RemoteConnectionTestResultViewModel,
    SettingsStateViewModel,
    SiteEditorViewModel,
    SyncProgressStateViewModel,
    SyncStatusViewModel,
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


class FailingAuditAndPOWorkflowService(StubProjectWorkflowService):
    """Workflow fake that fails on audit and PO processing."""

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        msg = f"Audit failed for {project_id}."
        raise ControlledServiceError(msg)

    def start_po_processing(
        self,
        project_id: str,
        locales: str | None = None,
        compile_mo: bool | None = None,
        use_external_translator: bool | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        del locales, compile_mo, use_external_translator, progress_callback
        msg = f"PO processing failed for {project_id}."
        raise ControlledServiceError(msg)


class FailingSaveSettingsService(InMemorySettingsService):
    """Settings fake that fails on save for route-persistence coverage."""

    def save_settings(self, app_settings: AppSettingsViewModel) -> SettingsStateViewModel:
        del app_settings
        msg = "Last opened screen could not be persisted."
        raise ControlledServiceError(msg)


class _AliveThread:
    def is_alive(self) -> bool:
        return True


class _CapturedThread:
    def __init__(self, *args: object, name: str, **kwargs: object) -> None:
        del args, kwargs
        self.name = name
        self.started = False

    def is_alive(self) -> bool:
        return False

    def start(self) -> None:
        self.started = True


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


def test_shell_surfaces_audit_and_po_failures_without_raising() -> None:
    seeded_services = build_seeded_services()
    shell = create_frontend_shell(
        FrontendServices(
            catalog=seeded_services.catalog,
            workflows=FailingAuditAndPOWorkflowService(),
            settings=seeded_services.settings,
            registry=seeded_services.registry,
        )
    )
    shell.open_projects()
    shell.select_project("wp-site")

    shell.start_audit()
    assert shell.audit_state is not None
    assert shell.audit_state.status == "failed"
    assert shell.audit_state.findings_summary == "Audit failed for wp-site."
    assert shell.latest_error == "Audit failed for wp-site."

    shell.start_po_processing()
    assert shell.po_processing_state is not None
    assert shell.po_processing_state.status == "failed"
    assert shell.po_processing_state.summary == "PO processing failed for wp-site."
    assert shell.latest_error == "PO processing failed for wp-site."


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


def test_frontend_shell_covers_runtime_helper_and_error_branches() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.surface_unhandled_runtime_error(RuntimeError("general boom"), context="callback")
    assert shell.latest_error is not None

    shell.open_projects()
    shell.select_project("wp-site")
    shell.start_audit()
    shell._set_route(RouteName.AUDIT, project_id="wp-site")
    shell.surface_unhandled_runtime_error(RuntimeError("audit boom"), context="audit")
    assert shell.audit_state is not None
    assert shell.audit_state.status == "failed"

    shell.open_settings()
    shell.surface_unhandled_runtime_error(RuntimeError("settings boom"), context="settings")
    assert shell.settings_state is not None
    assert shell.settings_state.status == "failed"

    shell.open_project_editor_create()
    shell.surface_unhandled_runtime_error(RuntimeError("editor boom"), context="editor")
    assert shell.project_editor_state is not None
    assert shell.project_editor_state.status == "failed"


def test_frontend_shell_sync_progress_helpers_cover_completed_failed_and_runtime_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = create_frontend_shell(build_seeded_services())
    shell.open_projects()
    shell.select_project("wp-site")

    shell.sync_progress_state = None
    shell._record_sync_progress_event(
        SyncProgressEvent(stage=SyncProgressStage.COMPLETED, message="ignored")
    )

    shell.sync_progress_state = SyncProgressStateViewModel(
        project_id="wp-site",
        project_name="Marketing Site",
        status="running",
        message="Running",
        progress_current=0,
        progress_total=0,
        progress_is_indeterminate=True,
        command_log_limit=2,
        command_log=[],
    )
    shell._record_sync_progress_event(
        SyncProgressEvent(
            stage=SyncProgressStage.COMPLETED,
            message="done",
            total_files=3,
            files_downloaded=3,
        )
    )
    assert shell.sync_progress_state is not None
    assert shell.sync_progress_state.status == "completed"

    shell._record_sync_progress_event(
        SyncProgressEvent(stage=SyncProgressStage.FAILED, message="failed")
    )
    assert shell.sync_progress_state.status == "failed"

    shell._surface_background_sync_failure(RuntimeError("broken transport"))
    assert shell.sync_state is not None
    assert shell.sync_state.error_code == "sync_runtime_failure"

    shell.sync_progress_state = SyncProgressStateViewModel(
        project_id="wp-site",
        project_name="Marketing Site",
        status="running",
        message="Running",
        progress_current=1,
        progress_total=1,
        progress_is_indeterminate=False,
        command_log_limit=2,
        command_log=[],
    )
    shell.sync_state = None
    monkeypatch.setattr(shell, "_run_sync", lambda **_kwargs: None)

    def _unused_workflow(
        _project_id: str,
        _progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        msg = "This workflow should not be used directly."
        raise AssertionError(msg)

    shell._run_sync_in_background("wp-site", _unused_workflow)
    assert shell._active_sync_thread is None


def test_frontend_shell_requirement_and_persist_helpers_cover_remaining_branches() -> None:
    shell = create_frontend_shell(build_seeded_services())

    with pytest.raises(ValueError, match="Settings must be loaded before editing them"):
        shell._require_settings_state()
    with pytest.raises(ValueError, match="Project editor state must be loaded before editing"):
        shell._require_project_editor_state()
    with pytest.raises(ValueError, match="A project must be selected before running workflows"):
        shell._require_project_id()

    shell.settings_state = None
    shell._persist_last_opened_screen(RouteName.DASHBOARD)

    shell.open_settings()
    state = cast(SettingsStateViewModel, shell.settings_state)
    shell.settings_state = replace(state, status="failed")
    shell._persist_last_opened_screen(RouteName.DASHBOARD)
    failed_state = shell.settings_state
    shell.settings_state = replace(
        failed_state,
        status="loaded",
        app_settings=replace(failed_state.app_settings, remember_last_screen=False),
    )
    shell._persist_last_opened_screen(RouteName.DASHBOARD)


def test_frontend_shell_covers_remaining_po_route_and_settings_update_branches() -> None:
    seeded_services = build_seeded_services()
    services = FrontendServices(
        catalog=seeded_services.catalog,
        workflows=seeded_services.workflows,
        settings=FailingSaveSettingsService(_saved_settings=build_default_app_settings()),
        registry=seeded_services.registry,
    )
    shell = create_frontend_shell(services)
    shell.open_settings()
    assert shell.settings_state is not None

    shell.set_settings_database_directory("/tmp/polyglot")
    shell.set_settings_database_filename("app.sqlite3")
    shell.set_settings_ui_language("es")
    assert shell.settings_state.app_settings.database_directory == "/tmp/polyglot"
    assert shell.settings_state.app_settings.database_filename == "app.sqlite3"
    assert shell.settings_state.app_settings.ui_language == "es"

    shell.select_settings_section("ftp-reporting")
    assert shell.settings_state.selected_section_key == "ftp-reporting"
    assert (
        shell.settings_state.status_message == "FTP / Reporting Settings will be available later."
    )

    shell.settings_state = replace(
        shell.settings_state,
        app_settings=replace(shell.settings_state.app_settings, remember_last_screen=True),
    )
    shell._persist_last_opened_screen(RouteName.DASHBOARD)
    assert shell.latest_error == "Last opened screen could not be persisted."

    shell.po_processing_state = None
    shell._record_po_processing_progress(
        POProcessingProgress(
            processed_families=1,
            completed_entries=1,
            total_entries=1,
            files_discovered=1,
            entries_synchronized=0,
            entries_translated=1,
            entries_failed=0,
            message="done",
            current_file="file.po",
            current_entry="Save",
        )
    )

    shell.surface_unhandled_runtime_error(
        RuntimeError("po thread boom"),
        context="worker",
        thread_name="po-processing-wp-site",
    )
    po_state = cast(POProcessingSummaryViewModel, shell.po_processing_state)
    assert po_state.status == "failed"

    shell.sync_progress_state = None
    shell.surface_unhandled_runtime_error(
        RuntimeError("sync thread boom"),
        context="worker",
        thread_name="sync-wp-site",
    )
    sync_state = cast(SyncStatusViewModel, shell.sync_state)
    assert sync_state.status == "failed"

    shell.router.go_to(RouteName.PO_PROCESSING, project_id="wp-site")
    shell.po_processing_state = None
    assert shell._surface_unhandled_route_error("route po boom") is True
    route_po_state = cast(POProcessingSummaryViewModel, shell.po_processing_state)
    assert route_po_state.summary == "route po boom"

    shell.router.go_to(RouteName.SYNC, project_id="wp-site")
    shell.sync_progress_state = None
    shell.surface_unhandled_runtime_error(RuntimeError("sync route boom"), context="sync")
    sync_route_state = cast(SyncStatusViewModel, shell.sync_state)
    assert sync_route_state.summary.endswith("sync route boom")


def test_frontend_shell_covers_thread_short_circuits_and_success_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell = create_frontend_shell(build_seeded_services())
    shell.open_projects()
    shell.select_project("wp-site")

    shell._active_po_processing_thread = cast(Any, _AliveThread())
    shell.start_po_processing_async("es_ES")
    assert shell.po_processing_state is None

    shell.project_detail_state = None
    shell.router.go_to(RouteName.PROJECT_DETAIL, project_id="wp-site")
    monkeypatch.setattr(frontend_shell_module, "Thread", _CapturedThread)

    def _unused_sync_workflow(
        _project_id: str,
        _progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        return SyncStatusViewModel(
            status="completed",
            files_synced=0,
            summary="unused",
            error_code=None,
        )

    shell._start_sync_async_with_message(
        run_workflow=_unused_sync_workflow,
        initial_message="Starting remote sync.",
    )
    sync_progress_state = cast(SyncProgressStateViewModel, shell.sync_progress_state)
    assert sync_progress_state.project_name == "wp-site"

    shell.open_project_editor_edit("wp-site")
    project_editor_state = cast(ProjectEditorStateViewModel, shell.project_editor_state)
    shell.project_editor_state = replace(project_editor_state, selected_section_key="remote")
    editor = replace(project_editor_state.editor, remote_host="ftp.example.com")
    shell.latest_error = "stale error"
    shell.test_project_connection(editor)
    assert shell.latest_error is None


def test_frontend_shell_updates_existing_progress_states_for_runtime_errors() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.po_processing_state = POProcessingSummaryViewModel(
        status="running",
        processed_families=1,
        progress_current=1,
        progress_total=2,
        progress_is_indeterminate=True,
        summary="running",
        current_file="file.po",
        current_entry="Save",
    )
    shell.surface_unhandled_runtime_error(
        RuntimeError("po replace boom"),
        context="worker",
        thread_name="po-processing-wp-site",
    )
    assert shell.po_processing_state.summary.endswith("po replace boom")

    shell.sync_progress_state = SyncProgressStateViewModel(
        project_id="wp-site",
        project_name="Marketing Site",
        status="running",
        message="Running",
        progress_current=0,
        progress_total=0,
        progress_is_indeterminate=True,
        command_log_limit=2,
        command_log=[],
    )
    shell.surface_unhandled_runtime_error(
        RuntimeError("sync replace boom"),
        context="worker",
        thread_name="sync-wp-site",
    )
    updated_sync_progress_state = shell.sync_progress_state
    assert updated_sync_progress_state.status == "failed"
