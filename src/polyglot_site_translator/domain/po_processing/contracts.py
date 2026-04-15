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
