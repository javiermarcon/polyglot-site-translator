"""Public application entrypoints."""

from __future__ import annotations

from polyglot_site_translator.bootstrap import create_frontend_shell
from polyglot_site_translator.infrastructure.settings import build_default_settings_service
from polyglot_site_translator.presentation.contracts import FrontendServices
from polyglot_site_translator.presentation.fakes import build_seeded_services_with_settings
from polyglot_site_translator.presentation.kivy.app import PolyglotSiteTranslatorApp


def create_kivy_app(
    services: FrontendServices | None = None,
) -> PolyglotSiteTranslatorApp:
    """Build the Kivy app with injectable presentation services."""
    resolved_services = services or build_seeded_services_with_settings(
        settings_service=build_default_settings_service()
    )
    shell = create_frontend_shell(resolved_services)
    return PolyglotSiteTranslatorApp(shell)
