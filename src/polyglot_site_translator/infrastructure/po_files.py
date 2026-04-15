"""Infrastructure repository for reading/writing PO files with polib."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import polib

from polyglot_site_translator.domain.po_processing.contracts import POCatalogRepository
from polyglot_site_translator.domain.po_processing.errors import POProcessingInfrastructureError
from polyglot_site_translator.domain.po_processing.models import (
    POEntryData,
    POEntryId,
    POFileData,
)


class PolibPOCatalogRepository(POCatalogRepository):
    """Load and persist PO files using `polib`."""

    def discover_po_files(self, workspace_root: Path) -> tuple[POFileData, ...]:
        files: list[POFileData] = []
        by_family: dict[str, list[POFileData]] = defaultdict(list)
        try:
            discovered_paths = sorted(workspace_root.rglob("*.po"))
        except OSError as error:
            msg = f"PO discovery failed for workspace '{workspace_root}'."
            raise POProcessingInfrastructureError(msg) from error
        for path in discovered_paths:
            locale = _locale_from_filename(path)
            relative_path = path.relative_to(workspace_root)
            family_key = _build_family_key(relative_path, locale)
            try:
                po_file = polib.pofile(str(path))
            except (OSError, UnicodeDecodeError) as error:
                msg = f"PO file '{path}' could not be parsed."
                raise POProcessingInfrastructureError(msg) from error
            file_data = POFileData(
                source_path=str(path),
                relative_path=str(relative_path),
                locale=locale,
                family_key=family_key,
                entries=tuple(_entry_from_polib(item) for item in po_file),
            )
            by_family[family_key].append(file_data)
        for family in sorted(by_family):
            files.extend(sorted(by_family[family], key=lambda item: item.locale))
        return tuple(files)

    def save_po_files(self, files: tuple[POFileData, ...]) -> None:
        for file_data in files:
            path = Path(file_data.source_path)
            try:
                po_file = polib.pofile(str(path))
            except (OSError, UnicodeDecodeError) as error:
                msg = f"PO file '{path}' could not be loaded for save."
                raise POProcessingInfrastructureError(msg) from error
            _apply_entries_to_polib(po_file, file_data.entries)
            try:
                po_file.save(str(path))
            except OSError as error:
                msg = f"PO file '{path}' could not be saved."
                raise POProcessingInfrastructureError(msg) from error


def _entry_from_polib(entry: polib.POEntry) -> POEntryData:
    msgid_plural = entry.msgid_plural or None
    return POEntryData(
        entry_id=POEntryId(
            context=entry.msgctxt,
            msgid=entry.msgid,
            msgid_plural=msgid_plural,
        ),
        msgstr=entry.msgstr,
        msgstr_plural={str(key): value for key, value in entry.msgstr_plural.items()},
    )


def _apply_entries_to_polib(po_file: polib.POFile, entries: tuple[POEntryData, ...]) -> None:
    updated_entries: dict[POEntryId, POEntryData] = {entry.entry_id: entry for entry in entries}
    for item in po_file:
        entry_id = POEntryId(
            context=item.msgctxt,
            msgid=item.msgid,
            msgid_plural=item.msgid_plural or None,
        )
        updated_entry = updated_entries.get(entry_id)
        if updated_entry is None:
            continue
        item.msgstr = updated_entry.msgstr
        item.msgstr_plural = {int(key): value for key, value in updated_entry.msgstr_plural.items()}


def _locale_from_filename(path: Path) -> str:
    return path.stem.split("-")[-1]


def _build_family_key(relative_path: Path, locale: str) -> str:
    suffix = f"-{locale}"
    stem = relative_path.stem
    family_stem = stem[: -len(suffix)] if stem.endswith(suffix) else stem
    return str(relative_path.with_name(family_stem))
