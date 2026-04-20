"""Application service for shared PO processing workflows."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import re

from polyglot_site_translator.domain.po_processing.contracts import (
    POCatalogRepository,
    POTranslationProvider,
)
from polyglot_site_translator.domain.po_processing.errors import POProcessingTranslationError
from polyglot_site_translator.domain.po_processing.models import (
    POEntryData,
    POEntryId,
    POFileData,
    POProcessingFailure,
    POProcessingProgress,
    POProcessingResult,
)
from polyglot_site_translator.domain.site_registry.locales import (
    parse_default_locale_list,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.infrastructure.po_files import PolibPOCatalogRepository

type TranslationValue = str | dict[str, str]


@dataclass(frozen=True)
class _FamilyProgressUpdate:
    synchronized_entries: int
    translated_entries: int
    failed_entries: int
    current_file: str | None
    current_entry: str | None


@dataclass(frozen=True)
class _FamilyProcessingRuntime:
    translation_provider: POTranslationProvider | None
    progress_callback: Callable[[_FamilyProgressUpdate], None] | None = None


@dataclass(frozen=True)
class _FamilyProgressContext:
    processed_families: int
    total_families: int
    total_entries: int
    files_discovered: int
    synchronized_entries: int
    translated_entries: int
    failed_entries: int


class POProcessingService:
    """Complete missing PO translations across selected locale variants."""

    def __init__(
        self,
        repository: POCatalogRepository | None = None,
        translation_provider: POTranslationProvider | None = None,
    ) -> None:
        self._repository = repository or PolibPOCatalogRepository()
        self._translation_provider = translation_provider

    def process_site(
        self,
        site: RegisteredSite,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingResult:
        configured_locales = parse_default_locale_list(site.default_locale)
        workspace_root = Path(site.local_path)
        discovered_files = self._repository.discover_po_files(workspace_root)
        target_files = _filter_files_by_selected_locales(
            discovered_files=discovered_files,
            locales=configured_locales,
        )
        if target_files == ():
            return POProcessingResult(
                files_discovered=0,
                families_processed=0,
                entries_pending=0,
                entries_synchronized=0,
                entries_translated=0,
                entries_failed=0,
                failures=(),
            )

        selected_locales = _resolve_processing_locales(
            target_files=target_files,
            configured_locales=configured_locales,
        )
        locale_groups = _group_locales_by_base(selected_locales)
        grouped_files = _group_files_by_family(target_files, selected_locales=selected_locales)
        translation_memory = _build_translation_memory(target_files)
        total_families = len(grouped_files)
        total_entries = _count_untranslated_entries(target_files)
        entries_synchronized = 0
        entries_translated = 0
        entries_failed = 0
        failures: list[POProcessingFailure] = []
        current_file: str | None = None
        current_entry: str | None = None

        def emit_progress(event: POProcessingProgress) -> None:
            if progress_callback is None:
                return
            progress_callback(event)

        emit_progress(
            POProcessingProgress(
                processed_families=0,
                completed_entries=0,
                total_entries=total_entries,
                files_discovered=len(target_files),
                entries_synchronized=0,
                entries_translated=0,
                entries_failed=0,
                message=f"Preparing {total_families} PO families for processing.",
            )
        )

        updated_files: list[POFileData] = []
        for processed_families, family_files in enumerate(grouped_files.values(), start=1):
            progress_context = _FamilyProgressContext(
                processed_families=processed_families,
                total_families=total_families,
                total_entries=total_entries,
                files_discovered=len(target_files),
                synchronized_entries=entries_synchronized,
                translated_entries=entries_translated,
                failed_entries=entries_failed,
            )

            def report_family_progress(
                update: _FamilyProgressUpdate,
                context: _FamilyProgressContext = progress_context,
            ) -> None:
                emit_progress(
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
                        entries_translated=context.translated_entries + update.translated_entries,
                        entries_failed=context.failed_entries + update.failed_entries,
                        message=(
                            "Processing PO family "
                            f"{context.processed_families} of {context.total_families}."
                        ),
                        current_file=update.current_file,
                        current_entry=update.current_entry,
                    )
                )

            (
                updated_family_files,
                family_synced,
                family_translated,
                family_failures,
            ) = _process_family(
                family_files=family_files,
                selected_locales=selected_locales,
                locale_groups=locale_groups,
                translation_memory=translation_memory,
                runtime=_FamilyProcessingRuntime(
                    translation_provider=self._translation_provider,
                    progress_callback=report_family_progress,
                ),
            )
            updated_files.extend(updated_family_files)
            entries_synchronized += family_synced
            entries_translated += family_translated
            entries_failed += len(family_failures)
            failures.extend(family_failures)
            if family_failures:
                current_file = family_failures[-1].relative_path
                current_entry = family_failures[-1].msgid
            emit_progress(
                POProcessingProgress(
                    processed_families=processed_families,
                    completed_entries=entries_synchronized + entries_translated,
                    total_entries=total_entries,
                    files_discovered=len(target_files),
                    entries_synchronized=entries_synchronized,
                    entries_translated=entries_translated,
                    entries_failed=entries_failed,
                    message=f"Processed {processed_families} of {total_families} PO families.",
                    current_file=current_file,
                    current_entry=current_entry,
                )
            )

        self._repository.save_po_files(tuple(updated_files))
        return POProcessingResult(
            files_discovered=len(target_files),
            families_processed=total_families,
            entries_pending=total_entries,
            entries_synchronized=entries_synchronized,
            entries_translated=entries_translated,
            entries_failed=entries_failed,
            failures=tuple(failures),
        )


def _filter_files_by_selected_locales(
    *,
    discovered_files: tuple[POFileData, ...],
    locales: tuple[str, ...],
) -> tuple[POFileData, ...]:
    if len(locales) == 1:
        allowed_base_language = _base_language(locales[0])
        return tuple(
            file_data
            for file_data in discovered_files
            if _base_language(file_data.locale) == allowed_base_language
        )
    allowed_locales = set(locales)
    return tuple(file_data for file_data in discovered_files if file_data.locale in allowed_locales)


def _group_locales_by_base(locales: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for locale in locales:
        grouped[_base_language(locale)].append(locale)
    return {base: tuple(items) for base, items in grouped.items()}


def _resolve_processing_locales(
    *,
    target_files: tuple[POFileData, ...],
    configured_locales: tuple[str, ...],
) -> tuple[str, ...]:
    if len(configured_locales) > 1:
        return configured_locales
    ordered_locales: list[str] = []
    configured_locale = configured_locales[0]
    if configured_locale not in ordered_locales:
        ordered_locales.append(configured_locale)
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
    locale_position = {locale: index for index, locale in enumerate(selected_locales)}
    grouped: dict[str, list[POFileData]] = defaultdict(list)
    for file_data in files:
        grouped[file_data.family_key].append(file_data)
    return {
        family_key: tuple(
            sorted(
                family_files,
                key=lambda file_data: locale_position.get(file_data.locale, len(locale_position)),
            )
        )
        for family_key, family_files in grouped.items()
    }


def _build_translation_memory(
    files: tuple[POFileData, ...],
) -> dict[str, dict[POEntryId, TranslationValue]]:
    memory: dict[str, dict[POEntryId, TranslationValue]] = defaultdict(dict)
    for file_data in files:
        for entry in file_data.entries:
            if not _is_translated(entry):
                continue
            memory[file_data.locale][entry.entry_id] = _translation_from_entry(entry)
    return memory


def _count_untranslated_entries(files: tuple[POFileData, ...]) -> int:
    return sum(1 for file_data in files for entry in file_data.entries if not _is_translated(entry))


def _process_family(
    *,
    family_files: tuple[POFileData, ...],
    selected_locales: tuple[str, ...],
    locale_groups: dict[str, tuple[str, ...]],
    translation_memory: dict[str, dict[POEntryId, TranslationValue]],
    runtime: _FamilyProcessingRuntime,
) -> tuple[tuple[POFileData, ...], int, int, tuple[POProcessingFailure, ...]]:
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
    return (
        updated_files,
        synchronized_entries + translated_entries[0],
        translated_entries[1],
        translated_entries[2],
    )


def _synchronize_family(
    *,
    family_entries: dict[str, list[POEntryData]],
    selected_locales: tuple[str, ...],
    locale_groups: dict[str, tuple[str, ...]],
    translation_memory: dict[str, dict[POEntryId, TranslationValue]],
) -> int:
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
                translation_memory.setdefault(related_locale, {})[entry_id] = translation
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
) -> tuple[int, int, tuple[POProcessingFailure, ...]]:
    synchronized_entries = 0
    translated_entries = 0
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
            if _is_translated(entry):
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
                continue
            if not _should_attempt_external_translation(entry):
                continue
            try:
                translation = _translate_entry(
                    entry=entry,
                    locale=locale,
                    nplurals=nplurals_by_locale.get(locale, 2),
                    translation_provider=runtime.translation_provider,
                )
            except POProcessingTranslationError as error:
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
            _apply_translation(entry, translation)
            translation_memory.setdefault(locale, {})[entry.entry_id] = translation
            translated_entries += 1
            synchronized_entries += _propagate_translation_to_family(
                family_entries=family_entries,
                source_locale=locale,
                entry_id=entry.entry_id,
                translation=translation,
                translation_memory=translation_memory,
            )
    return synchronized_entries, translated_entries, tuple(failures)


def _entries_by_key(
    family_entries: dict[str, list[POEntryData]],
) -> dict[POEntryId, dict[str, POEntryData]]:
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
) -> TranslationValue:
    if entry.entry_id.msgid_plural is None:
        return translation_provider.translate_text(
            text=entry.entry_id.msgid,
            target_locale=locale,
        )
    singular = translation_provider.translate_text(
        text=entry.entry_id.msgid,
        target_locale=locale,
    )
    plural = translation_provider.translate_text(
        text=entry.entry_id.msgid_plural,
        target_locale=locale,
    )
    plural_map = {"0": singular}
    for index in range(1, nplurals):
        plural_map[str(index)] = plural
    return plural_map


def _propagate_translation_to_family(
    *,
    family_entries: dict[str, list[POEntryData]],
    source_locale: str,
    entry_id: POEntryId,
    translation: TranslationValue,
    translation_memory: dict[str, dict[POEntryId, TranslationValue]],
) -> int:
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
    for entry in entries:
        if entry.entry_id == entry_id:
            return entry
    return None


def _apply_translation(entry: POEntryData, translation: TranslationValue) -> None:
    if isinstance(translation, dict):
        object.__setattr__(entry, "msgstr", "")
        object.__setattr__(entry, "msgstr_plural", dict(translation))
        return
    object.__setattr__(entry, "msgstr", translation)
    object.__setattr__(entry, "msgstr_plural", {})


def _translation_from_entry(entry: POEntryData) -> TranslationValue:
    if entry.entry_id.msgid_plural is not None:
        return dict(entry.msgstr_plural)
    return entry.msgstr


def _related_locales(
    locale: str,
    *,
    locale_groups: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    base_language = _base_language(locale)
    return tuple(
        candidate for candidate in locale_groups.get(base_language, ()) if candidate != locale
    )


def _base_language(locale: str) -> str:
    return locale.split("_", maxsplit=1)[0].lower()


def _is_effectively_empty_translation(translation: TranslationValue | None) -> bool:
    if translation is None:
        return True
    if isinstance(translation, dict):
        return not any(value.strip() for value in translation.values())
    return translation.strip() == ""


def _should_attempt_external_translation(entry: POEntryData) -> bool:
    singular = entry.entry_id.msgid.strip()
    if _is_hashtag_like_token(singular):
        return False
    plural = entry.entry_id.msgid_plural
    return not (plural is not None and _is_hashtag_like_token(plural.strip()))


def _is_hashtag_like_token(text: str) -> bool:
    return re.fullmatch(r"#[A-Za-z0-9_-]+", text) is not None


def _is_translated(entry: POEntryData) -> bool:
    if entry.entry_id.msgid_plural is not None:
        if entry.msgstr_plural == {}:
            return False
        return all(value.strip() != "" for value in entry.msgstr_plural.values())
    return entry.msgstr.strip() != ""
