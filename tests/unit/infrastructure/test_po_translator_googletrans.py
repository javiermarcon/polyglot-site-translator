"""Unit tests for the Google Translate PO provider."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
from typing import Any

import pytest
from pytest import MonkeyPatch

from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingTranslationError,
    POTranslationProviderConfigurationError,
    POTranslationProviderResponseError,
    POTranslationProviderTransportError,
)
from polyglot_site_translator.infrastructure.po_translator_googletrans import (
    GoogleTransPOTranslationProvider,
    _base_language,
    _load_googletrans_translator_class,
    _sanitize_text,
    _transport_error_types,
)


@dataclass
class _TranslatedResult:
    """Test helper for TranslatedResult.

    Attributes:
        src:
            Documented attribute exposed by this type.
        dest:
            Documented attribute exposed by this type.
        origin:
            Documented attribute exposed by this type.
        text:
            Documented attribute exposed by this type.
        pronunciation:
            Documented attribute exposed by this type.
        extra_data:
            Documented attribute exposed by this type.
        response:
            Documented attribute exposed by this type.
    """

    src: str
    dest: str
    origin: str
    text: str
    pronunciation: str | None
    extra_data: dict[str, object] | None
    response: object | None


@dataclass
class _StubTranslator:
    """Test helper for StubTranslator.

    Attributes:
        translated_text:
            Documented attribute exposed by this type.
        last_dest:
            Documented attribute exposed by this type.
        last_text:
            Documented attribute exposed by this type.
    """

    translated_text: str
    last_dest: str | None = None
    last_text: str | None = None

    async def translate(self, text: str, dest: str) -> Any:
        """Handle translate.

        Args:
            self:
                Value supplied to this callable.
            text:
                Value supplied to this callable.
            dest:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
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
    """Test helper for FailingTranslator.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    @staticmethod
    async def translate(text: str, dest: str) -> Any:
        """Handle translate.

        Args:
            text:
                Value supplied to this callable.
            dest:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            OSError:
                Raised when this callable hits the corresponding error path.
        """
        msg = "network down"
        raise OSError(msg)


@dataclass
class _ListTranslator:
    """Test helper for ListTranslator.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    @staticmethod
    async def translate(text: str, dest: str) -> list[str]:
        """Handle translate.

        Args:
            text:
                Value supplied to this callable.
            dest:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return ["bad-shape"]


@dataclass
class _ProtocolFailingTranslator:
    """Test helper for ProtocolFailingTranslator.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    @staticmethod
    async def translate(text: str, dest: str) -> Any:
        """Handle translate.

        Args:
            text:
                Value supplied to this callable.
            dest:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            RuntimeError:
                Raised when this callable hits the corresponding error path.
        """
        msg = "protocol closed"
        raise RuntimeError(msg)


@dataclass
class _MisconfiguredTranslator:
    """Test helper for MisconfiguredTranslator.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    @staticmethod
    async def translate(text: str, dest: str) -> Any:
        """Handle translate.

        Args:
            text:
                Value supplied to this callable.
            dest:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            AttributeError:
                Raised when this callable hits the corresponding error path.
        """
        msg = "translator object has no HTTP client"
        raise AttributeError(msg)


@dataclass
class _UnexpectedResultTranslator:
    """Test helper for UnexpectedResultTranslator.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    @staticmethod
    async def translate(text: str, dest: str) -> object:
        """Handle translate.

        Args:
            text:
                Value supplied to this callable.
            dest:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return {"text": "Hola"}


def test_googletrans_provider_translates_to_target_base_language() -> None:
    """Verify googletrans provider translates to target base language.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        POTranslationProviderConfigurationError:
            Expected from the exercised loader branch.
    """
    translator = _StubTranslator(translated_text="Hola {{name}} %1$s")
    provider = GoogleTransPOTranslationProvider(translator=translator)

    translated = provider.translate_text(
        text="Hello {name} % 1 $ s", target_locale="es_AR"
    )

    assert translated == "Hola {{name}} %1$s"
    assert translator.last_dest == "es"
    assert translator.last_text == "Hello {{name}} %1$s"


def test_googletrans_provider_wraps_translation_failures() -> None:
    """Verify googletrans provider wraps translation failures.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        ModuleNotFoundError:
            Raised by the controlled optional module import branch.
    """
    provider = GoogleTransPOTranslationProvider(translator=_FailingTranslator())

    with pytest.raises(
        POTranslationProviderTransportError, match="External PO translation failed"
    ):
        provider.translate_text(text="Hello", target_locale="es_AR")


def test_googletrans_provider_rejects_multiple_results_for_single_request() -> None:
    """Verify googletrans provider rejects multiple results for single request.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        POTranslationProviderConfigurationError:
            Expected from the exercised loader branch.
    """
    provider = GoogleTransPOTranslationProvider(translator=_ListTranslator())

    with pytest.raises(POTranslationProviderResponseError, match="multiple results"):
        provider.translate_text(text="Hello", target_locale="es_AR")


def test_googletrans_provider_reuses_loop_without_asyncio_run(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify googletrans provider reuses loop without asyncio run.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        AssertionError:
            Raised when this callable hits the corresponding error path.
    """
    translator = _StubTranslator(translated_text="Hola")
    provider = GoogleTransPOTranslationProvider(translator=translator)

    def _forbidden_asyncio_run(coro: object) -> object:
        """Handle forbidden asyncio run.

        Args:
            coro:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            AssertionError:
                Raised when this callable hits the corresponding error path.
        """
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


def test_googletrans_provider_wraps_http_protocol_errors() -> None:
    """Verify googletrans provider wraps http protocol errors.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        ModuleNotFoundError:
            Raised by the controlled optional module import branch.
    """
    provider = GoogleTransPOTranslationProvider(translator=_ProtocolFailingTranslator())

    with pytest.raises(POTranslationProviderTransportError, match="protocol closed"):
        provider.translate_text(text="Hello", target_locale="es_AR")


def test_googletrans_provider_wraps_configuration_errors() -> None:
    """Verify googletrans provider wraps configuration errors.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        POTranslationProviderConfigurationError:
            Expected from the exercised loader branch.
    """
    provider = GoogleTransPOTranslationProvider(translator=_MisconfiguredTranslator())

    with pytest.raises(POTranslationProviderConfigurationError, match="misconfigured"):
        provider.translate_text(text="Hello", target_locale="es_AR")


def test_googletrans_provider_translation_errors_keep_base_type() -> None:
    """Verify googletrans provider translation errors keep base type.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        ModuleNotFoundError:
            Raised by the controlled optional module import branch.
    """
    provider = GoogleTransPOTranslationProvider(translator=_FailingTranslator())

    with pytest.raises(POProcessingTranslationError):
        provider.translate_text(text="Hello", target_locale="es_AR")


def test_googletrans_provider_rejects_unexpected_result_type() -> None:
    """Verify googletrans provider rejects unexpected result type.

    Returns:
        value:
            Structured value returned by this callable.
    """
    provider = GoogleTransPOTranslationProvider(
        translator=_UnexpectedResultTranslator()
    )

    with pytest.raises(
        POTranslationProviderResponseError, match="unexpected result type"
    ):
        provider.translate_text(text="Hello", target_locale="es_AR")


def test_googletrans_provider_reuses_thread_local_translator_and_recreates_closed_loop(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify googletrans provider reuses thread local translator and recreates closed.

    loop.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    provider = GoogleTransPOTranslationProvider(translator=None)
    created: list[_StubTranslator] = []

    class _TranslatorFactory(_StubTranslator):
        """Test helper for TranslatorFactory.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        def __init__(self, *, http2: bool) -> None:
            """Initialize the test helper state.

            Args:
                self:
                    Value supplied to this callable.
                http2:
                    Value supplied to this callable.

            Returns:
                value:
                    Structured value returned by this callable.
            """
            assert http2 is False
            super().__init__(translated_text="Hola")
            created.append(self)

    monkeypatch.setattr(
        "polyglot_site_translator.infrastructure.po_translator_googletrans."
        "_load_googletrans_translator_class",
        lambda: _TranslatorFactory,
    )

    first_translator = provider._translator_for_current_thread()
    second_translator = provider._translator_for_current_thread()

    assert first_translator is second_translator
    assert len(created) == 1

    loop = provider._loop()
    loop.close()

    recreated_loop = provider._loop()
    assert recreated_loop is not loop
    recreated_loop.close()


def test_googletrans_loader_rejects_missing_dependency(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify googletrans loader rejects missing dependency.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        POTranslationProviderConfigurationError:
            Expected from the exercised loader branch.
    """

    def missing_googletrans(module_name: str) -> object:
        """Raise a missing dependency error for googletrans.

        Args:
            module_name:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ModuleNotFoundError:
                Raised when googletrans is imported.
        """
        if module_name == "googletrans":
            raise ModuleNotFoundError(module_name)
        return __import__(module_name)

    monkeypatch.setattr(
        "polyglot_site_translator.infrastructure.po_translator_googletrans."
        "importlib.import_module",
        missing_googletrans,
    )

    with pytest.raises(
        POTranslationProviderConfigurationError,
        match=re.escape("googletrans is not installed."),
    ):
        _load_googletrans_translator_class()


def test_googletrans_loader_rejects_missing_translator_class(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify googletrans loader rejects invalid translator class.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    module = type("GoogleTransModule", (), {"Translator": None})()

    monkeypatch.setattr(
        "polyglot_site_translator.infrastructure.po_translator_googletrans."
        "importlib.import_module",
        lambda _module_name: module,
    )

    with pytest.raises(
        POTranslationProviderConfigurationError,
        match=re.escape("googletrans.Translator is unavailable."),
    ):
        _load_googletrans_translator_class()


def test_googletrans_loader_returns_available_translator_class(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify googletrans loader returns the dependency translator class.

    Args:
        monkeypatch:
            Pytest helper used to isolate import resolution from installed
            third-party packages.

    Returns:
        value:
            Structured value returned by this callable.
    """
    translator_class = type("_FakeGoogleTransTranslator", (), {})
    module = type(
        "_FakeGoogleTransModule",
        (),
        {"Translator": translator_class},
    )

    monkeypatch.setattr(
        "polyglot_site_translator.infrastructure.po_translator_googletrans."
        "importlib.import_module",
        lambda module_name: module,
    )

    assert _load_googletrans_translator_class() is translator_class


def test_transport_error_types_ignore_missing_modules_and_invalid_attributes(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify transport error type discovery handles optional dependencies.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        ModuleNotFoundError:
            Raised by the controlled optional module import branch.
    """

    def import_optional_transport_module(module_name: str) -> object:
        """Return controlled optional transport modules.

        Args:
            module_name:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.

        Raises:
            ModuleNotFoundError:
                Raised for missing optional modules.
        """
        if module_name == "httpcore":
            raise ModuleNotFoundError(module_name)
        if module_name == "httpx":
            return type("HttpxModule", (), {"HTTPError": "not-an-error"})()
        return __import__(module_name)

    monkeypatch.setattr(
        "polyglot_site_translator.infrastructure.po_translator_googletrans."
        "importlib.import_module",
        import_optional_transport_module,
    )

    error_types = _transport_error_types()

    assert OSError in error_types
    assert RuntimeError in error_types
    assert all(isinstance(error_type, type) for error_type in error_types)


def test_googletrans_helpers_cover_locale_and_text_sanitization() -> None:
    """Verify googletrans helpers cover locale and text sanitization.

    Returns:
        value:
            Structured value returned by this callable.
    """
    assert _base_language("es_AR") == "es"
    assert _base_language("PT") == "pt"
    assert _sanitize_text("Hello {name} % 1 $ s") == "Hello {{name}} %1$s"
