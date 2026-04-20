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
    nplurals: int
    entries: tuple[POEntryData, ...]


@dataclass(frozen=True)
class POProcessingResult:
    """Observable typed outcome for one PO processing run."""

    files_discovered: int
    families_processed: int
    entries_pending: int
    entries_synchronized: int
    entries_translated: int
    entries_failed: int
    failures: tuple[POProcessingFailure, ...]


@dataclass(frozen=True)
class POProcessingProgress:
    """Progress update emitted while processing PO families."""

    processed_families: int
    completed_entries: int
    total_entries: int
    files_discovered: int
    entries_synchronized: int
    entries_translated: int
    entries_failed: int
    message: str


@dataclass(frozen=True)
class POProcessingFailure:
    """One PO entry that could not be completed during processing."""

    relative_path: str
    locale: str
    msgid: str
    error_message: str
