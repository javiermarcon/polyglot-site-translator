"""Typed models for shared PO processing workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class POEntryId:
    """Unique gettext identity for a PO entry."""

    context: str | None
    msgid: str
    msgid_plural: str | None


@dataclass(frozen=True)
class POEntryData:
    """Normalized PO entry data used by shared services."""

    entry_id: POEntryId
    msgstr: str
    msgstr_plural: dict[str, str]


@dataclass(frozen=True)
class POFileData:
    """A PO file discovered in the project workspace."""

    source_path: str
    relative_path: str
    locale: str
    family_key: str
    entries: tuple[POEntryData, ...]


@dataclass(frozen=True)
class POProcessingResult:
    """Observable typed outcome for one PO processing run."""

    files_discovered: int
    families_processed: int
    entries_synchronized: int
