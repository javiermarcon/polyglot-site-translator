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
    is_fuzzy: bool = False


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
class POCompilationFailure:
    """One PO file whose MO compilation could not be completed."""

    relative_path: str
    locale: str
    mo_path: str
    error_message: str


@dataclass(frozen=True)
class POProcessingCacheSettings:
    """Per-run cache configuration resolved before PO processing starts."""

    enabled: bool
    cache_path: str


@dataclass(frozen=True)
class POProcessingResult:
    """Observable typed outcome for one PO processing run."""

    files_discovered: int
    families_processed: int
    entries_pending: int
    entries_synchronized: int
    entries_translated: int
    entries_failed: int
    files_written: int
    mo_files_compiled: int
    failures: tuple[POProcessingFailure, ...]
    families_found: int = 0
    entries_total: int = 0
    entries_missing: int = 0
    entries_fuzzy: int = 0
    entries_completed_from_sync: int = 0
    entries_reused_from_other_variant: int = 0
    entries_translated_from_cache: int = 0
    entries_translated_from_provider: int = 0
    entries_skipped_sync_only: int = 0
    cache_enabled: bool = False
    dry_run: bool = False
    stats_only: bool = False
    variant_inconsistencies_found: int = 0
    variant_inconsistency_details: tuple[str, ...] = ()
    compilation_failures: tuple[POCompilationFailure, ...] = ()

    @property
    def files_found(self) -> int:
        """Return the discovered-file count using the legacy metric name."""
        return self.files_discovered

    @property
    def entries_translated_from_api(self) -> int:
        """Return provider-backed translations using the legacy metric name."""
        return self.entries_translated_from_provider

    @property
    def variant_differences_found(self) -> int:
        """Return variant-difference count using the legacy metric name."""
        return self.variant_inconsistencies_found

    @property
    def variant_difference_details(self) -> tuple[str, ...]:
        """Return variant-difference details using the legacy metric name."""
        return self.variant_inconsistency_details

    @property
    def mo_compiled(self) -> int:
        """Return compiled MO count using the legacy metric name."""
        return self.mo_files_compiled


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
    current_file: str | None = None
    current_entry: str | None = None


@dataclass(frozen=True)
class POProcessingFailure:
    """One PO entry that could not be completed during processing."""

    relative_path: str
    locale: str
    msgid: str
    error_message: str
