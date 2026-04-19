"""Locale parsing and normalization helpers for site registry workflows."""

from __future__ import annotations

import re

from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryValidationError,
)

_LOCALE_PATTERN = re.compile(r"^[a-z]{2,3}(?:_[A-Z]{2})?$")


def normalize_default_locale(value: str, *, label: str = "Default locale") -> str:
    """Return a canonical comma-separated locale list for persistence."""
    normalized_value = value.strip()
    if normalized_value == "":
        msg = f"{label} must not be empty."
        raise SiteRegistryValidationError(msg)
    locale_items = tuple(item.strip() for item in normalized_value.split(","))
    if any(item == "" for item in locale_items):
        msg = f"{label} must be a valid locale or a comma-separated list of valid locales."
        raise SiteRegistryValidationError(msg)
    invalid_locales = tuple(
        item for item in locale_items if _LOCALE_PATTERN.fullmatch(item) is None
    )
    if invalid_locales != ():
        invalid_list = ", ".join(invalid_locales)
        msg = (
            f"{label} must be a valid locale or a comma-separated list of valid locales. "
            f"Invalid values: {invalid_list}."
        )
        raise SiteRegistryValidationError(msg)
    return ",".join(locale_items)


def parse_default_locale_list(value: str, *, label: str = "Default locale") -> tuple[str, ...]:
    """Return the normalized configured locales as a tuple."""
    return tuple(normalize_default_locale(value, label=label).split(","))
