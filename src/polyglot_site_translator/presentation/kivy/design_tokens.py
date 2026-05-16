"""Central design tokens for the Kivy presentation layer.

The module keeps visual constants out of individual screens while remaining
independent from Kivy imports.  Pure token helpers are intentionally easy to
unit test without opening a graphical runtime.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpacingTokens:
    """Spacing scale shared by Kivy screens and reusable widgets.

    Attributes:
        xs:
            Smallest gap for tightly related inline elements.
        sm:
            Compact gap for labels, hints, and small control groups.
        md:
            Default gap between controls inside a surface.
        lg:
            Default padding for cards, panels, and page content.
        xl:
            Larger gap between major page regions.
    """

    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24


@dataclass(frozen=True)
class TypographyTokens:
    """Font-size scale for the Kivy frontend.

    Attributes:
        caption:
            Small supporting copy and compact metadata.
        body:
            Default body copy for labels and summaries.
        label:
            Form labels and compact section headings.
        section_title:
            Card and panel headings.
        screen_title:
            Main screen heading in the shared shell header.
    """

    caption: int = 13
    body: int = 15
    label: int = 16
    section_title: int = 18
    screen_title: int = 24


@dataclass(frozen=True)
class RadiusTokens:
    """Corner-radius scale for reusable Kivy surfaces.

    Attributes:
        control:
            Radius for small controls.
        card:
            Radius for grouped card surfaces.
        panel:
            Radius for larger screen-level panels.
    """

    control: int = 6
    card: int = 8
    panel: int = 10


@dataclass(frozen=True)
class ElevationTokens:
    """Lightweight surface depth tokens for Kivy canvas primitives.

    Attributes:
        card_border_width:
            Border width used by cards and status panels.
        divider_width:
            Thin separator width for grouped content.
    """

    card_border_width: int = 1
    divider_width: int = 1


@dataclass(frozen=True)
class ComponentSizeTokens:
    """Stable component dimensions used across Kivy widgets.

    Attributes:
        button_height:
            Default height for primary and secondary action buttons.
        compact_button_height:
            Height for compact toolbar or menu actions.
        input_height:
            Default height for single-line text inputs and spinners.
        progress_height:
            Height for progress indicators.
        header_height:
            Height for the shared application header.
        menu_width:
            Width for the application menu dropdown.
    """

    button_height: int = 44
    compact_button_height: int = 40
    input_height: int = 44
    progress_height: int = 20
    header_height: int = 88
    menu_width: int = 340


SPACING = SpacingTokens()
TYPOGRAPHY = TypographyTokens()
RADIUS = RadiusTokens()
ELEVATION = ElevationTokens()
COMPONENT_SIZES = ComponentSizeTokens()


def resolve_spacing(token_name: str) -> int:
    """Return a spacing token by name.

    Args:
        token_name:
            Public spacing token name such as ``"sm"`` or ``"lg"``.

    Returns:
        value:
            Integer spacing value suitable for Kivy padding or spacing.

    Raises:
        LookupError:
            Raised when ``token_name`` is not part of the spacing scale.
    """
    if hasattr(SPACING, token_name):
        return int(getattr(SPACING, token_name))
    msg = f"Unknown spacing token: {token_name}"
    raise LookupError(msg)
