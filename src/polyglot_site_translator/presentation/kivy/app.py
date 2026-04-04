"""Kivy application bootstrap."""

from __future__ import annotations

from typing import Any

from kivy.app import App

from polyglot_site_translator.presentation.frontend_shell import FrontendShell
from polyglot_site_translator.presentation.kivy.root import build_root_widget


class PolyglotSiteTranslatorApp(App):  # type: ignore[misc]
    """Thin Kivy application wrapper around the presentation shell."""

    def __init__(self, shell: FrontendShell, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._shell = shell

    def build(self) -> Any:
        """Build the root widget tree."""
        self.title = "Polyglot Site Translator"
        self._shell.open_dashboard()
        return build_root_widget(self._shell)
