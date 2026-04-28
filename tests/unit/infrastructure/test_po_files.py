"""Unit tests for PO file infrastructure helpers."""

from __future__ import annotations

from pathlib import Path

import polib
import pytest

from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingCompilationError,
    POProcessingInfrastructureError,
)
from polyglot_site_translator.domain.po_processing.models import (
    POEntryData,
    POEntryId,
    POFileData,
)
from polyglot_site_translator.infrastructure.po_files import (
    PolibPOCatalogRepository,
    _apply_entries_to_polib,
    _domain_msgstr_plural_from_polib,
    _entry_from_polib,
    _locale_from_filename,
    _nplurals_from_po,
)


def test_domain_msgstr_plural_from_polib_dict_int_keys() -> None:
    entry = polib.POEntry(
        msgid="file",
        msgid_plural="files",
        msgstr_plural={0: "archivo", 1: "archivos"},
    )
    assert _domain_msgstr_plural_from_polib(entry) == {
        "0": "archivo",
        "1": "archivos",
    }


def test_domain_msgstr_plural_from_polib_list_positions() -> None:
    entry = polib.POEntry(msgid="x")
    object.__setattr__(entry, "msgstr_plural", ["a", "b"])
    assert _domain_msgstr_plural_from_polib(entry) == {"0": "a", "1": "b"}


def test_domain_msgstr_plural_from_polib_empty_dict() -> None:
    entry = polib.POEntry(msgid="x", msgstr_plural={})
    assert _domain_msgstr_plural_from_polib(entry) == {}


def test_domain_msgstr_plural_from_polib_falsey_non_mapping_returns_empty_dict() -> None:
    entry = polib.POEntry(msgid="x")
    object.__setattr__(entry, "msgstr_plural", None)
    assert _domain_msgstr_plural_from_polib(entry) == {}


def test_domain_msgstr_plural_from_polib_rejects_unsupported_type() -> None:
    entry = polib.POEntry(msgid="odd")
    object.__setattr__(entry, "msgstr_plural", 99)
    with pytest.raises(TypeError, match="Unexpected msgstr_plural type"):
        _domain_msgstr_plural_from_polib(entry)


def test_nplurals_from_po_reads_plural_forms_metadata() -> None:
    po_file = polib.POFile()
    po_file.metadata = {"Plural-Forms": "nplurals=3; plural=n > 1;"}

    assert _nplurals_from_po(po_file) == 3


def test_nplurals_from_po_defaults_to_two_when_metadata_missing() -> None:
    po_file = polib.POFile()

    assert _nplurals_from_po(po_file) == 2


def test_catalog_repository_discovers_sorted_files_by_family_and_locale(tmp_path: Path) -> None:
    first_dir = tmp_path / "plugin_b"
    second_dir = tmp_path / "plugin_a"
    first_dir.mkdir(parents=True, exist_ok=True)
    second_dir.mkdir(parents=True, exist_ok=True)
    _write_po_file(first_dir / "messages-es_AR.po", [("Hello", "")])
    _write_po_file(first_dir / "messages-es_ES.po", [("Hello", "Hola")])
    _write_po_file(second_dir / "checkout-es_ES.po", [("Cart", "Carrito")])
    repository = PolibPOCatalogRepository()

    discovered = repository.discover_po_files(tmp_path)

    assert [file_data.relative_path for file_data in discovered] == [
        "plugin_a/checkout-es_ES.po",
        "plugin_b/messages-es_AR.po",
        "plugin_b/messages-es_ES.po",
    ]
    assert [file_data.family_key for file_data in discovered] == [
        "plugin_a/checkout",
        "plugin_b/messages",
        "plugin_b/messages",
    ]


def test_catalog_repository_wraps_workspace_scan_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = PolibPOCatalogRepository()

    def failing_rglob(self: Path, pattern: str) -> list[Path]:
        del pattern
        if self == tmp_path:
            msg = "permission denied"
            raise OSError(msg)
        return []

    monkeypatch.setattr(Path, "rglob", failing_rglob)

    with pytest.raises(POProcessingInfrastructureError, match="PO discovery failed"):
        repository.discover_po_files(tmp_path)


def test_catalog_repository_wraps_po_parse_errors_during_discovery(tmp_path: Path) -> None:
    po_path = tmp_path / "locale" / "messages-es_ES.po"
    po_path.parent.mkdir(parents=True, exist_ok=True)
    po_path.write_bytes(b"\xff\xfe\x00\x00")
    repository = PolibPOCatalogRepository()

    with pytest.raises(POProcessingInfrastructureError, match="could not be parsed"):
        repository.discover_po_files(tmp_path)


def test_catalog_repository_saves_po_files_with_updated_entries(tmp_path: Path) -> None:
    po_path = tmp_path / "locale" / "messages-es_ES.po"
    po_path.parent.mkdir(parents=True, exist_ok=True)
    _write_po_file(po_path, [("Save", "")])
    repository = PolibPOCatalogRepository()

    repository.save_po_files(
        (
            POFileData(
                source_path=str(po_path),
                relative_path="locale/messages-es_ES.po",
                locale="es_ES",
                family_key="locale/messages",
                nplurals=2,
                entries=(
                    POEntryData(
                        entry_id=POEntryId(
                            context=None,
                            msgid="Save",
                            msgid_plural=None,
                        ),
                        msgstr="Guardar",
                        msgstr_plural={},
                    ),
                ),
            ),
        )
    )

    saved = polib.pofile(str(po_path))
    saved_entry = saved.find("Save")
    assert saved_entry is not None
    assert saved_entry.msgstr == "Guardar"


def test_catalog_repository_wraps_po_load_errors_during_save(tmp_path: Path) -> None:
    po_path = tmp_path / "locale" / "messages-es_ES.po"
    po_path.parent.mkdir(parents=True, exist_ok=True)
    po_path.write_bytes(b"\xff\xfe\x00\x00")
    repository = PolibPOCatalogRepository()

    with pytest.raises(POProcessingInfrastructureError, match="could not be loaded for save"):
        repository.save_po_files((_build_po_file_data(po_path, tmp_path),))


def test_catalog_repository_wraps_po_write_errors_during_save(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    po_path = tmp_path / "locale" / "messages-es_ES.po"
    po_path.parent.mkdir(parents=True, exist_ok=True)
    _write_po_file(po_path, [("Save", "")])

    def failing_save(self: polib.POFile, path: str) -> None:
        del self, path
        msg = "read only"
        raise OSError(msg)

    monkeypatch.setattr(polib.POFile, "save", failing_save)
    repository = PolibPOCatalogRepository()

    with pytest.raises(POProcessingInfrastructureError, match="could not be saved"):
        repository.save_po_files((_build_po_file_data(po_path, tmp_path),))


def test_catalog_repository_compiles_mo_files_from_saved_po(tmp_path: Path) -> None:
    po_path = tmp_path / "locale" / "messages-es_ES.po"
    po_path.parent.mkdir(parents=True, exist_ok=True)
    po_file = polib.POFile()
    po_file.metadata = {"Language": "es_ES"}
    po_file.append(polib.POEntry(msgid="Save", msgstr="Guardar"))
    po_file.save(str(po_path))
    repository = PolibPOCatalogRepository()

    repository.compile_mo_file(_build_po_file_data(po_path, tmp_path))

    mo_path = po_path.with_suffix(".mo")
    compiled = polib.mofile(str(mo_path))
    compiled_entry = compiled.find("Save")
    assert mo_path.exists()
    assert compiled_entry is not None
    assert compiled_entry.msgstr == "Guardar"


def test_catalog_repository_raises_when_po_file_cannot_be_loaded_for_compile(
    tmp_path: Path,
) -> None:
    po_path = tmp_path / "locale" / "messages-es_ES.po"
    po_path.parent.mkdir(parents=True, exist_ok=True)
    po_path.write_bytes(b"\xff\xfe\x00\x00")
    repository = PolibPOCatalogRepository()

    with pytest.raises(POProcessingCompilationError, match="could not be loaded for compile"):
        repository.compile_mo_file(_build_po_file_data(po_path, tmp_path))


def test_catalog_repository_raises_when_mo_file_cannot_be_written(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    po_path = tmp_path / "locale" / "messages-es_ES.po"
    po_path.parent.mkdir(parents=True, exist_ok=True)
    po_file = polib.POFile()
    po_file.metadata = {"Language": "es_ES"}
    po_file.append(polib.POEntry(msgid="Save", msgstr="Guardar"))
    po_file.save(str(po_path))

    def failing_save_as_mofile(self: polib.POFile, path: str) -> None:
        del self, path
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(polib.POFile, "save_as_mofile", failing_save_as_mofile)
    repository = PolibPOCatalogRepository()

    with pytest.raises(POProcessingCompilationError, match="could not be compiled to MO"):
        repository.compile_mo_file(_build_po_file_data(po_path, tmp_path))


def test_apply_entries_to_polib_updates_only_matching_entries() -> None:
    po_file = polib.POFile()
    po_file.append(polib.POEntry(msgid="Save", msgstr=""))
    po_file.append(polib.POEntry(msgid="Ignore", msgstr="Leave"))

    _apply_entries_to_polib(
        po_file,
        (
            POEntryData(
                entry_id=POEntryId(context=None, msgid="Save", msgid_plural=None),
                msgstr="Guardar",
                msgstr_plural={},
            ),
        ),
    )

    assert _entry_from_polib(po_file[0]).msgstr == "Guardar"
    assert _entry_from_polib(po_file[1]).msgstr == "Leave"


def _build_po_file_data(path: Path, workspace_root: Path) -> POFileData:
    locale = _locale_from_filename(path)
    return POFileData(
        source_path=str(path),
        relative_path=str(path.relative_to(workspace_root)),
        locale=locale,
        family_key="messages",
        nplurals=2,
        entries=(),
    )


def _write_po_file(path: Path, entries: list[tuple[str, str]]) -> None:
    po_file = polib.POFile()
    po_file.metadata = {"Language": _locale_from_filename(path)}
    for msgid, msgstr in entries:
        po_file.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    po_file.save(str(path))
