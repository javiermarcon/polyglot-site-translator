"""Unit tests for PO processing service orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import polib
import pytest

from polyglot_site_translator.domain.po_processing.errors import (
    POProcessingCompilationError,
    POProcessingInfrastructureError,
    POProcessingTranslationError,
)
from polyglot_site_translator.domain.po_processing.models import (
    POCompilationFailure,
    POEntryData,
    POEntryId,
    POFileData,
    POProcessingFailure,
    POProcessingProgress,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.infrastructure.po_files import PolibPOCatalogRepository
from polyglot_site_translator.services.po_processing import (
    POProcessingService,
    _FamilyProcessingRuntime,
    _find_entry,
    _group_locales_by_base,
    _is_effectively_empty_translation,
    _is_translated,
    _synchronize_family,
    _translate_missing_entries,
)


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


class PartiallyFailingCompileRepository(PolibPOCatalogRepository):
    """Repository stub that fails MO compilation for one locale and continues."""

    def __init__(self, failing_locale: str) -> None:
        super().__init__()
        self.failing_locale = failing_locale

    def compile_mo_file(self, file_data: POFileData) -> None:
        if file_data.locale == self.failing_locale:
            msg = (
                f"MO file '{file_data.source_path}' could not be compiled for locale "
                f"'{file_data.locale}'."
            )
            raise POProcessingCompilationError(msg)
        super().compile_mo_file(file_data)


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
    compiled_es_es = polib.mofile(str(locale_dir / "messages-es_ES.mo"))
    compiled_es_ar = polib.mofile(str(locale_dir / "messages-es_AR.mo"))
    assert result.families_processed == 1
    assert result.entries_synchronized == 1
    assert result.mo_files_compiled == 2
    synced_entry = synced_po.find("Hello")
    compiled_es_es_entry = compiled_es_es.find("Hello")
    compiled_es_ar_entry = compiled_es_ar.find("Hello")
    assert synced_entry is not None
    assert compiled_es_es_entry is not None
    assert compiled_es_ar_entry is not None
    assert synced_entry.msgstr == "Hola"
    assert compiled_es_es_entry.msgstr == "Hola"
    assert compiled_es_ar_entry.msgstr == "Hola"


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
    assert len(progress_events) == 3
    assert progress_events[0].total_entries == 1
    assert progress_events[1].completed_entries == 0
    assert progress_events[1].total_entries == 1
    assert progress_events[1].current_file == "locale/messages-es_ES.po"
    assert progress_events[1].current_entry == "Save"
    assert progress_events[2].completed_entries == 0


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


def test_process_site_translates_multiple_entries_in_one_file(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(
        locale_dir / "messages-es_ES.po",
        [("Save", ""), ("Title", ""), ("Price", "")],
    )
    provider = StubTranslationProvider(
        {
            ("es_ES", "Save"): "Guardar",
            ("es_ES", "Title"): "Titulo",
            ("es_ES", "Price"): "Precio",
        }
    )

    service = POProcessingService(
        repository=PolibPOCatalogRepository(),
        translation_provider=provider,
    )

    result = service.process_site(_build_site(str(workspace), "es_ES"))

    translated_po = polib.pofile(str(locale_dir / "messages-es_ES.po"))
    assert result.entries_translated == 3
    assert provider.requests == [
        ("es_ES", "Save"),
        ("es_ES", "Title"),
        ("es_ES", "Price"),
    ]
    assert cast(polib.POEntry, translated_po.find("Save")).msgstr == "Guardar"
    assert cast(polib.POEntry, translated_po.find("Title")).msgstr == "Titulo"
    assert cast(polib.POEntry, translated_po.find("Price")).msgstr == "Precio"


def test_process_site_progress_reports_current_file_and_entry(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Save", ""), ("Title", "")])
    provider = StubTranslationProvider(
        {
            ("es_ES", "Save"): "Guardar",
            ("es_ES", "Title"): "Titulo",
        }
    )
    progress_events: list[POProcessingProgress] = []

    service = POProcessingService(
        repository=PolibPOCatalogRepository(),
        translation_provider=provider,
    )

    service.process_site(
        _build_site(str(workspace), "es_ES"),
        progress_callback=progress_events.append,
    )

    assert any(
        event.current_file == "locale/messages-es_ES.po" and event.current_entry == "Save"
        for event in progress_events
    )
    assert any(
        event.current_file == "locale/messages-es_ES.po" and event.current_entry == "Title"
        for event in progress_events
    )


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
    assert result.mo_files_compiled == 0
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


def test_process_site_collects_mo_compilation_failures_and_continues(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    locale_dir = workspace / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)
    _write_po(locale_dir / "messages-es_ES.po", [("Hello", "Hola")])
    _write_po(locale_dir / "messages-es_AR.po", [("Hello", "")])
    service = POProcessingService(repository=PartiallyFailingCompileRepository("es_AR"))

    result = service.process_site(_build_site(str(workspace), "es_ES"))

    assert result.entries_synchronized == 1
    assert result.mo_files_compiled == 1
    assert result.compilation_failures == (
        POCompilationFailure(
            relative_path="locale/messages-es_AR.po",
            locale="es_AR",
            mo_path="locale/messages-es_AR.mo",
            error_message=(
                f"MO file '{locale_dir / 'messages-es_AR.po'}' could not be compiled "
                "for locale 'es_AR'."
            ),
        ),
    )
    assert (locale_dir / "messages-es_ES.mo").exists()
    assert not (locale_dir / "messages-es_AR.mo").exists()


def test_find_entry_returns_matching_entry_and_none_for_missing() -> None:
    entry = POEntryData(
        entry_id=POEntryId(context=None, msgid="Save", msgid_plural=None),
        msgstr="Guardar",
        msgstr_plural={},
    )

    assert _find_entry([entry], entry.entry_id) is entry
    assert _find_entry([entry], POEntryId(context=None, msgid="Missing", msgid_plural=None)) is None


def test_is_effectively_empty_translation_treats_blank_plural_maps_as_empty() -> None:
    assert _is_effectively_empty_translation({"0": " ", "1": ""}) is True
    assert _is_effectively_empty_translation({"0": "uno"}) is False


def test_is_translated_requires_plural_map_entries_for_plural_po_entries() -> None:
    untranslated = POEntryData(
        entry_id=POEntryId(context=None, msgid="day", msgid_plural="days"),
        msgstr="",
        msgstr_plural={},
    )
    translated = POEntryData(
        entry_id=POEntryId(context=None, msgid="day", msgid_plural="days"),
        msgstr="",
        msgstr_plural={"0": "dia", "1": "dias"},
    )

    assert _is_translated(untranslated) is False
    assert _is_translated(translated) is True


def test_synchronize_family_does_not_overwrite_existing_target_translation() -> None:
    entry_id = POEntryId(context=None, msgid="Hello", msgid_plural=None)
    source_entry = POEntryData(entry_id=entry_id, msgstr="Hola", msgstr_plural={})
    translated_target = POEntryData(entry_id=entry_id, msgstr="Che hola", msgstr_plural={})
    family_entries = {
        "es_ES": [source_entry],
        "es_AR": [translated_target],
    }

    synchronized = _synchronize_family(
        family_entries=family_entries,
        selected_locales=("es_ES", "es_AR"),
        locale_groups=_group_locales_by_base(("es_ES", "es_AR")),
        translation_memory={"es_ES": {entry_id: "Hola"}},
    )

    assert synchronized == 0
    assert translated_target.msgstr == "Che hola"


def test_translate_missing_entries_skips_selected_locales_without_a_file() -> None:
    entry = POEntryData(
        entry_id=POEntryId(context=None, msgid="Save", msgid_plural=None),
        msgstr="",
        msgstr_plural={},
    )
    family_entries = {"es_ES": [entry]}
    file_by_locale = {
        "es_ES": POFileData(
            source_path="/tmp/messages-es_ES.po",
            relative_path="locale/messages-es_ES.po",
            locale="es_ES",
            family_key="locale/messages",
            nplurals=2,
            entries=(entry,),
        )
    }

    synchronized, translated, failures = _translate_missing_entries(
        family_entries=family_entries,
        selected_locales=("es_ES", "es_AR"),
        translation_memory={},
        file_by_locale=file_by_locale,
        runtime=_FamilyProcessingRuntime(translation_provider=None),
    )

    assert synchronized == 0
    assert translated == 0
    assert failures == ()


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
