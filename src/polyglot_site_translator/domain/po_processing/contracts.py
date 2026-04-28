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
