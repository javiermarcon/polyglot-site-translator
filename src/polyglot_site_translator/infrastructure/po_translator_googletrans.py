"""Google Translate-backed provider for PO processing."""

from __future__ import annotations

import asyncio
import re
from typing import Protocol, runtime_checkable

from googletrans import Translator  # type: ignore[import-untyped]

from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingTranslationError,
)


@runtime_checkable
class _TranslationResult(Protocol):
    text: str


class GoogleTransPOTranslationProvider:
    """Translate missing PO entries through ``googletrans``."""

    def __init__(self, translator: Translator | None = None) -> None:
        self._translator = translator or Translator()

    def translate_text(self, *, text: str, target_locale: str) -> str:
        """Translate text into the base language for the target locale."""
        destination_language = _base_language(target_locale)
        sanitized_source = _sanitize_text(text).replace(".", ". ")
        try:
            translated = asyncio.run(
                self._translator.translate(
                    sanitized_source,
                    dest=destination_language,
                )
            )
        except (AttributeError, LookupError, OSError, RuntimeError, TypeError, ValueError) as error:
            cause = str(error).strip() or error.__class__.__name__
            msg = (
                f"External PO translation failed for locale '{target_locale}' and text {text!r}. "
                f"Cause: {cause}"
            )
            raise POProcessingTranslationError(msg) from error
        if isinstance(translated, list):
            msg = "External PO translation returned multiple results for a single text request."
            raise POProcessingTranslationError(msg)
        if not isinstance(translated, _TranslationResult):
            msg = (
                "External PO translation returned an unexpected result type: "
                f"{type(translated).__name__}."
            )
            raise POProcessingTranslationError(msg)
        return str(translated.text)


def _base_language(locale: str) -> str:
    return locale.split("_", maxsplit=1)[0].lower()


def _sanitize_text(text: str) -> str:
    sanitized = text.replace("{", "{{").replace("}", "}}")
    return re.sub(r"%\s*(\d+)\s*\$\s*(\w)", r"%\1$\2", sanitized)
