"""Runtime theme support for the Kivy frontend."""

from __future__ import annotations

from dataclasses import dataclass

ColorTuple = tuple[float, float, float, float]


@dataclass(frozen=True)
class ThemePalette:
    """Color tokens used by the Kivy presentation layer."""

    app_background: ColorTuple
    header_background: ColorTuple
    card_background: ColorTuple
    card_subtle_background: ColorTuple
    border_color: ColorTuple
    primary_button_background: ColorTuple
    primary_button_text: ColorTuple
    secondary_button_background: ColorTuple
    secondary_button_text: ColorTuple
    text_primary: ColorTuple
    text_muted: ColorTuple
    error_background: ColorTuple
    error_text: ColorTuple


LIGHT_THEME = ThemePalette(
    app_background=(0.95, 0.97, 0.99, 1.0),
    header_background=(0.98, 0.99, 1.0, 1.0),
    card_background=(1.0, 1.0, 1.0, 1.0),
    card_subtle_background=(0.94, 0.96, 0.99, 1.0),
    border_color=(0.84, 0.88, 0.93, 1.0),
    primary_button_background=(0.02, 0.44, 0.86, 1.0),
    primary_button_text=(1.0, 1.0, 1.0, 1.0),
    secondary_button_background=(0.91, 0.94, 0.98, 1.0),
    secondary_button_text=(0.06, 0.18, 0.31, 1.0),
    text_primary=(0.12, 0.16, 0.22, 1.0),
    text_muted=(0.42, 0.47, 0.54, 1.0),
    error_background=(0.99, 0.92, 0.92, 1.0),
    error_text=(0.57, 0.13, 0.14, 1.0),
)

DARK_THEME = ThemePalette(
    app_background=(0.08, 0.11, 0.15, 1.0),
    header_background=(0.11, 0.15, 0.21, 1.0),
    card_background=(0.12, 0.16, 0.22, 1.0),
    card_subtle_background=(0.17, 0.22, 0.29, 1.0),
    border_color=(0.24, 0.31, 0.4, 1.0),
    primary_button_background=(0.16, 0.52, 0.96, 1.0),
    primary_button_text=(1.0, 1.0, 1.0, 1.0),
    secondary_button_background=(0.18, 0.24, 0.31, 1.0),
    secondary_button_text=(0.88, 0.92, 0.97, 1.0),
    text_primary=(0.94, 0.96, 0.99, 1.0),
    text_muted=(0.68, 0.74, 0.81, 1.0),
    error_background=(0.38, 0.15, 0.17, 1.0),
    error_text=(1.0, 0.84, 0.85, 1.0),
)

_ACTIVE_THEME_STATE = {"mode": "light"}


def normalize_theme_mode(theme_mode: str) -> str:
    """Normalize supported theme modes into an applied palette mode."""
    if theme_mode == "system":
        return "light"
    if theme_mode in {"light", "dark"}:
        return theme_mode
    msg = f"Unsupported theme mode: {theme_mode}"
    raise ValueError(msg)


def resolve_theme_palette(theme_mode: str) -> ThemePalette:
    """Resolve a palette for the given theme mode."""
    normalized_mode = normalize_theme_mode(theme_mode)
    return DARK_THEME if normalized_mode == "dark" else LIGHT_THEME


def set_active_theme_mode(theme_mode: str) -> None:
    """Store the active theme mode for newly rendered widgets."""
    _ACTIVE_THEME_STATE["mode"] = normalize_theme_mode(theme_mode)


def get_active_theme_mode() -> str:
    """Return the currently active theme mode."""
    return _ACTIVE_THEME_STATE["mode"]


def get_active_theme() -> ThemePalette:
    """Return the currently active theme palette."""
    return resolve_theme_palette(_ACTIVE_THEME_STATE["mode"])
