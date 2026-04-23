"""Branch coverage tests for runtime entrypoint helpers."""

from __future__ import annotations

from dataclasses import replace
import threading

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.presentation.kivy.app import PolyglotSiteTranslatorApp
from polyglot_site_translator.presentation.kivy.root import _resolve_initial_screen_name
from polyglot_site_translator.presentation.router import RouteName
from polyglot_site_translator.presentation.view_models import (
    POProcessingSummaryViewModel,
    build_default_app_settings,
)
from tests.support.frontend_doubles import (
    InMemorySettingsService,
    build_failing_settings_load_services,
    build_seeded_services,
    build_seeded_services_with_settings,
)


def test_apply_runtime_settings_refreshes_current_screen_when_root_is_present() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)
    root = app.build()

    app.apply_runtime_settings(build_default_app_settings())

    assert root.current_screen is not None


def test_resolve_initial_screen_name_maps_project_detail_and_po_processing() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.router.go_to(RouteName.PROJECT_DETAIL, project_id="wp-site")
    assert _resolve_initial_screen_name(shell) == "project_detail"

    shell.router.go_to(RouteName.PO_PROCESSING, project_id="wp-site")
    assert _resolve_initial_screen_name(shell) == "po_processing"


def test_set_settings_ui_language_accepts_spanish_value() -> None:
    shell = create_frontend_shell(build_seeded_services())

    shell.open_settings()
    shell.set_settings_ui_language("es")

    assert shell.settings_state is not None
    assert shell.settings_state.app_settings.ui_language == "es"


def test_persist_last_opened_screen_keeps_latest_error_when_settings_save_fails() -> None:
    failing_settings = InMemorySettingsService(
        _saved_settings=replace(
            build_default_app_settings(),
            remember_last_screen=True,
            last_opened_screen="dashboard",
        ),
        fail_save=True,
    )
    shell = create_frontend_shell(build_seeded_services_with_settings(failing_settings))

    shell.open_settings()
    shell.open_dashboard()

    assert shell.latest_error == "App settings could not be saved."


def test_open_initial_route_falls_back_to_dashboard_when_startup_state_is_missing() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)

    app._load_startup_settings = lambda: None  # type: ignore[method-assign]

    app._open_initial_route()

    assert shell.router.current.name is RouteName.DASHBOARD


def test_load_startup_settings_converts_controlled_errors_to_failed_state() -> None:
    shell = create_frontend_shell(build_failing_settings_load_services())
    app = PolyglotSiteTranslatorApp(shell)

    state = app._load_startup_settings()

    assert state is not None
    assert state.status == "failed"
    assert shell.latest_error == "App settings are temporarily unavailable."


def test_handle_thread_exception_surfaces_po_processing_failures() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)
    shell.po_processing_state = POProcessingSummaryViewModel(
        status="running",
        processed_families=1,
        summary="Running.",
        progress_current=2,
        progress_total=5,
        progress_is_indeterminate=False,
        current_file="locale/messages-es_ES.po",
        current_entry="Labels",
    )

    runtime_error = RuntimeError("transport closed")
    worker_thread = threading.Thread(name="po-processing-site-1")
    app._handle_thread_exception(
        threading.ExceptHookArgs(
            (RuntimeError, runtime_error, None, worker_thread),
        )
    )

    assert shell.po_processing_state is not None
    assert shell.po_processing_state.status == "failed"
    assert "transport closed" in shell.po_processing_state.summary
    assert shell.po_processing_state.current_file == "locale/messages-es_ES.po"
    assert shell.po_processing_state.current_entry == "Labels"


def test_runtime_exception_handler_surfaces_kivy_callback_failures() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)
    shell.open_settings()

    result = app._runtime_exception_handler.handle_exception(RuntimeError("boom"))

    assert result == 1
    assert shell.settings_state is not None
    assert shell.settings_state.status == "failed"
    assert shell.settings_state.status_message is not None
    assert "boom" in shell.settings_state.status_message
