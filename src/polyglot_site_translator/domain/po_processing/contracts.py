"""Contracts for PO processing repositories."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from polyglot_site_translator.domain.po_processing.models import POFileData


class POCatalogRepository(Protocol):
    """Persistence boundary for loading and saving PO catalogs.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def discover_po_files(self, workspace_root: Path) -> tuple[POFileData, ...]:
        """Load all PO files found under a workspace root.

        Args:
            workspace_root (Path): Value supplied to this callable.

        Returns:
            tuple[POFileData, ...]: Structured value returned by this callable.
        """

    def save_po_files(self, files: tuple[POFileData, ...]) -> None:
        """Persist PO files after synchronization changes.

        Args:
            files (tuple[POFileData, ...]): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """

    def compile_mo_file(self, file_data: POFileData) -> None:
        """Compile one persisted PO file into its sibling MO catalog.

        Args:
            file_data (POFileData): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """


class POTranslationProvider(Protocol):
    """External translation provider used for missing PO entries.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def translate_text(self, *, text: str, target_locale: str) -> str:
        """Translate ``text`` into the base language implied by ``target_locale``.

        Args:
            text (str): Value supplied to this callable.
            target_locale (str): Value supplied to this callable.

        Returns:
            str: Structured value returned by this callable.
        """


class POTranslationCache(Protocol):
    """Persistent translation cache used to avoid repeated external calls.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def open(self) -> None:
        """Open any backing resources required by the cache.

        Returns:
            None: This callable does not return a value.
        """

    def close(self) -> None:
        """Close any backing resources required by the cache.

        Returns:
            None: This callable does not return a value.
        """

    def get(self, *, base_language: str, text: str) -> str | None:
        """Return a cached translation for ``text`` if available.

        Args:
            base_language (str): Value supplied to this callable.
            text (str): Value supplied to this callable.

        Returns:
            str | None: Structured value returned by this callable.
        """

    def set(self, *, base_language: str, text: str, translated_text: str) -> None:
        """Persist a translated text in the cache.

        Args:
            base_language (str): Value supplied to this callable.
            text (str): Value supplied to this callable.
            translated_text (str): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """


class POTranslationCacheFactory(Protocol):
    """Build one translation cache instance for a processing run.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def __call__(
        self,
        *,
        cache_path: Path,
        enabled: bool,
    ) -> POTranslationCache:
        """Create a cache instance for the requested path and enabled flag.

        Args:
            cache_path (Path): Value supplied to this callable.
            enabled (bool): Value supplied to this callable.

        Returns:
            POTranslationCache: Structured value returned by this callable.
        """
