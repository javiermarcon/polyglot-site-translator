"""Google Translate-backed provider for PO processing."""

from __future__ import annotations

import asyncio
import re
import threading
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
        self._translator = translator
        self._thread_state = threading.local()

    def translate_text(self, *, text: str, target_locale: str) -> str:
        """Translate text into the base language for the target locale."""
        destination_language = _base_language(target_locale)
        sanitized_source = _sanitize_text(text).replace(".", ". ")
        try:
            translated = self._loop().run_until_complete(
                self._translator_for_current_thread().translate(
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

    def _loop(self) -> asyncio.AbstractEventLoop:
        loop = getattr(self._thread_state, "loop", None)
        if isinstance(loop, asyncio.AbstractEventLoop) and not loop.is_closed():
            return loop
        loop = asyncio.new_event_loop()
        self._thread_state.loop = loop
        return loop

    def _translator_for_current_thread(self) -> Translator:
        if self._translator is not None:
            return self._translator
        translator = getattr(self._thread_state, "translator", None)
        if isinstance(translator, Translator):
            return translator
        translator = Translator()
        self._thread_state.translator = translator
        return translator


def _base_language(locale: str) -> str:
    return locale.split("_", maxsplit=1)[0].lower()


def _sanitize_text(text: str) -> str:
    sanitized = text.replace("{", "{{").replace("}", "}}")
    return re.sub(r"%\s*(\d+)\s*\$\s*(\w)", r"%\1$\2", sanitized)
