"""Application service for shared PO processing workflows."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from polyglot_site_translator.domain.po_processing.contracts import POCatalogRepository
from polyglot_site_translator.domain.po_processing.models import (
    POEntryData,
    POEntryId,
    POFileData,
    POProcessingResult,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.infrastructure.po_files import PolibPOCatalogRepository


class POProcessingService:
    """Synchronize missing PO translations across locale variants."""

    def __init__(self, repository: POCatalogRepository | None = None) -> None:
        self._repository = repository or PolibPOCatalogRepository()

    def process_site(self, site: RegisteredSite) -> POProcessingResult:
        workspace_root = Path(site.local_path)
        discovered_files = self._repository.discover_po_files(workspace_root)
        target_files = _filter_files_by_base_language(
            discovered_files=discovered_files,
            locale=site.default_locale,
        )
        if target_files == ():
            return POProcessingResult(
                files_discovered=0,
                families_processed=0,
                entries_synchronized=0,
            )
        grouped_files = _group_files_by_family(target_files)
        updated_files: list[POFileData] = []
        entries_synchronized = 0
        for family_files in grouped_files.values():
            synchronized_family_files, synchronized_entries = _synchronize_family(family_files)
            updated_files.extend(synchronized_family_files)
            entries_synchronized += synchronized_entries
        self._repository.save_po_files(tuple(updated_files))
        return POProcessingResult(
            files_discovered=len(target_files),
            families_processed=len(grouped_files),
            entries_synchronized=entries_synchronized,
        )


def _filter_files_by_base_language(
    *,
    discovered_files: tuple[POFileData, ...],
    locale: str,
) -> tuple[POFileData, ...]:
    base_language = _base_language(locale)
    matching_files = [
        file_data
        for file_data in discovered_files
        if _base_language(file_data.locale) == base_language
    ]
    return tuple(matching_files)


def _base_language(locale: str) -> str:
    return locale.split("_", maxsplit=1)[0].lower()


def _group_files_by_family(files: tuple[POFileData, ...]) -> dict[str, tuple[POFileData, ...]]:
    grouped: dict[str, list[POFileData]] = defaultdict(list)
    for file_data in files:
        grouped[file_data.family_key].append(file_data)
    return {
        family_key: tuple(sorted(family_files, key=lambda file_data: file_data.locale))
        for family_key, family_files in grouped.items()
    }


def _synchronize_family(
    family_files: tuple[POFileData, ...],
) -> tuple[tuple[POFileData, ...], int]:
    translation_memory: dict[POEntryId, POEntryData] = {}
    for file_data in family_files:
        for entry in file_data.entries:
            if _is_translated(entry):
                translation_memory.setdefault(entry.entry_id, entry)

    synchronized_entries = 0
    synchronized_files: list[POFileData] = []
    for file_data in family_files:
        updated_entries: list[POEntryData] = []
        for entry in file_data.entries:
            if _is_translated(entry):
                updated_entries.append(entry)
                continue
            candidate = translation_memory.get(entry.entry_id)
            if candidate is None:
                updated_entries.append(entry)
                continue
            synchronized_entries += 1
            synchronized_entry = POEntryData(
                entry_id=entry.entry_id,
                msgstr=candidate.msgstr,
                msgstr_plural=dict(candidate.msgstr_plural),
            )
            updated_entries.append(synchronized_entry)
            translation_memory[entry.entry_id] = synchronized_entry
        synchronized_files.append(
            POFileData(
                source_path=file_data.source_path,
                relative_path=file_data.relative_path,
                locale=file_data.locale,
                family_key=file_data.family_key,
                entries=tuple(updated_entries),
            )
        )
    return tuple(synchronized_files), synchronized_entries


def _is_translated(entry: POEntryData) -> bool:
    if entry.entry_id.msgid_plural is not None:
        if entry.msgstr_plural == {}:
            return False
        return all(value.strip() != "" for value in entry.msgstr_plural.values())
    return entry.msgstr.strip() != ""
