"""Contracts for PO processing repositories."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from polyglot_site_translator.domain.po_processing.models import POFileData


class POCatalogRepository(Protocol):
    """Persistence boundary for loading and saving PO catalogs."""

    def discover_po_files(self, workspace_root: Path) -> tuple[POFileData, ...]:
        """Load all PO files found under a workspace root."""

    def save_po_files(self, files: tuple[POFileData, ...]) -> None:
        """Persist PO files after synchronization changes."""

    def compile_mo_file(self, file_data: POFileData) -> None:
        """Compile one persisted PO file into its sibling MO catalog."""


class POTranslationProvider(Protocol):
    """External translation provider used for missing PO entries."""

    def translate_text(self, *, text: str, target_locale: str) -> str:
        """Translate ``text`` into the base language implied by ``target_locale``."""


class POTranslationCache(Protocol):
    """Persistent translation cache used to avoid repeated external calls."""

    def open(self) -> None:
        """Open any backing resources required by the cache."""

    def close(self) -> None:
        """Close any backing resources required by the cache."""

    def get(self, *, base_language: str, text: str) -> str | None:
        """Return a cached translation for ``text`` if available."""

    def set(self, *, base_language: str, text: str, translated_text: str) -> None:
        """Persist a translated text in the cache."""


class POTranslationCacheFactory(Protocol):
    """Build one translation cache instance for a processing run."""

    def __call__(
        self,
        *,
        cache_path: Path,
        enabled: bool,
    ) -> POTranslationCache:
        """Create a cache instance for the requested path and enabled flag."""
