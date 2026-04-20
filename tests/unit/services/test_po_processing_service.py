"""Unit tests for PO processing service orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import polib
import pytest

from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingInfrastructureError,
    POProcessingTranslationError,
)
from polyglot_site_translator.domain.po_processing.models import (
    POProcessingFailure,
    POProcessingProgress,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.infrastructure.po_files import PolibPOCatalogRepository
from polyglot_site_translator.services.po_processing import POProcessingService


class StubTranslationProvider:
    """Deterministic translation provider for service tests."""

    def __init__(self, translations: dict[tuple[str, str], str] | None = None) -> None:
        self.translations = translations or {}
        self.requests: list[tuple[str, str]] = []

    def translate_text(self, *, text: str, target_locale: str) -> str:
        request = (target_locale, text)
        self.requests.append(request)
        return self.translations[request]


class FailingTranslationProvider:
    """Provider stub that always surfaces a translation error."""

    def translate_text(self, *, text: str, target_locale: str) -> str:
        msg = f"translation failed for {target_locale}:{text}"
        raise POProcessingTranslationError(msg)


class PartiallyFailingTranslationProvider:
    """Provider stub that fails for one text and succeeds for another."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, str]] = []

    def translate_text(self, *, text: str, target_locale: str) -> str:
        request = (target_locale, text)
        self.requests.append(request)
        if text == "Broken":
            msg = f"translation failed for {target_locale}:{text}"
            raise POProcessingTranslationError(msg)
        return "Guardar"


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


def test_process_site_reports_progress_by_family(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Hello", "Hola")])
    _write_po(locale_dir / "messages-es_AR.po", [("Hello", "")])
    progress_events: list[POProcessingProgress] = []

    service = POProcessingService(repository=PolibPOCatalogRepository())

    result = service.process_site(
        _build_site(str(workspace), "es_ES"),
        progress_callback=progress_events.append,
    )

    assert result.families_processed == 1
    assert len(progress_events) == 2
    assert progress_events[0].processed_families == 0
    assert progress_events[0].completed_entries == 0
    assert progress_events[0].total_entries == 1
    assert progress_events[1].processed_families == 1
    assert progress_events[1].completed_entries == 1
    assert progress_events[1].total_entries == 1
    assert progress_events[1].entries_synchronized == 1
    assert progress_events[1].entries_translated == 0


def test_process_site_reports_entry_progress_for_partial_completion(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Save", "")])
    progress_events: list[POProcessingProgress] = []

    service = POProcessingService(repository=PolibPOCatalogRepository())

    result = service.process_site(
        _build_site(str(workspace), "es_ES"),
        progress_callback=progress_events.append,
    )

    assert result.entries_synchronized == 0
    assert result.entries_translated == 0
    assert len(progress_events) == 2
    assert progress_events[0].total_entries == 1
    assert progress_events[1].completed_entries == 0
    assert progress_events[1].total_entries == 1


def test_process_site_skips_hashtag_like_tokens_for_external_translation(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("#tag1", ""), ("Save", "")])
    provider = StubTranslationProvider({("es_ES", "Save"): "Guardar"})

    service = POProcessingService(
        repository=PolibPOCatalogRepository(),
        translation_provider=provider,
    )

    result = service.process_site(_build_site(str(workspace), "es_ES"))

    translated_po = polib.pofile(str(locale_dir / "messages-es_ES.po"))
    assert result.entries_translated == 1
    assert result.entries_failed == 0
    assert provider.requests == [("es_ES", "Save")]
    assert cast(polib.POEntry, translated_po.find("#tag1")).msgstr == ""
    assert cast(polib.POEntry, translated_po.find("Save")).msgstr == "Guardar"


def test_process_site_collects_translation_failures_and_continues(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Broken", ""), ("Save", "")])
    provider = PartiallyFailingTranslationProvider()

    service = POProcessingService(
        repository=PolibPOCatalogRepository(),
        translation_provider=provider,
    )

    result = service.process_site(_build_site(str(workspace), "es_ES"))

    translated_po = polib.pofile(str(locale_dir / "messages-es_ES.po"))
    assert result.entries_translated == 1
    assert result.entries_failed == 1
    assert result.failures == (
        POProcessingFailure(
            relative_path="locale/messages-es_ES.po",
            locale="es_ES",
            msgid="Broken",
            error_message="translation failed for es_ES:Broken",
        ),
    )
    assert cast(polib.POEntry, translated_po.find("Broken")).msgstr == ""
    assert cast(polib.POEntry, translated_po.find("Save")).msgstr == "Guardar"


def test_process_site_accepts_multiple_configured_default_locales(tmp_path: Path) -> None:
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
    _write_po(
        locale_dir / "messages-pt_BR.po",
        [
            ("Hello", "Ola"),
        ],
    )

    service = POProcessingService(repository=PolibPOCatalogRepository())

    result = service.process_site(_build_site(str(workspace), "pt_BR, es_ES, es_AR"))

    synced_po = polib.pofile(str(locale_dir / "messages-es_AR.po"))
    assert result.families_processed == 1
    assert result.entries_synchronized == 1
    synced_entry = synced_po.find("Hello")
    assert synced_entry is not None
    assert synced_entry.msgstr == "Hola"


def test_process_site_returns_zero_result_when_no_matching_locale_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    _write_po(workspace / "messages-en_US.po", [("Hello", "Hello")])
    service = POProcessingService(repository=PolibPOCatalogRepository())

    result = service.process_site(_build_site(str(workspace), "es_ES"))

    assert result.files_discovered == 0
    assert result.families_processed == 0
    assert result.entries_synchronized == 0
    assert result.entries_translated == 0


def test_process_site_raises_when_po_file_is_invalid(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    invalid_file = workspace / "messages-es_ES.po"
    invalid_file.write_bytes(b"\xff\xfe\x00\x00")
    service = POProcessingService(repository=PolibPOCatalogRepository())

    with pytest.raises(POProcessingInfrastructureError):
        service.process_site(_build_site(str(workspace), "es_ES"))


def test_process_site_reuses_translation_memory_across_families(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    first_dir = workspace / "plugin_a"
    second_dir = workspace / "plugin_b"
    first_dir.mkdir(parents=True, exist_ok=True)
    second_dir.mkdir(parents=True, exist_ok=True)
    _write_po(first_dir / "messages-es_ES.po", [("Hello", "Hola")])
    _write_po(first_dir / "messages-es_AR.po", [("Hello", "")])
    _write_po(second_dir / "checkout-es_ES.po", [("Hello", "")])
    _write_po(second_dir / "checkout-es_AR.po", [("Hello", "")])

    service = POProcessingService(repository=PolibPOCatalogRepository())

    result = service.process_site(_build_site(str(workspace), "es_ES,es_AR"))

    synced_po = polib.pofile(str(second_dir / "checkout-es_AR.po"))
    synced_entry = synced_po.find("Hello")
    assert result.families_processed == 2
    assert result.entries_synchronized == 3
    assert result.entries_translated == 0
    assert synced_entry is not None
    assert synced_entry.msgstr == "Hola"


def test_process_site_translates_missing_entries_with_external_provider(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Save", "")])
    _write_po(locale_dir / "messages-es_AR.po", [("Save", "")])
    provider = StubTranslationProvider({("es_ES", "Save"): "Guardar"})

    service = POProcessingService(
        repository=PolibPOCatalogRepository(),
        translation_provider=provider,
    )

    result = service.process_site(_build_site(str(workspace), "es_ES,es_AR"))

    es_es_po = polib.pofile(str(locale_dir / "messages-es_ES.po"))
    es_ar_po = polib.pofile(str(locale_dir / "messages-es_AR.po"))
    assert result.entries_synchronized == 1
    assert result.entries_translated == 1
    assert provider.requests == [("es_ES", "Save")]
    assert cast(polib.POEntry, es_es_po.find("Save")).msgstr == "Guardar"
    assert cast(polib.POEntry, es_ar_po.find("Save")).msgstr == "Guardar"


def test_process_site_translates_plural_entries_with_external_provider(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    es_es = polib.POFile()
    es_es.metadata = {"Language": "es_ES", "Plural-Forms": "nplurals=3; plural=n > 1;"}
    es_es.append(
        polib.POEntry(
            msgid="day",
            msgid_plural="days",
            msgstr_plural={0: "", 1: "", 2: ""},
        )
    )
    es_es.save(str(locale_dir / "messages-es_ES.po"))
    provider = StubTranslationProvider(
        {
            ("es_ES", "day"): "dia",
            ("es_ES", "days"): "dias",
        }
    )

    service = POProcessingService(
        repository=PolibPOCatalogRepository(),
        translation_provider=provider,
    )

    result = service.process_site(_build_site(str(workspace), "es_ES"))

    translated_po = polib.pofile(str(locale_dir / "messages-es_ES.po"))
    translated_entry = translated_po.find("day")
    assert result.entries_synchronized == 0
    assert result.entries_translated == 1
    assert translated_entry is not None
    assert translated_entry.msgstr_plural[0] == "dia"
    assert translated_entry.msgstr_plural[1] == "dias"
    assert translated_entry.msgstr_plural[2] == "dias"


def test_process_site_filters_by_exact_selected_locales(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Hello", "Hola")])
    _write_po(locale_dir / "messages-es_AR.po", [("Hello", "")])
    _write_po(locale_dir / "messages-es_MX.po", [("Hello", "")])

    service = POProcessingService(repository=PolibPOCatalogRepository())

    result = service.process_site(_build_site(str(workspace), "es_ES,es_AR"))

    es_ar_po = polib.pofile(str(locale_dir / "messages-es_AR.po"))
    es_mx_po = polib.pofile(str(locale_dir / "messages-es_MX.po"))
    assert result.files_discovered == 2
    assert result.entries_synchronized == 1
    assert cast(polib.POEntry, es_ar_po.find("Hello")).msgstr == "Hola"
    assert cast(polib.POEntry, es_mx_po.find("Hello")).msgstr == ""


def test_process_site_raises_when_every_external_translation_fails_and_no_file_can_continue(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Save", "")])
    service = POProcessingService(
        repository=PolibPOCatalogRepository(),
        translation_provider=FailingTranslationProvider(),
    )

    result = service.process_site(_build_site(str(workspace), "es_ES"))

    assert result.entries_translated == 0
    assert result.entries_failed == 1
    assert result.failures[0].relative_path == "locale/messages-es_ES.po"


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
