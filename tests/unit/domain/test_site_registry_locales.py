"""Unit tests for locale normalization helpers."""

from __future__ import annotations

import pytest

from polyglot_site_translator.domain.site_registry.locales import normalize_default_locale


def test_normalize_default_locale_uses_default_label_in_errors() -> None:
    """Verify normalize default locale uses default label in errors.

    Returns:
        None: This callable does not return a value.
    """
    with pytest.raises(ValueError, match=r"Default locale must not be empty\."):
        normalize_default_locale("")


def test_normalize_default_locale_allows_custom_error_label() -> None:
    """Verify normalize default locale allows custom error label.

    Returns:
        None: This callable does not return a value.
    """
    with pytest.raises(
        ValueError,
        match=(
            r"Selected locales must be a valid locale or a comma-separated list of "
            r"valid locales\. Invalid values: asad@\."
        ),
    ):
        normalize_default_locale("asad@", label="Selected locales")
