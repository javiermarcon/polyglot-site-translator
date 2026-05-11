"""Unit tests for the shelve-backed translation cache."""

from __future__ import annotations

from pathlib import Path
import shelve
from typing import cast

import pytest

from polyglot_site_translator.domain.po_processing.errors import POProcessingCacheError
from polyglot_site_translator.infrastructure.po_translation_cache_shelve import (
    ShelvePOTranslationCache,
    _build_cache_key,
    build_shelve_translation_cache,
)


class _FailingShelf:
    """Test helper for FailingShelf.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def __init__(self, *, fail_on_get: bool = False, fail_on_set: bool = False) -> None:
        """Initialize the test helper state.

        Args:
            fail_on_get (bool): Value supplied to this callable.
            fail_on_set (bool): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        self.fail_on_get = fail_on_get
        self.fail_on_set = fail_on_set
        self.store: dict[str, str] = {}
        self.closed = False

    def get(self, key: str, default: object = None) -> object:
        """Handle get.

        Args:
            key (str): Value supplied to this callable.
            default (object): Value supplied to this callable.

        Returns:
            object: Structured value returned by this callable.

        Raises:
            OSError: Raised when this callable hits the corresponding error path.
        """
        if self.fail_on_get:
            msg = "read failed"
            raise OSError(msg)
        return self.store.get(key, default)

    def __setitem__(self, key: str, value: str) -> None:
        """Handle setitem.

        Args:
            key (str): Value supplied to this callable.
            value (str): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.

        Raises:
            OSError: Raised when this callable hits the corresponding error path.
        """
        if self.fail_on_set:
            msg = "write failed"
            raise OSError(msg)
        self.store[key] = value

    def close(self) -> None:
        """Handle close.

        Returns:
            None: This callable does not return a value.
        """
        self.closed = True


def test_shelve_translation_cache_roundtrips_values(tmp_path: Path) -> None:
    """Verify shelve translation cache roundtrips values.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    cache_path = tmp_path / "translations.cache"
    cache = ShelvePOTranslationCache(cache_path=cache_path, enabled=True)

    cache.open()
    cache.set(base_language="es", text="Save", translated_text="Guardar")
    assert cache.get(base_language="es", text="Save") == "Guardar"
    cache.close()

    reopened = ShelvePOTranslationCache(cache_path=cache_path, enabled=True)
    reopened.open()
    assert reopened.get(base_language="es", text="Save") == "Guardar"
    reopened.close()


def test_shelve_translation_cache_is_noop_when_disabled(tmp_path: Path) -> None:
    """Verify shelve translation cache is noop when disabled.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    cache = ShelvePOTranslationCache(cache_path=tmp_path / "translations.cache", enabled=False)

    cache.open()
    cache.set(base_language="es", text="Save", translated_text="Guardar")

    assert cache.get(base_language="es", text="Save") is None
    cache.close()
    assert not (tmp_path / "translations.cache").exists()


def test_shelve_translation_cache_wraps_open_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify shelve translation cache wraps open errors.

    Args:
        tmp_path (Path): Value supplied to this callable.
        monkeypatch (pytest.MonkeyPatch): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.

    Raises:
        OSError: Raised when this callable hits the corresponding error path.
    """
    cache = ShelvePOTranslationCache(cache_path=tmp_path / "translations.cache", enabled=True)

    def _raise_open(*_args: object, **_kwargs: object) -> object:
        """Handle raise open.

        Args:
            _args (object): Value supplied to this callable.
            _kwargs (object): Value supplied to this callable.

        Returns:
            object: Structured value returned by this callable.

        Raises:
            OSError: Raised when this callable hits the corresponding error path.
        """
        msg = "open failed"
        raise OSError(msg)

    monkeypatch.setattr(shelve, "open", _raise_open)

    with pytest.raises(POProcessingCacheError, match=r"could not be opened"):
        cache.open()


def test_shelve_translation_cache_wraps_close_errors(tmp_path: Path) -> None:
    """Verify shelve translation cache wraps close errors.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.

    Raises:
        OSError: Raised when this callable hits the corresponding error path.
    """
    cache = ShelvePOTranslationCache(cache_path=tmp_path / "translations.cache", enabled=True)

    class _CloseFailingShelf(_FailingShelf):
        """Test helper for CloseFailingShelf.

        Attributes:
            None: This type does not declare additional class-level attributes.
        """

        def close(self) -> None:
            """Handle close.

            Returns:
                None: This callable does not return a value.

            Raises:
                OSError: Raised when this callable hits the corresponding error path.
            """
            msg = "close failed"
            raise OSError(msg)

    cache._db = cast(shelve.Shelf[str], _CloseFailingShelf())

    with pytest.raises(POProcessingCacheError, match=r"could not be closed"):
        cache.close()


def test_shelve_translation_cache_wraps_get_and_set_errors(tmp_path: Path) -> None:
    """Verify shelve translation cache wraps get and set errors.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    cache = ShelvePOTranslationCache(cache_path=tmp_path / "translations.cache", enabled=True)
    cache._db = cast(shelve.Shelf[str], _FailingShelf(fail_on_get=True, fail_on_set=True))

    with pytest.raises(POProcessingCacheError, match=r"could not be read"):
        cache.get(base_language="es", text="Save")

    with pytest.raises(POProcessingCacheError, match=r"could not be updated"):
        cache.set(base_language="es", text="Save", translated_text="Guardar")


def test_build_shelve_translation_cache_factory_and_cache_key(tmp_path: Path) -> None:
    """Verify build shelve translation cache factory and cache key.

    Args:
        tmp_path (Path): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    cache = build_shelve_translation_cache(
        cache_path=tmp_path / "translations.cache",
        enabled=True,
    )

    assert isinstance(cache, ShelvePOTranslationCache)
    assert _build_cache_key(base_language="es", text="Save") == "es\x1fSave"
