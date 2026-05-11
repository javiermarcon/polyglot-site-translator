"""Shelve-backed translation cache used by PO processing workflows."""

from __future__ import annotations

from pathlib import Path
import shelve

from polyglot_site_translator.domain.po_processing.errors import POProcessingCacheError


class ShelvePOTranslationCache:
    """Persistent translation cache backed by ``shelve``.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def __init__(self, *, cache_path: Path, enabled: bool) -> None:
        """Store cache configuration and defer opening the shelve database.

        Args:
            cache_path (Path): Value supplied to this callable.
            enabled (bool): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        self._cache_path = cache_path
        self._enabled = enabled
        self._db: shelve.Shelf[str] | None = None

    def open(self) -> None:
        """Open the shelve database when cache support is enabled.

        Returns:
            None: This callable does not return a value.

        Raises:
            POProcessingCacheError: Raised when this callable hits the corresponding error path.
        """
        if not self._enabled:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = shelve.open(str(self._cache_path), writeback=False)  # noqa: SIM115
        except OSError as error:
            msg = f"Translation cache could not be opened at {self._cache_path}."
            raise POProcessingCacheError(msg) from error

    def close(self) -> None:
        """Close the open shelve database if one is active.

        Returns:
            None: This callable does not return a value.

        Raises:
            POProcessingCacheError: Raised when this callable hits the corresponding error path.
        """
        if self._db is None:
            return
        try:
            self._db.close()
        except OSError as error:
            msg = f"Translation cache could not be closed at {self._cache_path}."
            raise POProcessingCacheError(msg) from error
        finally:
            self._db = None

    def get(self, *, base_language: str, text: str) -> str | None:
        """Return a cached translation for the requested base language and text.

        Args:
            base_language (str): Value supplied to this callable.
            text (str): Value supplied to this callable.

        Returns:
            str | None: Structured value returned by this callable.

        Raises:
            POProcessingCacheError: Raised when this callable hits the corresponding error path.
        """
        if not self._enabled or self._db is None:
            return None
        key = _build_cache_key(base_language=base_language, text=text)
        try:
            value = self._db.get(key)
        except OSError as error:
            msg = f"Translation cache could not be read from {self._cache_path}."
            raise POProcessingCacheError(msg) from error
        if value is None:
            return None
        return str(value)

    def set(self, *, base_language: str, text: str, translated_text: str) -> None:
        """Persist one translated string in the open shelve database.

        Args:
            base_language (str): Value supplied to this callable.
            text (str): Value supplied to this callable.
            translated_text (str): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.

        Raises:
            POProcessingCacheError: Raised when this callable hits the corresponding error path.
        """
        if not self._enabled or self._db is None:
            return
        key = _build_cache_key(base_language=base_language, text=text)
        try:
            self._db[key] = translated_text
        except OSError as error:
            msg = f"Translation cache could not be updated at {self._cache_path}."
            raise POProcessingCacheError(msg) from error


def build_shelve_translation_cache(
    *,
    cache_path: Path,
    enabled: bool,
) -> ShelvePOTranslationCache:
    """Build the default shelve-backed translation cache implementation.

    Args:
        cache_path (Path): Value supplied to this callable.
        enabled (bool): Value supplied to this callable.

    Returns:
        ShelvePOTranslationCache: Structured value returned by this callable.
    """
    return ShelvePOTranslationCache(cache_path=cache_path, enabled=enabled)


def _build_cache_key(*, base_language: str, text: str) -> str:
    """Return the stable cache key used by shelve storage.

    Args:
        base_language (str): Value supplied to this callable.
        text (str): Value supplied to this callable.

    Returns:
        str: Structured value returned by this callable.
    """
    return f"{base_language}\x1f{text}"
