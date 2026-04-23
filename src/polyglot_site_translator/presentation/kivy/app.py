"""Kivy application bootstrap."""

from __future__ import annotations

import sys
import threading
from types import TracebackType
from typing import Any, cast

from kivy.app import App
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.core.window import Window

from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.root import build_root_widget
from polyglot_site_translator.presentation.kivy.theme import set_active_theme_mode
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    SettingsStateViewModel,
    build_default_app_settings,
    build_settings_state,
)


class PolyglotSiteTranslatorApp(App):  # type: ignore[misc]
    """Thin Kivy application wrapper around the presentation shell."""

    def __init__(self, shell: FrontendShell, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._shell = shell
        self._built_root: Any | None = None
        self._previous_excepthook = sys.excepthook
        self._previous_threading_excepthook = threading.excepthook
        self._runtime_exception_handler = _RuntimeExceptionHandler(self)

    def build(self) -> Any:
        """Build the root widget tree."""
        self.title = "Polyglot Site Translator"
        self._install_runtime_error_handlers()
        self._open_initial_route()
        self._built_root = build_root_widget(self._shell, self.apply_runtime_settings)
        return self._built_root

    def on_stop(self) -> None:
        """Restore global runtime exception hooks on shutdown."""
        ExceptionManager.remove_handler(self._runtime_exception_handler)
        sys.excepthook = self._previous_excepthook
        threading.excepthook = self._previous_threading_excepthook
        super().on_stop()

    def apply_runtime_settings(self, app_settings: AppSettingsViewModel) -> None:
        """Apply runtime Kivy settings after a successful save."""
        set_active_theme_mode(app_settings.theme_mode)
        Window.size = (app_settings.window_width, app_settings.window_height)
        root = self.root or self._built_root
        if root is None:
            return
        for screen in root.screens:
            if hasattr(screen, "apply_theme"):
                screen.apply_theme()
        current_screen = root.current_screen
        if current_screen is not None:
            current_screen.refresh()

    def _open_initial_route(self) -> None:
        """Load persisted frontend settings before choosing the initial route."""
        state = self._load_startup_settings()
        if state is None:
            self._shell.open_dashboard()
            return
        self.apply_runtime_settings(state.app_settings)
        if not state.app_settings.remember_last_screen:
            self._shell.open_dashboard()
            return
        if state.app_settings.last_opened_screen == "settings":
            self._shell.open_settings()
            return
        if state.app_settings.last_opened_screen == "projects":
            self._shell.open_projects()
            return
        self._shell.open_dashboard()

    def _load_startup_settings(self) -> SettingsStateViewModel | None:
        """Load settings for startup without mutating remembered navigation first."""
        try:
            state = self._shell.services.settings.load_settings()
            self._shell.settings_state = state
            self._shell.latest_error = None
        except ControlledServiceError as error:
            state = build_settings_state(
                app_settings=build_default_app_settings(),
                status="failed",
                status_message=str(error),
            )
            self._shell.settings_state = state
            self._shell.latest_error = str(error)
        return self._shell.settings_state

    def _install_runtime_error_handlers(self) -> None:
        """Install app-level exception routing for foreground and background failures."""
        sys.excepthook = self._handle_main_exception
        threading.excepthook = self._handle_thread_exception
        ExceptionManager.add_handler(self._runtime_exception_handler)

    def _handle_main_exception(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        """Route uncaught main-thread exceptions into shell state."""
        if issubclass(exc_type, KeyboardInterrupt | SystemExit):
            self._previous_excepthook(exc_type, exc_value, exc_traceback)
            return
        self._shell.surface_unhandled_runtime_error(
            exc_value,
            context="main thread",
        )

    def _handle_thread_exception(self, args: threading.ExceptHookArgs) -> None:
        """Route uncaught worker-thread exceptions into shell state."""
        if issubclass(args.exc_type, KeyboardInterrupt | SystemExit):
            self._previous_threading_excepthook(args)
            return
        if args.exc_value is None:
            return
        thread_name = None if args.thread is None else args.thread.name
        self._shell.surface_unhandled_runtime_error(
            args.exc_value,
            context=f"background thread '{thread_name or 'unknown'}'",
            thread_name=thread_name,
            traceback=args.exc_traceback,
        )


class _RuntimeExceptionHandler(ExceptionHandler):  # type: ignore[misc]
    """Kivy exception bridge that surfaces callback failures in the shell."""

    def __init__(self, app: PolyglotSiteTranslatorApp) -> None:
        super().__init__()
        self._app = app

    def handle_exception(self, inst: BaseException) -> int:
        if isinstance(inst, KeyboardInterrupt | SystemExit):
            return cast(int, ExceptionManager.RAISE)
        self._app._shell.surface_unhandled_runtime_error(
            inst,
            context="kivy callback",
        )
        return cast(int, ExceptionManager.PASS)
