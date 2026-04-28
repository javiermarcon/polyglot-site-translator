"""Infrastructure repository for reading/writing PO files with polib."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Any, cast

import polib

from polyglot_site_translator.domain.po_processing.contracts import POCatalogRepository
from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingCompilationError,
    POProcessingInfrastructureError,
)
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
                nplurals=_nplurals_from_po(po_file),
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

    def compile_mo_file(self, file_data: POFileData) -> None:
        path = Path(file_data.source_path)
        mo_path = path.with_suffix(".mo")
        try:
            po_file = polib.pofile(str(path))
        except (OSError, UnicodeDecodeError) as error:
            msg = f"PO file '{path}' could not be loaded for compile."
            raise POProcessingCompilationError(msg) from error
        try:
            po_file.save_as_mofile(str(mo_path))
        except OSError as error:
            msg = f"PO file '{path}' could not be compiled to MO '{mo_path}'."
            raise POProcessingCompilationError(msg) from error


def _domain_msgstr_plural_from_polib(entry: polib.POEntry) -> dict[str, str]:
    """Map polib plural translations to domain ``dict[str, str]``.

    At runtime polib stores ``msgstr_plural`` as ``dict[int, str]``. Published
    stubs for ``polib`` have disagreed on the annotated type; treating the value
    as :class:`object` and branching on ``isinstance`` keeps mypy strict without
    misrepresenting polib's real shape.
    """
    raw = cast(object, entry.msgstr_plural)
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    if isinstance(raw, list):
        return {str(index): str(text) for index, text in enumerate(raw)}
    if not raw:
        return {}
    msg = f"Unexpected msgstr_plural type (msgid={entry.msgid!r}): {type(raw).__name__}"
    raise TypeError(msg)


def _entry_from_polib(entry: polib.POEntry) -> POEntryData:
    msgid_plural = entry.msgid_plural or None
    return POEntryData(
        entry_id=POEntryId(
            context=entry.msgctxt,
            msgid=entry.msgid,
            msgid_plural=msgid_plural,
        ),
        msgstr=entry.msgstr,
        msgstr_plural=_domain_msgstr_plural_from_polib(entry),
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
        plural_for_polib = {int(key): value for key, value in updated_entry.msgstr_plural.items()}
        # Third-party stubs sometimes type ``msgstr_plural`` as ``list[str]``; polib
        # persists plural forms as ``dict[int, str]`` at runtime.
        cast(Any, item).msgstr_plural = plural_for_polib


def _locale_from_filename(path: Path) -> str:
    return path.stem.split("-")[-1]


def _build_family_key(relative_path: Path, locale: str) -> str:
    suffix = f"-{locale}"
    stem = relative_path.stem
    family_stem = stem[: -len(suffix)] if stem.endswith(suffix) else stem
    return str(relative_path.with_name(family_stem))


def _nplurals_from_po(po_file: polib.POFile) -> int:
    plural_forms = po_file.metadata.get("Plural-Forms", "")
    match = re.search(r"nplurals\s*=\s*(\d+)", plural_forms)
    if match is None:
        return 2
    return int(match.group(1))
