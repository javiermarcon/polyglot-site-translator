"""Unit tests for PO processing service orchestration."""

from __future__ import annotations

from pathlib import Path

import polib
import pytest

from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingInfrastructureError,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.infrastructure.po_files import PolibPOCatalogRepository
from polyglot_site_translator.services.po_processing import POProcessingService


def test_process_site_syncs_missing_variant_entries(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(
        locale_dir / "messages-es_ES.po",
        [
            ("Hello", "Hola"),
        ],
    )
    _write_po(
        locale_dir / "messages-es_AR.po",
        [
            ("Hello", ""),
        ],
    )

    service = POProcessingService(repository=PolibPOCatalogRepository())

    result = service.process_site(_build_site(str(workspace), "es_ES"))

    synced_po = polib.pofile(str(locale_dir / "messages-es_AR.po"))
    assert result.families_processed == 1
    assert result.entries_synchronized == 1
    synced_entry = synced_po.find("Hello")
    assert synced_entry is not None
    assert synced_entry.msgstr == "Hola"


def test_process_site_handles_plural_entries_with_same_key(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    es_es = polib.POFile()
    es_es.metadata = {"Language": "es_ES", "Plural-Forms": "nplurals=2; plural=n != 1;"}
    es_es.append(
        polib.POEntry(
            msgid="file",
            msgid_plural="files",
            msgstr_plural={0: "archivo", 1: "archivos"},
        )
    )
    es_es.save(str(locale_dir / "messages-es_ES.po"))
    es_ar = polib.POFile()
    es_ar.metadata = {"Language": "es_AR", "Plural-Forms": "nplurals=2; plural=n != 1;"}
    es_ar.append(
        polib.POEntry(
            msgid="file",
            msgid_plural="files",
            msgstr_plural={0: "", 1: ""},
        )
    )
    es_ar.save(str(locale_dir / "messages-es_AR.po"))

    service = POProcessingService(repository=PolibPOCatalogRepository())

    result = service.process_site(_build_site(str(workspace), "es_ES"))

    synced_po = polib.pofile(str(locale_dir / "messages-es_AR.po"))
    plural_entry = synced_po.find("file")
    assert result.entries_synchronized == 1
    assert plural_entry is not None
    assert plural_entry.msgstr_plural[0] == "archivo"
    assert plural_entry.msgstr_plural[1] == "archivos"


def test_process_site_returns_zero_result_when_no_matching_locale_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    _write_po(workspace / "messages-en_US.po", [("Hello", "Hello")])
    service = POProcessingService(repository=PolibPOCatalogRepository())

    result = service.process_site(_build_site(str(workspace), "es_ES"))

    assert result.files_discovered == 0
    assert result.families_processed == 0
    assert result.entries_synchronized == 0


def test_process_site_raises_when_po_file_is_invalid(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    invalid_file = workspace / "messages-es_ES.po"
    invalid_file.write_bytes(b"\xff\xfe\x00\x00")
    service = POProcessingService(repository=PolibPOCatalogRepository())

    with pytest.raises(POProcessingInfrastructureError):
        service.process_site(_build_site(str(workspace), "es_ES"))


def _build_site(local_path: str, default_locale: str) -> RegisteredSite:
    return RegisteredSite(
        project=SiteProject(
            id="site-1",
            name="Site One",
            framework_type="wordpress",
            local_path=local_path,
            default_locale=default_locale,
            is_active=True,
        ),
        remote_connection=None,
    )


def _write_po(path: Path, entries: list[tuple[str, str]]) -> None:
    po_file = polib.POFile()
    po_file.metadata = {"Language": path.stem.split("-")[-1]}
    for msgid, msgstr in entries:
        po_file.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    po_file.save(str(path))
