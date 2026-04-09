"""Tests for the application navigation menu state."""

from __future__ import annotations

from polyglot_site_translator.bootstrap import create_frontend_shell
from tests.support.frontend_doubles import build_seeded_services


def test_navigation_menu_is_grouped_for_future_growth() -> None:
    shell = create_frontend_shell(build_seeded_services())

    navigation_menu = shell.navigation_menu

    section_keys = [section.key for section in navigation_menu.sections]
    assert section_keys == ["workspace", "operations", "system"]
    assert navigation_menu.active_route_key == "dashboard"
    assert [item.key for item in navigation_menu.sections[2].items] == ["settings"]
