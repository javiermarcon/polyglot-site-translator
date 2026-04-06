"""Additional tests for presentation view model builders."""

from __future__ import annotations

import pytest

from polyglot_site_translator.presentation.view_models import (
    build_default_app_settings,
    build_settings_state,
)


def test_build_settings_state_rejects_unknown_section_keys() -> None:
    with pytest.raises(LookupError, match="Unknown settings section: unsupported"):
        build_settings_state(
            app_settings=build_default_app_settings(),
            status="loaded",
            status_message=None,
            selected_section_key="unsupported",
        )
