"""Typed models for shared PO processing workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class POEntryId:
    """Unique gettext identity for a PO entry.

    Attributes:
        context (str | None): Documented attribute exposed by this type.
        msgid (str): Documented attribute exposed by this type.
        msgid_plural (str | None): Documented attribute exposed by this type.
    """

    context: str | None
    msgid: str
    msgid_plural: str | None


@dataclass(frozen=True)
class POEntryData:
    """Normalized PO entry data used by shared services.

    Attributes:
        entry_id (POEntryId): Documented attribute exposed by this type.
        msgstr (str): Documented attribute exposed by this type.
        msgstr_plural (dict[str, str]): Documented attribute exposed by this type.
        is_fuzzy (bool): Documented attribute exposed by this type.
    """

    entry_id: POEntryId
    msgstr: str
    msgstr_plural: dict[str, str]
    is_fuzzy: bool = False


@dataclass(frozen=True)
class POFileData:
    """A PO file discovered in the project workspace.

    Attributes:
        source_path (str): Documented attribute exposed by this type.
        relative_path (str): Documented attribute exposed by this type.
        locale (str): Documented attribute exposed by this type.
        family_key (str): Documented attribute exposed by this type.
        nplurals (int): Documented attribute exposed by this type.
        entries (tuple[POEntryData, ...]): Documented attribute exposed by this type.
    """

    source_path: str
    relative_path: str
    locale: str
    family_key: str
    nplurals: int
    entries: tuple[POEntryData, ...]


@dataclass(frozen=True)
class POCompilationFailure:
    """One PO file whose MO compilation could not be completed.

    Attributes:
        relative_path (str): Documented attribute exposed by this type.
        locale (str): Documented attribute exposed by this type.
        mo_path (str): Documented attribute exposed by this type.
        error_message (str): Documented attribute exposed by this type.
    """

    relative_path: str
    locale: str
    mo_path: str
    error_message: str


@dataclass(frozen=True)
class POProcessingCacheSettings:
    """Per-run cache configuration resolved before PO processing starts.

    Attributes:
        enabled (bool): Documented attribute exposed by this type.
        cache_path (str): Documented attribute exposed by this type.
    """

    enabled: bool
    cache_path: str


@dataclass(frozen=True)
class POProcessingResult:
    """Observable typed outcome for one PO processing run.

    Attributes:
        files_discovered (int): Documented attribute exposed by this type.
        families_processed (int): Documented attribute exposed by this type.
        entries_pending (int): Documented attribute exposed by this type.
        entries_synchronized (int): Documented attribute exposed by this type.
        entries_translated (int): Documented attribute exposed by this type.
        entries_failed (int): Documented attribute exposed by this type.
        files_written (int): Documented attribute exposed by this type.
        mo_files_compiled (int): Documented attribute exposed by this type.
        failures (tuple[POProcessingFailure, ...]): Documented attribute exposed by this type.
        families_found (int): Documented attribute exposed by this type.
        entries_total (int): Documented attribute exposed by this type.
        entries_missing (int): Documented attribute exposed by this type.
        entries_fuzzy (int): Documented attribute exposed by this type.
        entries_completed_from_sync (int): Documented attribute exposed by this type.
        entries_reused_from_other_variant (int): Documented attribute exposed by this type.
        entries_translated_from_cache (int): Documented attribute exposed by this type.
        entries_translated_from_provider (int): Documented attribute exposed by this type.
        entries_skipped_sync_only (int): Documented attribute exposed by this type.
        cache_enabled (bool): Documented attribute exposed by this type.
        dry_run (bool): Documented attribute exposed by this type.
        stats_only (bool): Documented attribute exposed by this type.
        variant_inconsistencies_found (int): Documented attribute exposed by this type.
        variant_inconsistency_details (tuple[str, ...]): Documented attribute exposed by this type.
        compilation_failures (tuple[POCompilationFailure, ...]): Documented attribute exposed by
    this
        type.
    """

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
        """Return the discovered-file count using the legacy metric name.

        Returns:
            int: Structured value returned by this callable.
        """
        return self.files_discovered

    @property
    def entries_translated_from_api(self) -> int:
        """Return provider-backed translations using the legacy metric name.

        Returns:
            int: Structured value returned by this callable.
        """
        return self.entries_translated_from_provider

    @property
    def variant_differences_found(self) -> int:
        """Return variant-difference count using the legacy metric name.

        Returns:
            int: Structured value returned by this callable.
        """
        return self.variant_inconsistencies_found

    @property
    def variant_difference_details(self) -> tuple[str, ...]:
        """Return variant-difference details using the legacy metric name.

        Returns:
            tuple[str, ...]: Structured value returned by this callable.
        """
        return self.variant_inconsistency_details

    @property
    def mo_compiled(self) -> int:
        """Return compiled MO count using the legacy metric name.

        Returns:
            int: Structured value returned by this callable.
        """
        return self.mo_files_compiled


@dataclass(frozen=True)
class POProcessingProgress:
    """Progress update emitted while processing PO families.

    Attributes:
        processed_families (int): Documented attribute exposed by this type.
        completed_entries (int): Documented attribute exposed by this type.
        total_entries (int): Documented attribute exposed by this type.
        files_discovered (int): Documented attribute exposed by this type.
        entries_synchronized (int): Documented attribute exposed by this type.
        entries_translated (int): Documented attribute exposed by this type.
        entries_failed (int): Documented attribute exposed by this type.
        message (str): Documented attribute exposed by this type.
        current_file (str | None): Documented attribute exposed by this type.
        current_entry (str | None): Documented attribute exposed by this type.
    """

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
    """One PO entry that could not be completed during processing.

    Attributes:
        relative_path (str): Documented attribute exposed by this type.
        locale (str): Documented attribute exposed by this type.
        msgid (str): Documented attribute exposed by this type.
        error_message (str): Documented attribute exposed by this type.
    """

    relative_path: str
    locale: str
    msgid: str
    error_message: str
