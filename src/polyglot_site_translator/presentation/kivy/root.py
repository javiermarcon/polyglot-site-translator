"""Root widget builder for the Kivy shell."""

from __future__ import annotations

from collections.abc import Callable

from kivy.uix.screenmanager import NoTransition, ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.audit import AuditScreen
from polyglot_site_translator.presentation.kivy.screens.dashboard import DashboardScreen
from polyglot_site_translator.presentation.kivy.screens.po_processing import POProcessingScreen
from polyglot_site_translator.presentation.kivy.screens.project_detail import ProjectDetailScreen
from polyglot_site_translator.presentation.kivy.screens.project_editor import ProjectEditorScreen
from polyglot_site_translator.presentation.kivy.screens.projects import ProjectsScreen
from polyglot_site_translator.presentation.kivy.screens.settings import SettingsScreen
from polyglot_site_translator.presentation.kivy.screens.sync import SyncScreen
from polyglot_site_translator.presentation.router import RouteName
from polyglot_site_translator.presentation.view_models import AppSettingsViewModel


def build_root_widget(
    shell: FrontendShell,
    apply_runtime_settings: Callable[[AppSettingsViewModel], None] | None = None,
) -> ScreenManager:
    """Create the ScreenManager used by the Kivy app."""
    manager = ScreenManager(transition=NoTransition())
    screens = [
        DashboardScreen(shell=shell, manager_ref=manager),
        ProjectsScreen(shell=shell, manager_ref=manager),
        ProjectDetailScreen(shell=shell, manager_ref=manager),
        ProjectEditorScreen(shell=shell, manager_ref=manager),
        SyncScreen(shell=shell, manager_ref=manager),
        AuditScreen(shell=shell, manager_ref=manager),
        POProcessingScreen(shell=shell, manager_ref=manager),
        SettingsScreen(
            shell=shell,
            manager_ref=manager,
            apply_runtime_settings=apply_runtime_settings,
        ),
    ]
    for screen in screens:
        manager.add_widget(screen)
    manager.current = _resolve_initial_screen_name(shell)
    return manager


def _resolve_initial_screen_name(shell: FrontendShell) -> str:
    """Map the shell route to the corresponding screen name."""
    route_name = shell.router.current.name
    if route_name is RouteName.PROJECT_DETAIL:
        return "project_detail"
    if route_name is RouteName.PROJECT_EDITOR:
        return "project_editor"
    if route_name is RouteName.PO_PROCESSING:
        return "po_processing"
    return route_name.value
