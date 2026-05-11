"""Application service for shared PO processing workflows."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import re

from polyglot_site_translator.domain.po_processing.contracts import (
    POCatalogRepository,
    POTranslationCache,
    POTranslationCacheFactory,
    POTranslationProvider,
)
from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingCacheError,
    POProcessingCompilationError,
    POProcessingTranslationError,
)
from polyglot_site_translator.domain.po_processing.models import (
    POCompilationFailure,
    POEntryData,
    POEntryId,
    POFileData,
    POProcessingCacheSettings,
    POProcessingFailure,
    POProcessingProgress,
    POProcessingResult,
)
from polyglot_site_translator.domain.site_registry.locales import (
    parse_default_locale_list,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.infrastructure.po_files import PolibPOCatalogRepository
from polyglot_site_translator.infrastructure.po_translation_cache_shelve import (
    build_shelve_translation_cache,
)

TranslationValue = str | dict[str, str]
_MIN_TRANSLATED_VARIANTS_FOR_INCONSISTENCY = 2


def _emit_po_processing_progress(
    progress_callback: Callable[[POProcessingProgress], None] | None,
    event: POProcessingProgress,
) -> None:
    """Emit one progress event when the caller provided a workflow callback.

    Args:
        progress_callback:
            Value supplied to this callable.
        event:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if progress_callback is None:
        return
    progress_callback(event)


def _build_empty_processing_result(
    *,
    site: RegisteredSite,
    cache_settings: POProcessingCacheSettings,
) -> POProcessingResult:
    """Build the empty-result shape used when no selected PO files were discovered.

    Args:
        site:
            Value supplied to this callable.
        cache_settings:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return POProcessingResult(
        files_discovered=0,
        families_processed=0,
        entries_pending=0,
        entries_synchronized=0,
        entries_translated=0,
        entries_failed=0,
        files_written=0,
        mo_files_compiled=0,
        failures=(),
        families_found=0,
        entries_total=0,
        entries_missing=0,
        entries_fuzzy=0,
        entries_completed_from_sync=0,
        entries_reused_from_other_variant=0,
        entries_translated_from_cache=0,
        entries_translated_from_provider=0,
        entries_skipped_sync_only=0,
        cache_enabled=cache_settings.enabled,
        dry_run=site.dry_run,
        stats_only=site.stats_only,
    )


@dataclass(frozen=True)
class _FamilyProgressUpdate:
    """Provide FamilyProgressUpdate behavior for this module.

    Attributes:
        synchronized_entries:
            Documented attribute exposed by this type.
        translated_entries:
            Documented attribute exposed by this type.
        failed_entries:
            Documented attribute exposed by this type.
        current_file:
            Documented attribute exposed by this type.
        current_entry:
            Documented attribute exposed by this type.
    """

    synchronized_entries: int
    translated_entries: int
    failed_entries: int
    current_file: str | None
    current_entry: str | None


@dataclass(frozen=True)
class _FamilyProcessingRuntime:
    """Provide FamilyProcessingRuntime behavior for this module.

    Attributes:
        translation_provider:
            Documented attribute exposed by this type.
        translation_cache:
            Documented attribute exposed by this type.
        progress_callback:
            Documented attribute exposed by this type.
        only_fuzzy:
            Documented attribute exposed by this type.
    """

    translation_provider: POTranslationProvider | None
    translation_cache: POTranslationCache | None = None
    progress_callback: Callable[[_FamilyProgressUpdate], None] | None = None
    only_fuzzy: bool = False


@dataclass(frozen=True)
class _FamilyProgressContext:
    """Provide FamilyProgressContext behavior for this module.

    Attributes:
        processed_families:
            Documented attribute exposed by this type.
        total_families:
            Documented attribute exposed by this type.
        total_entries:
            Documented attribute exposed by this type.
        files_discovered:
            Documented attribute exposed by this type.
        synchronized_entries:
            Documented attribute exposed by this type.
        translated_entries:
            Documented attribute exposed by this type.
        failed_entries:
            Documented attribute exposed by this type.
    """

    processed_families: int
    total_families: int
    total_entries: int
    files_discovered: int
    synchronized_entries: int
    translated_entries: int
    failed_entries: int


@dataclass(frozen=True)
class _TranslationPassOutcome:
    """Provide TranslationPassOutcome behavior for this module.

    Attributes:
        synchronized_entries:
            Documented attribute exposed by this type.
        reused_from_other_variant:
            Documented attribute exposed by this type.
        translated_entries:
            Documented attribute exposed by this type.
        translated_from_cache:
            Documented attribute exposed by this type.
        translated_from_provider:
            Documented attribute exposed by this type.
        skipped_sync_only:
            Documented attribute exposed by this type.
        failures:
            Documented attribute exposed by this type.
    """

    synchronized_entries: int
    reused_from_other_variant: int
    translated_entries: int
    translated_from_cache: int
    translated_from_provider: int
    skipped_sync_only: int
    failures: tuple[POProcessingFailure, ...]


@dataclass(frozen=True)
class _FamilyProcessingOutcome:
    """Provide FamilyProcessingOutcome behavior for this module.

    Attributes:
        updated_files:
            Documented attribute exposed by this type.
        synchronized_entries:
            Documented attribute exposed by this type.
        initial_sync_entries:
            Documented attribute exposed by this type.
        reused_from_other_variant:
            Documented attribute exposed by this type.
        translated_entries:
            Documented attribute exposed by this type.
        translated_from_cache:
            Documented attribute exposed by this type.
        translated_from_provider:
            Documented attribute exposed by this type.
        skipped_sync_only:
            Documented attribute exposed by this type.
        failures:
            Documented attribute exposed by this type.
    """

    updated_files: tuple[POFileData, ...]
    synchronized_entries: int
    initial_sync_entries: int
    reused_from_other_variant: int
    translated_entries: int
    translated_from_cache: int
    translated_from_provider: int
    skipped_sync_only: int
    failures: tuple[POProcessingFailure, ...]


class POProcessingService:
    """Complete missing PO translations across selected locale variants.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def __init__(
        self,
        repository: POCatalogRepository | None = None,
        translation_provider: POTranslationProvider | None = None,
        translation_cache_factory: POTranslationCacheFactory | None = None,
    ) -> None:
        """Store repository, translation provider, and cache factory dependencies.

        Args:
            self:
                Value supplied to this callable.
            repository:
                Value supplied to this callable.
            translation_provider:
                Value supplied to this callable.
            translation_cache_factory:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        self._repository = repository or PolibPOCatalogRepository()
        self._translation_provider = translation_provider
        self._translation_cache_factory = (
            translation_cache_factory or build_shelve_translation_cache
        )

    def process_site(
        self,
        site: RegisteredSite,
        cache_settings: POProcessingCacheSettings | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingResult:
        """Run the full shared PO workflow for one persisted site workspace.

        Args:
            self:
                Value supplied to this callable.
            site:
                Value supplied to this callable.
            cache_settings:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        resolved_cache_settings = _resolve_cache_settings(
            site=site, cache_settings=cache_settings
        )
        cache = self._translation_cache_factory(
            cache_path=Path(resolved_cache_settings.cache_path),
            enabled=resolved_cache_settings.enabled,
        )
        cache.open()
        try:
            return self._process_site_with_cache(
                site=site,
                cache=cache,
                cache_settings=resolved_cache_settings,
                progress_callback=progress_callback,
            )
        finally:
            cache.close()

    def _process_site_with_cache(
        self,
        *,
        site: RegisteredSite,
        cache: POTranslationCache,
        cache_settings: POProcessingCacheSettings,
        progress_callback: Callable[[POProcessingProgress], None] | None,
    ) -> POProcessingResult:
        """Process discovered PO files using an already-open translation cache.

        Args:
            self:
                Value supplied to this callable.
            site:
                Value supplied to this callable.
            cache:
                Value supplied to this callable.
            cache_settings:
                Value supplied to this callable.
            progress_callback:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        configured_locales = parse_default_locale_list(site.default_locale)
        workspace_root = Path(site.local_path)
        discovered_files = self._repository.discover_po_files(workspace_root)
        target_files = _filter_files_by_selected_locales(
            discovered_files=discovered_files,
            locales=configured_locales,
        )
        if target_files == ():
            return _build_empty_processing_result(
                site=site, cache_settings=cache_settings
            )

        selected_locales = _resolve_processing_locales(
            target_files=target_files,
            configured_locales=configured_locales,
        )
        locale_groups = _group_locales_by_base(selected_locales)
        grouped_files = _group_files_by_family(
            target_files, selected_locales=selected_locales
        )
        translation_memory = _build_translation_memory(target_files)
        files_discovered = len(target_files)
        total_families = len(grouped_files)
        total_entries = _count_total_entries(target_files)
        missing_entries = _count_untranslated_entries(target_files)
        fuzzy_entries = _count_fuzzy_entries(target_files)
        pending_entries = _count_pending_entries(
            target_files, only_fuzzy=site.only_fuzzy
        )
        entries_synchronized = entries_completed_from_sync = (
            entries_reused_from_other_variant
        ) = 0
        entries_translated = entries_translated_from_cache = (
            entries_translated_from_provider
        ) = 0
        entries_skipped_sync_only = entries_failed = 0
        failures: list[POProcessingFailure] = []
        current_file = current_entry = None

        _emit_po_processing_progress(
            progress_callback,
            POProcessingProgress(
                processed_families=0,
                completed_entries=0,
                total_entries=pending_entries,
                files_discovered=files_discovered,
                entries_synchronized=0,
                entries_translated=0,
                entries_failed=0,
                message=f"Preparing {total_families} PO families for processing.",
            ),
        )

        updated_files: list[POFileData] = []
        for processed_families, family_files in enumerate(
            grouped_files.values(), start=1
        ):
            progress_context = _FamilyProgressContext(
                processed_families=processed_families,
                total_families=total_families,
                total_entries=pending_entries,
                files_discovered=files_discovered,
                synchronized_entries=entries_synchronized,
                translated_entries=entries_translated,
                failed_entries=entries_failed,
            )

            def report_family_progress(
                update: _FamilyProgressUpdate,
                context: _FamilyProgressContext = progress_context,
            ) -> None:
                """Emit the current family-level progress snapshot through the workflow.

                callback.

                Args:
                    update:
                        Value supplied to this callable.
                    context:
                        Value supplied to this callable.

                Returns:
                    value:
                        Structured value returned by this callable.
                """
                _emit_po_processing_progress(
                    progress_callback,
                    POProcessingProgress(
                        processed_families=context.processed_families - 1,
                        completed_entries=(
                            context.synchronized_entries
                            + context.translated_entries
                            + update.synchronized_entries
                            + update.translated_entries
                        ),
                        total_entries=context.total_entries,
                        files_discovered=context.files_discovered,
                        entries_synchronized=context.synchronized_entries
                        + update.synchronized_entries,
                        entries_translated=context.translated_entries
                        + update.translated_entries,
                        entries_failed=context.failed_entries + update.failed_entries,
                        message=(
                            "Processing PO family "
                            f"{context.processed_families} of {context.total_families}."
                        ),
                        current_file=update.current_file,
                        current_entry=update.current_entry,
                    ),
                )

            family_outcome = _process_family(
                family_files=family_files,
                selected_locales=selected_locales,
                locale_groups=locale_groups,
                translation_memory=translation_memory,
                runtime=_FamilyProcessingRuntime(
                    translation_provider=(
                        self._translation_provider
                        if site.use_external_translator
                        else None
                    ),
                    translation_cache=cache,
                    progress_callback=report_family_progress,
                    only_fuzzy=site.only_fuzzy,
                ),
            )
            updated_files.extend(family_outcome.updated_files)
            entries_synchronized += family_outcome.synchronized_entries
            entries_completed_from_sync += family_outcome.initial_sync_entries
            entries_reused_from_other_variant += (
                family_outcome.reused_from_other_variant
            )
            entries_translated += family_outcome.translated_entries
            entries_translated_from_cache += family_outcome.translated_from_cache
            entries_translated_from_provider += family_outcome.translated_from_provider
            entries_skipped_sync_only += family_outcome.skipped_sync_only
            entries_failed += len(family_outcome.failures)
            failures.extend(family_outcome.failures)
            if family_outcome.failures:
                current_file = family_outcome.failures[-1].relative_path
                current_entry = family_outcome.failures[-1].msgid
            _emit_po_processing_progress(
                progress_callback,
                POProcessingProgress(
                    processed_families=processed_families,
                    completed_entries=entries_synchronized + entries_translated,
                    total_entries=pending_entries,
                    files_discovered=files_discovered,
                    entries_synchronized=entries_synchronized,
                    entries_translated=entries_translated,
                    entries_failed=entries_failed,
                    message=(
                        f"Processed {processed_families} of "
                        f"{total_families} PO families."
                    ),
                    current_file=current_file,
                    current_entry=current_entry,
                ),
            )

        inconsistency_details = _detect_variant_inconsistencies(
            grouped_files=tuple(updated_files),
            enabled=site.report_inconsistencies,
        )
        if site.stats_only or site.dry_run:
            return POProcessingResult(
                files_discovered=files_discovered,
                families_processed=total_families,
                entries_pending=pending_entries,
                entries_synchronized=entries_synchronized,
                entries_translated=entries_translated,
                entries_failed=entries_failed,
                files_written=0,
                mo_files_compiled=0,
                failures=tuple(failures),
                families_found=total_families,
                entries_total=total_entries,
                entries_missing=missing_entries,
                entries_fuzzy=fuzzy_entries,
                entries_completed_from_sync=entries_completed_from_sync,
                entries_reused_from_other_variant=entries_reused_from_other_variant,
                entries_translated_from_cache=entries_translated_from_cache,
                entries_translated_from_provider=entries_translated_from_provider,
                entries_skipped_sync_only=entries_skipped_sync_only,
                cache_enabled=cache_settings.enabled,
                dry_run=site.dry_run,
                stats_only=site.stats_only,
                variant_inconsistencies_found=len(inconsistency_details),
                variant_inconsistency_details=tuple(inconsistency_details),
                compilation_failures=(),
            )
        self._repository.save_po_files(tuple(updated_files))
        files_written = len(updated_files)
        if not site.compile_mo:
            return POProcessingResult(
                files_discovered=files_discovered,
                families_processed=total_families,
                entries_pending=pending_entries,
                entries_synchronized=entries_synchronized,
                entries_translated=entries_translated,
                entries_failed=entries_failed,
                files_written=files_written,
                mo_files_compiled=0,
                failures=tuple(failures),
                families_found=total_families,
                entries_total=total_entries,
                entries_missing=missing_entries,
                entries_fuzzy=fuzzy_entries,
                entries_completed_from_sync=entries_completed_from_sync,
                entries_reused_from_other_variant=entries_reused_from_other_variant,
                entries_translated_from_cache=entries_translated_from_cache,
                entries_translated_from_provider=entries_translated_from_provider,
                entries_skipped_sync_only=entries_skipped_sync_only,
                cache_enabled=cache_settings.enabled,
                dry_run=site.dry_run,
                stats_only=site.stats_only,
                variant_inconsistencies_found=len(inconsistency_details),
                variant_inconsistency_details=tuple(inconsistency_details),
                compilation_failures=(),
            )
        mo_files_compiled, compilation_failures = _compile_mo_files(
            repository=self._repository,
            files=tuple(updated_files),
        )
        return POProcessingResult(
            files_discovered=files_discovered,
            families_processed=total_families,
            entries_pending=pending_entries,
            entries_synchronized=entries_synchronized,
            entries_translated=entries_translated,
            entries_failed=entries_failed,
            files_written=files_written,
            mo_files_compiled=mo_files_compiled,
            failures=tuple(failures),
            families_found=total_families,
            entries_total=total_entries,
            entries_missing=missing_entries,
            entries_fuzzy=fuzzy_entries,
            entries_completed_from_sync=entries_completed_from_sync,
            entries_reused_from_other_variant=entries_reused_from_other_variant,
            entries_translated_from_cache=entries_translated_from_cache,
            entries_translated_from_provider=entries_translated_from_provider,
            entries_skipped_sync_only=entries_skipped_sync_only,
            cache_enabled=cache_settings.enabled,
            dry_run=site.dry_run,
            stats_only=site.stats_only,
            variant_inconsistencies_found=len(inconsistency_details),
            variant_inconsistency_details=tuple(inconsistency_details),
            compilation_failures=tuple(compilation_failures),
        )


def _compile_mo_files(
    *,
    repository: POCatalogRepository,
    files: tuple[POFileData, ...],
) -> tuple[int, list[POCompilationFailure]]:
    """Handle compile mo files.

    Args:
        repository:
            Value supplied to this callable.
        files:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    compiled = 0
    failures: list[POCompilationFailure] = []
    for file_data in files:
        try:
            repository.compile_mo_file(file_data)
        except POProcessingCompilationError as error:
            failures.append(
                POCompilationFailure(
                    relative_path=file_data.relative_path,
                    locale=file_data.locale,
                    mo_path=str(Path(file_data.relative_path).with_suffix(".mo")),
                    error_message=str(error),
                )
            )
            continue
        compiled += 1
    return compiled, failures


def _detect_variant_inconsistencies(
    *,
    grouped_files: tuple[POFileData, ...],
    enabled: bool,
) -> list[str]:
    """Detect variant inconsistencies.

    Args:
        grouped_files:
            Value supplied to this callable.
        enabled:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if not enabled:
        return []
    family_entries = {
        file_data.locale: list(file_data.entries) for file_data in grouped_files
    }
    entry_map = _entries_by_key(family_entries)
    details: list[str] = []
    for entry_id, entries_by_locale in entry_map.items():
        translated_values = {
            locale: _canonical_translation_value(_translation_from_entry(entry))
            for locale, entry in entries_by_locale.items()
            if _is_translated(entry)
        }
        if len(translated_values) < _MIN_TRANSLATED_VARIANTS_FOR_INCONSISTENCY:
            continue
        if len(set(translated_values.values())) <= 1:
            continue
        context_label = (
            entry_id.context if entry_id.context is not None else "<sin contexto>"
        )
        details.append(
            "Diferencia entre variantes: "
            f"{grouped_files[0].family_key} | msgctxt='{context_label}' | "
            f"msgid='{entry_id.msgid}' | locales={', '.join(sorted(translated_values))}"
        )
    return details


def _canonical_translation_value(value: TranslationValue) -> str:
    """Handle canonical translation value.

    Args:
        value:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if isinstance(value, dict):
        return "\x1f".join(f"{key}={value[key]}" for key in sorted(value))
    return value


def _filter_files_by_selected_locales(
    *,
    discovered_files: tuple[POFileData, ...],
    locales: tuple[str, ...],
) -> tuple[POFileData, ...]:
    """Filter files by selected locales.

    Args:
        discovered_files:
            Value supplied to this callable.
        locales:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if len(locales) == 1:
        allowed_base_language = _base_language(locales[0])
        return tuple(
            file_data
            for file_data in discovered_files
            if _base_language(file_data.locale) == allowed_base_language
        )
    allowed_locales = set(locales)
    return tuple(
        file_data
        for file_data in discovered_files
        if file_data.locale in allowed_locales
    )


def _group_locales_by_base(locales: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    """Group locales by base.

    Args:
        locales:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    grouped: dict[str, list[str]] = defaultdict(list)
    for locale in locales:
        grouped[_base_language(locale)].append(locale)
    return {base: tuple(items) for base, items in grouped.items()}


def _resolve_processing_locales(
    *,
    target_files: tuple[POFileData, ...],
    configured_locales: tuple[str, ...],
) -> tuple[str, ...]:
    """Resolve processing locales.

    Args:
        target_files:
            Value supplied to this callable.
        configured_locales:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if len(configured_locales) > 1:
        return configured_locales
    ordered_locales: list[str] = [configured_locales[0]]
    for file_data in target_files:
        if file_data.locale in ordered_locales:
            continue
        ordered_locales.append(file_data.locale)
    return tuple(ordered_locales)


def _group_files_by_family(
    files: tuple[POFileData, ...],
    *,
    selected_locales: tuple[str, ...],
) -> dict[str, tuple[POFileData, ...]]:
    """Group files by family.

    Args:
        files:
            Value supplied to this callable.
        selected_locales:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    locale_position = {locale: index for index, locale in enumerate(selected_locales)}
    grouped: dict[str, list[POFileData]] = defaultdict(list)
    for file_data in files:
        grouped[file_data.family_key].append(file_data)
    return {
        family_key: tuple(
            sorted(
                family_files,
                key=lambda file_data: locale_position.get(
                    file_data.locale, len(locale_position)
                ),
            )
        )
        for family_key, family_files in grouped.items()
    }


def _build_translation_memory(
    files: tuple[POFileData, ...],
) -> dict[str, dict[POEntryId, TranslationValue]]:
    """Build translation memory.

    Args:
        files:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    memory: dict[str, dict[POEntryId, TranslationValue]] = defaultdict(dict)
    for file_data in files:
        for entry in file_data.entries:
            if not _is_translated(entry):
                continue
            memory[file_data.locale][entry.entry_id] = _translation_from_entry(entry)
    return memory


def _count_untranslated_entries(files: tuple[POFileData, ...]) -> int:
    """Count untranslated entries.

    Args:
        files:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return sum(
        1
        for file_data in files
        for entry in file_data.entries
        if not _is_translated(entry)
    )


def _count_total_entries(files: tuple[POFileData, ...]) -> int:
    """Count total entries.

    Args:
        files:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return sum(len(file_data.entries) for file_data in files)


def _count_fuzzy_entries(files: tuple[POFileData, ...]) -> int:
    """Count fuzzy entries.

    Args:
        files:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return sum(
        1 for file_data in files for entry in file_data.entries if entry.is_fuzzy
    )


def _count_pending_entries(files: tuple[POFileData, ...], *, only_fuzzy: bool) -> int:
    """Count pending entries.

    Args:
        files:
            Value supplied to this callable.
        only_fuzzy:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return sum(
        1
        for file_data in files
        for entry in file_data.entries
        if _should_process_entry_for_translation(entry, only_fuzzy=only_fuzzy)
    )


def _process_family(
    *,
    family_files: tuple[POFileData, ...],
    selected_locales: tuple[str, ...],
    locale_groups: dict[str, tuple[str, ...]],
    translation_memory: dict[str, dict[POEntryId, TranslationValue]],
    runtime: _FamilyProcessingRuntime,
) -> _FamilyProcessingOutcome:
    """Handle process family.

    Args:
        family_files:
            Value supplied to this callable.
        selected_locales:
            Value supplied to this callable.
        locale_groups:
            Value supplied to this callable.
        translation_memory:
            Value supplied to this callable.
        runtime:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    file_by_locale = {file_data.locale: file_data for file_data in family_files}
    family_entries: dict[str, list[POEntryData]] = {
        file_data.locale: list(file_data.entries) for file_data in family_files
    }
    synchronized_entries = _synchronize_family(
        family_entries=family_entries,
        selected_locales=selected_locales,
        locale_groups=locale_groups,
        translation_memory=translation_memory,
    )
    translated_entries = _translate_missing_entries(
        family_entries=family_entries,
        selected_locales=selected_locales,
        file_by_locale=file_by_locale,
        translation_memory=translation_memory,
        runtime=runtime,
    )
    updated_files = tuple(
        POFileData(
            source_path=file_data.source_path,
            relative_path=file_data.relative_path,
            locale=file_data.locale,
            family_key=file_data.family_key,
            nplurals=file_data.nplurals,
            entries=tuple(family_entries[file_data.locale]),
        )
        for file_data in family_files
    )
    return _FamilyProcessingOutcome(
        updated_files=updated_files,
        synchronized_entries=synchronized_entries
        + translated_entries.synchronized_entries,
        initial_sync_entries=synchronized_entries,
        reused_from_other_variant=translated_entries.reused_from_other_variant,
        translated_entries=translated_entries.translated_entries,
        translated_from_cache=translated_entries.translated_from_cache,
        translated_from_provider=translated_entries.translated_from_provider,
        skipped_sync_only=translated_entries.skipped_sync_only,
        failures=translated_entries.failures,
    )


def _synchronize_family(
    *,
    family_entries: dict[str, list[POEntryData]],
    selected_locales: tuple[str, ...],
    locale_groups: dict[str, tuple[str, ...]],
    translation_memory: dict[str, dict[POEntryId, TranslationValue]],
) -> int:
    """Handle synchronize family.

    Args:
        family_entries:
            Value supplied to this callable.
        selected_locales:
            Value supplied to this callable.
        locale_groups:
            Value supplied to this callable.
        translation_memory:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    entry_map = _entries_by_key(family_entries)
    synchronized_entries = 0
    for entry_id, entries_by_locale in entry_map.items():
        for locale in selected_locales:
            source_entry = entries_by_locale.get(locale)
            if source_entry is None or not _is_translated(source_entry):
                continue
            translation = _translation_from_entry(source_entry)
            for related_locale in _related_locales(
                locale,
                locale_groups=locale_groups,
            ):
                target_entry = entries_by_locale.get(related_locale)
                if target_entry is None or _is_translated(target_entry):
                    continue
                _apply_translation(target_entry, translation)
                translation_memory.setdefault(related_locale, {})[entry_id] = (
                    translation
                )
                synchronized_entries += 1
            break
    return synchronized_entries


def _translate_missing_entries(
    *,
    family_entries: dict[str, list[POEntryData]],
    selected_locales: tuple[str, ...],
    translation_memory: dict[str, dict[POEntryId, TranslationValue]],
    file_by_locale: dict[str, POFileData],
    runtime: _FamilyProcessingRuntime,
) -> _TranslationPassOutcome:
    """Handle translate missing entries.

    Args:
        family_entries:
            Value supplied to this callable.
        selected_locales:
            Value supplied to this callable.
        translation_memory:
            Value supplied to this callable.
        file_by_locale:
            Value supplied to this callable.
        runtime:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    synchronized_entries = 0
    reused_from_other_variant = 0
    translated_entries = 0
    translated_from_cache = 0
    translated_from_provider = 0
    skipped_sync_only = 0
    failures: list[POProcessingFailure] = []
    locale_groups = _group_locales_by_base(selected_locales)
    nplurals_by_locale = {
        locale: file_data.nplurals for locale, file_data in file_by_locale.items()
    }
    for locale in selected_locales:
        entries = family_entries.get(locale)
        if entries is None:
            continue
        for entry in entries:
            if not _should_process_entry_for_translation(
                entry, only_fuzzy=runtime.only_fuzzy
            ):
                continue
            if runtime.progress_callback is not None:
                runtime.progress_callback(
                    _FamilyProgressUpdate(
                        synchronized_entries=synchronized_entries,
                        translated_entries=translated_entries,
                        failed_entries=len(failures),
                        current_file=file_by_locale[locale].relative_path,
                        current_entry=entry.entry_id.msgid,
                    )
                )
            candidate = _candidate_translation_from_memory(
                locale=locale,
                entry_id=entry.entry_id,
                locale_groups=locale_groups,
                translation_memory=translation_memory,
            )
            if candidate is not None:
                _apply_translation(entry, candidate)
                translation_memory.setdefault(locale, {})[entry.entry_id] = candidate
                reused_from_other_variant += 1
                synchronized_entries += 1
                synchronized_entries += _propagate_translation_to_family(
                    family_entries=family_entries,
                    source_locale=locale,
                    entry_id=entry.entry_id,
                    translation=candidate,
                    translation_memory=translation_memory,
                )
                continue
            if runtime.translation_provider is None:
                skipped_sync_only += 1
                continue
            if not _should_attempt_external_translation(entry):
                continue
            try:
                translation = _translate_entry(
                    entry=entry,
                    locale=locale,
                    nplurals=nplurals_by_locale.get(locale, 2),
                    translation_provider=runtime.translation_provider,
                    translation_cache=runtime.translation_cache,
                )
            except (POProcessingTranslationError, POProcessingCacheError) as error:
                file_data = file_by_locale[locale]
                failures.append(
                    POProcessingFailure(
                        relative_path=file_data.relative_path,
                        locale=locale,
                        msgid=entry.entry_id.msgid,
                        error_message=str(error),
                    )
                )
                continue
            _apply_translation(entry, translation[0])
            translation_memory.setdefault(locale, {})[entry.entry_id] = translation[0]
            translated_entries += 1
            if translation[1] == "cache":
                translated_from_cache += 1
            else:
                translated_from_provider += 1
            synchronized_entries += _propagate_translation_to_family(
                family_entries=family_entries,
                source_locale=locale,
                entry_id=entry.entry_id,
                translation=translation[0],
                translation_memory=translation_memory,
            )
    return _TranslationPassOutcome(
        synchronized_entries=synchronized_entries,
        reused_from_other_variant=reused_from_other_variant,
        translated_entries=translated_entries,
        translated_from_cache=translated_from_cache,
        translated_from_provider=translated_from_provider,
        skipped_sync_only=skipped_sync_only,
        failures=tuple(failures),
    )


def _entries_by_key(
    family_entries: dict[str, list[POEntryData]],
) -> dict[POEntryId, dict[str, POEntryData]]:
    """Handle entries by key.

    Args:
        family_entries:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    indexed: dict[POEntryId, dict[str, POEntryData]] = defaultdict(dict)
    for locale, entries in family_entries.items():
        for entry in entries:
            indexed[entry.entry_id][locale] = entry
    return indexed


def _candidate_translation_from_memory(
    *,
    locale: str,
    entry_id: POEntryId,
    locale_groups: dict[str, tuple[str, ...]],
    translation_memory: dict[str, dict[POEntryId, TranslationValue]],
) -> TranslationValue | None:
    """Handle candidate translation from memory.

    Args:
        locale:
            Value supplied to this callable.
        entry_id:
            Value supplied to this callable.
        locale_groups:
            Value supplied to this callable.
        translation_memory:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    for related_locale in _related_locales(locale, locale_groups=locale_groups):
        candidate = translation_memory.get(related_locale, {}).get(entry_id)
        if _is_effectively_empty_translation(candidate):
            continue
        return candidate
    return None


def _translate_entry(
    *,
    entry: POEntryData,
    locale: str,
    nplurals: int,
    translation_provider: POTranslationProvider,
    translation_cache: POTranslationCache | None,
) -> tuple[TranslationValue, str]:
    """Handle translate entry.

    Args:
        entry:
            Value supplied to this callable.
        locale:
            Value supplied to this callable.
        nplurals:
            Value supplied to this callable.
        translation_provider:
            Value supplied to this callable.
        translation_cache:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if entry.entry_id.msgid_plural is None:
        translated_text, source = _translate_text(
            text=entry.entry_id.msgid,
            locale=locale,
            translation_provider=translation_provider,
            translation_cache=translation_cache,
        )
        return translated_text, source
    singular, singular_source = _translate_text(
        text=entry.entry_id.msgid,
        locale=locale,
        translation_provider=translation_provider,
        translation_cache=translation_cache,
    )
    plural, plural_source = _translate_text(
        text=entry.entry_id.msgid_plural,
        locale=locale,
        translation_provider=translation_provider,
        translation_cache=translation_cache,
    )
    plural_map = {"0": singular}
    for index in range(1, nplurals):
        plural_map[str(index)] = plural
    source = (
        "cache"
        if singular_source == "cache" and plural_source == "cache"
        else "provider"
    )
    return plural_map, source


def _translate_text(
    *,
    text: str,
    locale: str,
    translation_provider: POTranslationProvider,
    translation_cache: POTranslationCache | None,
) -> tuple[str, str]:
    """Handle translate text.

    Args:
        text:
            Value supplied to this callable.
        locale:
            Value supplied to this callable.
        translation_provider:
            Value supplied to this callable.
        translation_cache:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    base_language = _base_language(locale)
    if translation_cache is not None:
        cached = translation_cache.get(base_language=base_language, text=text)
        if cached is not None:
            return cached, "cache"
    translated_text = translation_provider.translate_text(
        text=text,
        target_locale=locale,
    )
    if translation_cache is not None:
        translation_cache.set(
            base_language=base_language,
            text=text,
            translated_text=translated_text,
        )
    return translated_text, "provider"


def _resolve_cache_settings(
    *,
    site: RegisteredSite,
    cache_settings: POProcessingCacheSettings | None,
) -> POProcessingCacheSettings:
    """Resolve cache settings.

    Args:
        site:
            Value supplied to this callable.
        cache_settings:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if cache_settings is not None:
        return cache_settings
    return POProcessingCacheSettings(
        enabled=site.use_translation_cache,
        cache_path=str(Path(site.local_path) / ".po_translation_cache"),
    )


def _propagate_translation_to_family(
    *,
    family_entries: dict[str, list[POEntryData]],
    source_locale: str,
    entry_id: POEntryId,
    translation: TranslationValue,
    translation_memory: dict[str, dict[POEntryId, TranslationValue]],
) -> int:
    """Handle propagate translation to family.

    Args:
        family_entries:
            Value supplied to this callable.
        source_locale:
            Value supplied to this callable.
        entry_id:
            Value supplied to this callable.
        translation:
            Value supplied to this callable.
        translation_memory:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    propagated_entries = 0
    translation_base = _base_language(source_locale)
    for locale, entries in family_entries.items():
        if _base_language(locale) != translation_base or locale == source_locale:
            continue
        target_entry = _find_entry(entries, entry_id)
        if target_entry is None or _is_translated(target_entry):
            continue
        _apply_translation(target_entry, translation)
        translation_memory.setdefault(locale, {})[entry_id] = translation
        propagated_entries += 1
    return propagated_entries


def _find_entry(entries: list[POEntryData], entry_id: POEntryId) -> POEntryData | None:
    """Find entry.

    Args:
        entries:
            Value supplied to this callable.
        entry_id:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    for entry in entries:
        if entry.entry_id == entry_id:
            return entry
    return None


def _apply_translation(entry: POEntryData, translation: TranslationValue) -> None:
    """Apply translation.

    Args:
        entry:
            Value supplied to this callable.
        translation:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if isinstance(translation, dict):
        object.__setattr__(entry, "msgstr", "")
        object.__setattr__(entry, "msgstr_plural", dict(translation))
        return
    object.__setattr__(entry, "msgstr", translation)
    object.__setattr__(entry, "msgstr_plural", {})


def _translation_from_entry(entry: POEntryData) -> TranslationValue:
    """Handle translation from entry.

    Args:
        entry:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if entry.entry_id.msgid_plural is not None:
        return dict(entry.msgstr_plural)
    return entry.msgstr


def _related_locales(
    locale: str,
    *,
    locale_groups: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Handle related locales.

    Args:
        locale:
            Value supplied to this callable.
        locale_groups:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    base_language = _base_language(locale)
    return tuple(
        candidate
        for candidate in locale_groups.get(base_language, ())
        if candidate != locale
    )


def _base_language(locale: str) -> str:
    """Handle base language.

    Args:
        locale:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return locale.split("_", maxsplit=1)[0].lower()


def _is_effectively_empty_translation(translation: TranslationValue | None) -> bool:
    """Handle is effectively empty translation.

    Args:
        translation:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if translation is None:
        return True
    if isinstance(translation, dict):
        return not any(value.strip() for value in translation.values())
    return translation.strip() == ""


def _should_attempt_external_translation(entry: POEntryData) -> bool:
    """Handle should attempt external translation.

    Args:
        entry:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    singular = entry.entry_id.msgid.strip()
    if _is_hashtag_like_token(singular):
        return False
    plural = entry.entry_id.msgid_plural
    return not (plural is not None and _is_hashtag_like_token(plural.strip()))


def _should_process_entry_for_translation(
    entry: POEntryData, *, only_fuzzy: bool
) -> bool:
    """Handle should process entry for translation.

    Args:
        entry:
            Value supplied to this callable.
        only_fuzzy:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if _is_translated(entry):
        return False
    if only_fuzzy:
        return entry.is_fuzzy
    return True


def _is_hashtag_like_token(text: str) -> bool:
    """Handle is hashtag like token.

    Args:
        text:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return re.fullmatch(r"#[A-Za-z0-9_-]+", text) is not None


def _is_translated(entry: POEntryData) -> bool:
    """Handle is translated.

    Args:
        entry:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if entry.entry_id.msgid_plural is not None:
        if entry.msgstr_plural == {}:
            return False
        return all(value.strip() != "" for value in entry.msgstr_plural.values())
    return entry.msgstr.strip() != ""
