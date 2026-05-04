"""Unit tests for frontend support doubles."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.view_models import SiteEditorViewModel
from tests.support.frontend_doubles import (
    FailingSiteRegistryCatalogService,
    InMemorySettingsService,
    StubProjectWorkflowService,
    build_empty_services,
    build_failing_settings_load_services,
    build_failing_settings_save_services,
    build_failing_sync_services,
    build_seeded_services,
)


def test_catalog_double_returns_detail_and_raises_for_unknown_project() -> None:
    services = build_seeded_services()
    catalog = services.catalog

    detail = catalog.get_project_detail("wp-site")

    assert detail.project.id == "wp-site"
    assert detail.compile_mo is True
    assert detail.use_external_translator is True
    with pytest.raises(LookupError, match="Unknown project id: missing"):
        catalog.get_project_detail("missing")


def test_failing_catalog_double_surfaces_controlled_errors() -> None:
    catalog = FailingSiteRegistryCatalogService()

    with pytest.raises(
        ControlledServiceError,
        match="SQLite site registry is temporarily unavailable",
    ):
        catalog.list_projects()
    with pytest.raises(
        ControlledServiceError,
        match="SQLite site registry is temporarily unavailable for wp-site",
    ):
        catalog.get_project_detail("wp-site")


def test_stub_workflow_double_covers_success_and_fail_sync_branches() -> None:
    workflow = StubProjectWorkflowService()

    assert workflow.start_sync("dj-admin").status == "completed"
    assert workflow.start_sync_to_remote("dj-admin").files_synced == 7
    assert workflow.trust_remote_host_key("dj-admin").success is True
    assert workflow.start_audit("dj-admin").status == "completed"
    assert (
        workflow.start_po_processing(
            "dj-admin",
            locales="es_ES",
            compile_mo=False,
            use_external_translator=False,
        ).status
        == "completed"
    )

    with pytest.raises(
        ControlledServiceError,
        match="Sync preview is unavailable for this project",
    ):
        StubProjectWorkflowService(fail_sync=True).start_sync("wp-site")


def test_in_memory_settings_service_covers_save_load_fail_and_reset() -> None:
    seeded_settings = build_seeded_services().settings.load_settings().app_settings
    service = InMemorySettingsService(_saved_settings=seeded_settings)

    saved = service.save_settings(
        replace(
            service.load_settings().app_settings,
            default_project_locale="es_ES, es_AR",
            default_use_external_translator=False,
        )
    )

    assert saved.app_settings.default_project_locale == "es_ES,es_AR"
    assert saved.app_settings.default_use_external_translator is False
    assert service.reset_settings().status == "defaults-restored"

    with pytest.raises(ControlledServiceError, match="App settings are temporarily unavailable"):
        InMemorySettingsService(
            _saved_settings=saved.app_settings,
            fail_load=True,
        ).load_settings()
    with pytest.raises(ControlledServiceError, match="App settings could not be saved"):
        InMemorySettingsService(
            _saved_settings=saved.app_settings,
            fail_save=True,
        ).save_settings(saved.app_settings)


def test_registry_management_double_covers_create_edit_update_and_preview() -> None:
    services = build_seeded_services()
    registry = services.registry

    create_state = registry.build_create_project_editor()
    assert create_state.mode == "create"

    edit_state = registry.build_edit_project_editor("wp-site")
    assert edit_state.editor.site_id == "wp-site"

    detail = registry.create_project(
        SiteEditorViewModel(
            site_id=None,
            name="New Site",
            framework_type="wordpress",
            local_path="/workspace/new-site",
            default_locale="es_ES",
            connection_type="ftp",
            remote_host="ftp.example.com",
            remote_port="21",
            remote_username="deploy",
            remote_password="secret",
            remote_path="/public_html",
            is_active=False,
            compile_mo=False,
            use_external_translator=False,
        )
    )
    assert "External translator: disabled" in detail.configuration_summary

    updated = registry.update_project(
        "created-site",
        replace(
            create_state.editor,
            name="Updated Site",
            local_path="/workspace/updated-site",
        ),
    )
    assert updated.project.name == "Updated Site"

    assert registry.test_remote_connection(create_state.editor).success is False
    preview = registry.preview_project_editor(create_state.editor, mode="create")
    assert preview.status == "editing"


def test_seeded_service_builders_cover_empty_and_failing_variants() -> None:
    assert build_empty_services().catalog.list_projects() == []
    assert (
        cast(StubProjectWorkflowService, build_failing_sync_services().workflows).fail_sync is True
    )
    with pytest.raises(ControlledServiceError):
        build_failing_settings_load_services().settings.load_settings()
    with pytest.raises(ControlledServiceError):
        build_failing_settings_save_services().settings.save_settings(
            build_seeded_services().settings.load_settings().app_settings
        )
