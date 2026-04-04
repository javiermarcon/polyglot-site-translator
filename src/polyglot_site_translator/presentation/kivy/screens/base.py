"""Shared Kivy screen helpers."""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager

from polyglot_site_translator.presentation.frontend_shell import FrontendShell


class BaseShellScreen(Screen):  # type: ignore[misc]
    """Shared screen scaffold with basic navigation helpers."""

    def __init__(
        self,
        *,
        screen_name: str,
        title: str,
        shell: FrontendShell,
        manager_ref: ScreenManager,
    ) -> None:
        super().__init__(name=screen_name)
        self._shell = shell
        self._manager_ref = manager_ref
        self._container = BoxLayout(orientation="vertical", spacing=8, padding=12)
        self._title = Label(text=title, size_hint_y=None, height=48)
        self._content = BoxLayout(orientation="vertical", spacing=8)
        self._error_label = Label(text="", size_hint_y=None, height=32)
        self._container.add_widget(self._title)
        self._container.add_widget(self._content)
        self._container.add_widget(self._error_label)
        self.add_widget(self._container)

    def add_nav_button(self, text: str, callback: object) -> None:
        """Add a navigation button to the content area."""
        button = Button(text=text, size_hint_y=None, height=44)
        button.bind(on_release=callback)
        self._content.add_widget(button)

    def update_error_label(self) -> None:
        """Refresh the controlled error area."""
        self._error_label.text = self._shell.latest_error or ""

    def refresh(self) -> None:
        """Refresh screen content when the route changes."""

    def on_pre_enter(self, *args: object) -> None:
        """Refresh content before the screen becomes visible."""
        super().on_pre_enter(*args)
        self.refresh()

    def show_route(self, route_name: str) -> None:
        """Switch the ScreenManager to a given route."""
        self._manager_ref.current = route_name
