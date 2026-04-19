"""Application service for shared PO processing workflows."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from polyglot_site_translator.domain.po_processing.contracts import (
    POCatalogRepository,
    POTranslationProvider,
)
from polyglot_site_translator.domain.po_processing.models import (
    POEntryData,
    POEntryId,
    POFileData,
    POProcessingProgress,
    POProcessingResult,
)
from polyglot_site_translator.domain.site_registry.locales import (
    parse_default_locale_list,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.infrastructure.po_files import PolibPOCatalogRepository

type TranslationValue = str | dict[str, str]


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

        if progress_callback is not None:
            progress_callback(
                POProcessingProgress(
                    processed_families=0,
                    completed_entries=0,
                    total_entries=total_entries,
                    files_discovered=len(target_files),
                    entries_synchronized=0,
                    entries_translated=0,
                    message=f"Preparing {total_families} PO families for processing.",
                )
            )

        updated_files: list[POFileData] = []
        for processed_families, family_files in enumerate(grouped_files.values(), start=1):
            updated_family_files, family_synced, family_translated = _process_family(
                family_files=family_files,
                selected_locales=selected_locales,
                locale_groups=locale_groups,
                translation_memory=translation_memory,
                translation_provider=self._translation_provider,
            )
            updated_files.extend(updated_family_files)
            entries_synchronized += family_synced
            entries_translated += family_translated
            if progress_callback is not None:
                progress_callback(
                    POProcessingProgress(
                        processed_families=processed_families,
                        completed_entries=entries_synchronized + entries_translated,
                        total_entries=total_entries,
                        files_discovered=len(target_files),
                        entries_synchronized=entries_synchronized,
                        entries_translated=entries_translated,
                        message=f"Processed {processed_families} of {total_families} PO families.",
                    )
                )

        self._repository.save_po_files(tuple(updated_files))
        return POProcessingResult(
            files_discovered=len(target_files),
            families_processed=total_families,
            entries_pending=total_entries,
            entries_synchronized=entries_synchronized,
            entries_translated=entries_translated,
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
    translation_provider: POTranslationProvider | None,
) -> tuple[tuple[POFileData, ...], int, int]:
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
        family_files=family_files,
        translation_memory=translation_memory,
        translation_provider=translation_provider,
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
    return updated_files, synchronized_entries + translated_entries[0], translated_entries[1]


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
    family_files: tuple[POFileData, ...],
    translation_memory: dict[str, dict[POEntryId, TranslationValue]],
    translation_provider: POTranslationProvider | None,
) -> tuple[int, int]:
    synchronized_entries = 0
    translated_entries = 0
    locale_groups = _group_locales_by_base(selected_locales)
    nplurals_by_locale = {file_data.locale: file_data.nplurals for file_data in family_files}
    for locale in selected_locales:
        entries = family_entries.get(locale)
        if entries is None:
            continue
        for entry in entries:
            if _is_translated(entry):
                continue
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
            if translation_provider is None:
                continue
            translation = _translate_entry(
                entry=entry,
                locale=locale,
                nplurals=nplurals_by_locale.get(locale, 2),
                translation_provider=translation_provider,
            )
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
    return synchronized_entries, translated_entries


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


def _is_translated(entry: POEntryData) -> bool:
    if entry.entry_id.msgid_plural is not None:
        if entry.msgstr_plural == {}:
            return False
        return all(value.strip() != "" for value in entry.msgstr_plural.values())
    return entry.msgstr.strip() != ""
