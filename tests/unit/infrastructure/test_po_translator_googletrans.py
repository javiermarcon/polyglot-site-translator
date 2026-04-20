"""Unit tests for the Google Translate PO provider."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest
from pytest import MonkeyPatch

from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingTranslationError,
)
from polyglot_site_translator.infrastructure.po_translator_googletrans import (
    GoogleTransPOTranslationProvider,
)


@dataclass
class _TranslatedResult:
    src: str
    dest: str
    origin: str
    text: str
    pronunciation: str | None
    extra_data: dict[str, object] | None
    response: object | None


@dataclass
class _StubTranslator:
    translated_text: str
    last_dest: str | None = None
    last_text: str | None = None

    async def translate(self, text: str, dest: str) -> Any:
        self.last_text = text
        self.last_dest = dest
        return _TranslatedResult(
            src="en",
            dest=dest,
            origin=text,
            text=self.translated_text,
            pronunciation=None,
            extra_data=None,
            response=None,
        )


@dataclass
class _FailingTranslator:
    async def translate(self, text: str, dest: str) -> Any:
        del text, dest
        msg = "network down"
        raise OSError(msg)


@dataclass
class _ListTranslator:
    async def translate(self, text: str, dest: str) -> list[str]:
        del text, dest
        return ["bad-shape"]


def test_googletrans_provider_translates_to_target_base_language() -> None:
    translator = _StubTranslator(translated_text="Hola {{name}} %1$s")
    provider = GoogleTransPOTranslationProvider(translator=translator)

    translated = provider.translate_text(text="Hello {name} % 1 $ s", target_locale="es_AR")

    assert translated == "Hola {{name}} %1$s"
    assert translator.last_dest == "es"
    assert translator.last_text == "Hello {{name}} %1$s"


def test_googletrans_provider_wraps_translation_failures() -> None:
    provider = GoogleTransPOTranslationProvider(translator=_FailingTranslator())

    with pytest.raises(POProcessingTranslationError, match="External PO translation failed"):
        provider.translate_text(text="Hello", target_locale="es_AR")


def test_googletrans_provider_rejects_multiple_results_for_single_request() -> None:
    provider = GoogleTransPOTranslationProvider(translator=_ListTranslator())

    with pytest.raises(POProcessingTranslationError, match="multiple results"):
        provider.translate_text(text="Hello", target_locale="es_AR")


def test_googletrans_provider_reuses_loop_without_asyncio_run(monkeypatch: MonkeyPatch) -> None:
    translator = _StubTranslator(translated_text="Hola")
    provider = GoogleTransPOTranslationProvider(translator=translator)

    def _forbidden_asyncio_run(coro: object) -> object:
        if asyncio.iscoroutine(coro):
            coro.close()
        msg = "asyncio.run must not be used per translation request"
        raise AssertionError(msg)

    monkeypatch.setattr(
        "polyglot_site_translator.infrastructure.po_translator_googletrans.asyncio.run",
        _forbidden_asyncio_run,
    )

    first = provider.translate_text(text="Hello", target_locale="es_AR")
    second = provider.translate_text(text="World", target_locale="es_AR")

    assert first == "Hola"
    assert second == "Hola"
