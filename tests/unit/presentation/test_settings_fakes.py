"""Tests for settings contracts and fake persistence."""

from __future__ import annotations

from polyglot_site_translator.presentation.contracts import SettingsService
from tests.support.frontend_doubles import build_seeded_services


def test_fake_settings_service_matches_contract() -> None:
    services = build_seeded_services()

    settings_service: SettingsService = services.settings
    settings_state = settings_service.load_settings()

    assert settings_state.selected_section_key == "app-ui-kivy"
    assert settings_state.app_settings.window_width == 1280
    assert len(settings_state.sections) >= 3
