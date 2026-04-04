"""Root widget builder for the Kivy shell."""

from __future__ import annotations

from kivy.uix.screenmanager import NoTransition, ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.screens.audit import AuditScreen
from polyglot_site_translator.presentation.kivy.screens.dashboard import DashboardScreen
from polyglot_site_translator.presentation.kivy.screens.po_processing import POProcessingScreen
from polyglot_site_translator.presentation.kivy.screens.project_detail import ProjectDetailScreen
from polyglot_site_translator.presentation.kivy.screens.projects import ProjectsScreen
from polyglot_site_translator.presentation.kivy.screens.sync import SyncScreen


def build_root_widget(shell: FrontendShell) -> ScreenManager:
    """Create the ScreenManager used by the Kivy app."""
    manager = ScreenManager(transition=NoTransition())
    screens = [
        DashboardScreen(shell=shell, manager_ref=manager),
        ProjectsScreen(shell=shell, manager_ref=manager),
        ProjectDetailScreen(shell=shell, manager_ref=manager),
        SyncScreen(shell=shell, manager_ref=manager),
        AuditScreen(shell=shell, manager_ref=manager),
        POProcessingScreen(shell=shell, manager_ref=manager),
    ]
    for screen in screens:
        manager.add_widget(screen)
    manager.current = "dashboard"
    return manager
