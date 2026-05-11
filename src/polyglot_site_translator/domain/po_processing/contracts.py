"""Contracts for PO processing repositories."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from polyglot_site_translator.domain.po_processing.models import POFileData


class POCatalogRepository(Protocol):
    """Persistence boundary for loading and saving PO catalogs.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def discover_po_files(self, workspace_root: Path) -> tuple[POFileData, ...]:
        """Load all PO files found under a workspace root.

        Args:
            self:
                Value supplied to this callable.
            workspace_root:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def save_po_files(self, files: tuple[POFileData, ...]) -> None:
        """Persist PO files after synchronization changes.

        Args:
            self:
                Value supplied to this callable.
            files:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def compile_mo_file(self, file_data: POFileData) -> None:
        """Compile one persisted PO file into its sibling MO catalog.

        Args:
            self:
                Value supplied to this callable.
            file_data:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """


class POTranslationProvider(Protocol):
    """External translation provider used for missing PO entries.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def translate_text(self, *, text: str, target_locale: str) -> str:
        """Translate ``text`` into the base language implied by ``target_locale``.

        Args:
            self:
                Value supplied to this callable.
            text:
                Value supplied to this callable.
            target_locale:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """


class POTranslationCache(Protocol):
    """Persistent translation cache used to avoid repeated external calls.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def open(self) -> None:
        """Open any backing resources required by the cache.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def close(self) -> None:
        """Close any backing resources required by the cache.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def get(self, *, base_language: str, text: str) -> str | None:
        """Return a cached translation for ``text`` if available.

        Args:
            self:
                Value supplied to this callable.
            base_language:
                Value supplied to this callable.
            text:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def set(self, *, base_language: str, text: str, translated_text: str) -> None:
        """Persist a translated text in the cache.

        Args:
            self:
                Value supplied to this callable.
            base_language:
                Value supplied to this callable.
            text:
                Value supplied to this callable.
            translated_text:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """


class POTranslationCacheFactory(Protocol):
    """Build one translation cache instance for a processing run.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __call__(
        self,
        *,
        cache_path: Path,
        enabled: bool,
    ) -> POTranslationCache:
        """Create a cache instance for the requested path and enabled flag.

        Args:
            self:
                Value supplied to this callable.
            cache_path:
                Value supplied to this callable.
            enabled:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
