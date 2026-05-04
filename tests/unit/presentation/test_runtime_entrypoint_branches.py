"""Branch coverage tests for runtime entrypoint helpers."""

from __future__ import annotations

from dataclasses import replace
import sys
import threading
from types import TracebackType
from typing import Any, cast

from kivy.base import ExceptionManager

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

    shell.router.go_to(RouteName.PROJECT_EDITOR)
    assert _resolve_initial_screen_name(shell) == "project_editor"

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


def test_apply_runtime_settings_is_noop_when_root_is_missing() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)

    app.apply_runtime_settings(build_default_app_settings())


def test_apply_runtime_settings_handles_screens_without_theme_and_missing_current_screen() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)
    screen_with_theme = type(
        "_ScreenWithTheme",
        (),
        {"apply_theme": lambda self: setattr(self, "applied", True)},
    )()
    screen_without_theme = object()
    app._built_root = cast(
        Any,
        type(
            "_Root",
            (),
            {"screens": [screen_with_theme, screen_without_theme], "current_screen": None},
        )(),
    )

    app.apply_runtime_settings(build_default_app_settings())

    assert getattr(screen_with_theme, "applied", False) is True


def test_open_initial_route_honors_settings_and_projects_preferences() -> None:
    settings_service = InMemorySettingsService(
        _saved_settings=replace(
            build_default_app_settings(),
            remember_last_screen=True,
            last_opened_screen="settings",
        )
    )
    settings_shell = create_frontend_shell(build_seeded_services_with_settings(settings_service))
    settings_app = PolyglotSiteTranslatorApp(settings_shell)

    settings_app._open_initial_route()
    assert settings_shell.router.current.name is RouteName.SETTINGS

    projects_settings = InMemorySettingsService(
        _saved_settings=replace(
            build_default_app_settings(),
            remember_last_screen=True,
            last_opened_screen="projects",
        )
    )
    projects_shell = create_frontend_shell(build_seeded_services_with_settings(projects_settings))
    projects_app = PolyglotSiteTranslatorApp(projects_shell)

    projects_app._open_initial_route()
    assert projects_shell.router.current.name is RouteName.PROJECTS


def test_open_initial_route_falls_back_to_dashboard_for_unknown_saved_screen() -> None:
    settings_service = InMemorySettingsService(
        _saved_settings=replace(
            build_default_app_settings(),
            remember_last_screen=True,
            last_opened_screen="unknown-screen",
        )
    )
    shell = create_frontend_shell(build_seeded_services_with_settings(settings_service))
    app = PolyglotSiteTranslatorApp(shell)

    app._open_initial_route()

    assert shell.router.current.name is RouteName.DASHBOARD


def test_on_stop_restores_runtime_handlers() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)
    app.build()
    removed_handlers: list[object] = []
    original_remove_handler = ExceptionManager.remove_handler

    def _capture_remove_handler(handler: object) -> None:
        removed_handlers.append(handler)

    cast(Any, ExceptionManager).remove_handler = _capture_remove_handler
    try:
        app.on_stop()
    finally:
        cast(Any, ExceptionManager).remove_handler = original_remove_handler

    assert removed_handlers == [app._runtime_exception_handler]
    assert sys.excepthook is app._previous_excepthook
    assert threading.excepthook is app._previous_threading_excepthook


def test_main_and_thread_exception_handlers_delegate_interrupts_and_empty_values() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)
    main_calls: list[type[BaseException]] = []
    thread_calls: list[type[BaseException]] = []

    def _capture_main(
        exc_type: type[BaseException],
        _exc_value: BaseException,
        _exc_traceback: TracebackType | None,
    ) -> None:
        main_calls.append(exc_type)

    def _capture_thread(args: threading.ExceptHookArgs) -> None:
        thread_calls.append(args.exc_type)

    app._previous_excepthook = _capture_main
    app._previous_threading_excepthook = _capture_thread

    app._handle_main_exception(KeyboardInterrupt, KeyboardInterrupt(), None)
    app._handle_thread_exception(
        threading.ExceptHookArgs(
            (SystemExit, SystemExit(), None, threading.Thread(name="worker")),
        )
    )
    app._handle_thread_exception(
        threading.ExceptHookArgs(
            (RuntimeError, None, None, threading.Thread(name="worker")),
        )
    )

    assert main_calls == [KeyboardInterrupt]
    assert thread_calls == [SystemExit]


def test_main_exception_handler_surfaces_non_interrupt_errors() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)

    app._handle_main_exception(RuntimeError, RuntimeError("boom"), None)

    assert shell.latest_error == "Unhandled runtime error in main thread. Cause: RuntimeError: boom"


def test_runtime_exception_handler_raises_for_interrupts() -> None:
    shell = create_frontend_shell(build_seeded_services())
    app = PolyglotSiteTranslatorApp(shell)

    result = app._runtime_exception_handler.handle_exception(KeyboardInterrupt())

    assert result == cast(int, ExceptionManager.RAISE)
