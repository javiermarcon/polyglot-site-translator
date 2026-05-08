"""Shelve-backed translation cache used by PO processing workflows."""

from __future__ import annotations

from pathlib import Path
import shelve

from polyglot_site_translator.domain.po_processing.errors import POProcessingCacheError


class ShelvePOTranslationCache:
    """Persistent translation cache backed by ``shelve``."""

    def __init__(self, *, cache_path: Path, enabled: bool) -> None:
        self._cache_path = cache_path
        self._enabled = enabled
        self._db: shelve.Shelf[str] | None = None

    def open(self) -> None:
        """Open the shelve database when cache support is enabled."""
        if not self._enabled:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = shelve.open(str(self._cache_path), writeback=False)  # noqa: SIM115
        except OSError as error:
            msg = f"Translation cache could not be opened at {self._cache_path}."
            raise POProcessingCacheError(msg) from error

    def close(self) -> None:
        """Close the open shelve database if one is active."""
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
        """Return a cached translation for the requested base language and text."""
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
        """Persist one translated string in the open shelve database."""
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
    """Build the default shelve-backed translation cache implementation."""
    return ShelvePOTranslationCache(cache_path=cache_path, enabled=enabled)


def _build_cache_key(*, base_language: str, text: str) -> str:
    """Return the stable cache key used by shelve storage."""
    return f"{base_language}\x1f{text}"
