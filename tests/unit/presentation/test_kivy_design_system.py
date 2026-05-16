"""Unit tests for pure Kivy design-system helpers."""

from __future__ import annotations

from polyglot_site_translator.presentation.kivy.design_tokens import (
    COMPONENT_SIZES,
    ELEVATION,
    RADIUS,
    SPACING,
    TYPOGRAPHY,
    resolve_spacing,
)
from polyglot_site_translator.presentation.kivy.widgets.actions import (
    ActionIntent,
    resolve_button_style,
)
from polyglot_site_translator.presentation.kivy.widgets.surfaces import (
    StatusTone,
    resolve_status_surface_roles,
    status_tone_from_workflow_status,
)


def test_design_tokens_provide_consistent_component_dimensions() -> None:
    """Verify design tokens expose stable dimensions for Kivy controls.

    Returns:
        value:
            Structured value returned by this callable.
    """
    assert resolve_spacing("md") == SPACING.md
    assert COMPONENT_SIZES.button_height > TYPOGRAPHY.body
    assert COMPONENT_SIZES.input_height == COMPONENT_SIZES.button_height
    assert RADIUS.card > RADIUS.control
    assert ELEVATION.card_border_width >= 1


def test_resolve_spacing_rejects_unknown_token_names() -> None:
    """Verify spacing lookup rejects unsupported token names.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when the helper accepts an unsupported token name.
    """
    try:
        resolve_spacing("unknown")
    except LookupError as exc:
        assert "Unknown spacing token: unknown" in str(exc)
    else:
        msg = "resolve_spacing should reject unknown token names"
        raise AssertionError(msg)


def test_button_style_resolution_maps_intents_to_theme_roles() -> None:
    """Verify button style helpers keep action styling centralized.

    Returns:
        value:
            Structured value returned by this callable.
    """
    primary = resolve_button_style(ActionIntent.PRIMARY)
    secondary = resolve_button_style(ActionIntent.SECONDARY)
    destructive = resolve_button_style(ActionIntent.DESTRUCTIVE)

    assert primary.background_role == "primary_button_background"
    assert primary.text_role == "primary_button_text"
    assert secondary.background_role == "secondary_button_background"
    assert destructive.background_role == "destructive_button_background"


def test_status_surface_roles_cover_empty_loading_error_and_success() -> None:
    """Verify status role resolution covers visible workflow states.

    Returns:
        value:
            Structured value returned by this callable.
    """
    assert resolve_status_surface_roles(StatusTone.EMPTY).background_role == (
        "card_subtle_background"
    )
    assert resolve_status_surface_roles(StatusTone.LOADING).accent_role == "info_text"
    assert resolve_status_surface_roles(StatusTone.ERROR).text_role == "error_text"
    assert resolve_status_surface_roles(StatusTone.SUCCESS).accent_role == (
        "success_text"
    )


def test_status_tone_from_workflow_status_maps_common_statuses() -> None:
    """Verify workflow statuses map to reusable visual tones.

    Returns:
        value:
            Structured value returned by this callable.
    """
    assert status_tone_from_workflow_status("failed") == StatusTone.ERROR
    assert status_tone_from_workflow_status("running") == StatusTone.LOADING
    assert status_tone_from_workflow_status("completed") == StatusTone.SUCCESS
    assert status_tone_from_workflow_status("queued") == StatusTone.INFO
