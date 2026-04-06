#!/bin/fades

"""Traducir y sincronizar archivos .po entre variantes de un mismo idioma.

Características principales:
- Detecta automáticamente familias de archivos .po del mismo plugin/theme.
- Sincroniza primero las traducciones existentes entre variantes del mismo idioma.
- Reutiliza traducciones ya presentes para evitar requests innecesarios.
- Soporta msgctxt y plurales.
- Traduce usando el idioma base (por ejemplo, ``es`` para ``es_ES`` y ``es_AR``).
- Guarda el resultado manteniendo la estructura de directorios original.
- Soporta caché persistente en disco mediante ``shelve``.
- Permite modo ``--sync-only`` para no llamar al traductor externo.
- Permite compilar ``.mo`` junto a los ``.po`` procesados con ``--compile-mo``.
- Permite ``--dry-run`` para no escribir archivos.
- Permite ``--stats-only`` para mostrar estadísticas sin modificar archivos.
- Ignora por defecto las diferencias regionales ya traducidas.
- Permite reportar diferencias entre variantes con ``--report-inconsistencies``.

Ejemplos:
    fades traducir.py --locales es_ES,es_AR --origen public_html --destino public_html_traducido
    fades traducir.py --locales es_ES,es_AR --sync-only
    fades traducir.py --locales es_ES,es_AR --compile-mo
    fades traducir.py --locales es_ES,es_AR --stats-only
    fades traducir.py --locales es_ES,es_AR --dry-run
    fades traducir.py --locales es_ES,es_AR --report-inconsistencies
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import re
import shelve
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TypeAlias

import polib  # fades
from googletrans import Translator  # fades
from googletrans.models import Translated  # fades

EntryKey: TypeAlias = tuple[str | None, str, str | None]
PluralMap: TypeAlias = dict[str, str]
TranslationValue: TypeAlias = str | PluralMap


@dataclass(slots=True)
class POFileContext:
    """Contexto de trabajo de un archivo .po."""

    source_path: pathlib.Path
    relative_path: pathlib.Path
    locale: str
    family_key: str
    po: polib.POFile


@dataclass(slots=True)
class ProcessStats:
    """Estadísticas del procesamiento."""

    files_found: int = 0
    families_found: int = 0
    entries_total: int = 0
    entries_missing: int = 0
    entries_fuzzy: int = 0
    entries_completed_from_sync: int = 0
    entries_reused_from_other_variant: int = 0
    entries_translated_from_cache: int = 0
    entries_translated_from_api: int = 0
    entries_skipped_sync_only: int = 0
    variant_differences_found: int = 0
    files_written: int = 0
    mo_compiled: int = 0
    families_processed: int = 0
    variant_difference_details: list[str] = field(default_factory=list)


class TranslationCache:
    """Caché persistente de traducciones basado en ``shelve``."""

    def __init__(self, cache_path: pathlib.Path, enabled: bool = True) -> None:
        self.cache_path = cache_path
        self.enabled = enabled
        self._db: shelve.Shelf[str, str] | None = None

    def open(self) -> None:
        """Abre la caché persistente."""
        if not self.enabled:
            return

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = shelve.open(str(self.cache_path), writeback=False)

    def close(self) -> None:
        """Cierra la caché persistente."""
        if self._db is None:
            return

        self._db.close()
        self._db = None

    @staticmethod
    def _build_key(base_lang: str, text: str) -> str:
        """Construye la clave interna de caché."""
        return f"{base_lang}\x1f{text}"

    def get(self, base_lang: str, text: str) -> str | None:
        """Obtiene una traducción cacheada."""
        if not self.enabled or self._db is None:
            return None

        key = self._build_key(base_lang, text)
        value = self._db.get(key)
        if value is None:
            return None
        return str(value)

    def set(self, base_lang: str, text: str, translated_text: str) -> None:
        """Guarda una traducción cacheada."""
        if not self.enabled or self._db is None:
            return

        key = self._build_key(base_lang, text)
        self._db[key] = translated_text


class POTranslationProcessor:
    """Procesa archivos .po reutilizando traducciones entre variantes."""

    def __init__(
        self,
        locales: list[str],
        origen: str,
        destino: str,
        solo_fuzzy: bool = False,
        resume: bool = False,
        sync_only: bool = False,
        compile_mo: bool = False,
        cache_path: str = ".po_translation_cache",
        disable_cache: bool = False,
        stats_only: bool = False,
        dry_run: bool = False,
        report_inconsistencies: bool = False,
    ) -> None:
        self.locales = [locale.strip() for locale in locales if locale.strip()]
        self.origen = pathlib.Path(origen).resolve()
        self.destino = pathlib.Path(destino).resolve()
        self.solo_fuzzy = solo_fuzzy
        self.resume = resume
        self.sync_only = sync_only
        self.compile_mo = compile_mo
        self.stats_only = stats_only
        self.dry_run = dry_run
        self.report_inconsistencies = report_inconsistencies

        self.translator = Translator()
        self.cache = TranslationCache(
            cache_path=pathlib.Path(cache_path).resolve(),
            enabled=not disable_cache,
        )
        self.stats = ProcessStats()

        self.destino.mkdir(parents=True, exist_ok=True)

        self.file_contexts = self._discover_po_files()
        self.locale_groups = self._group_locales_by_base()
        self.family_groups = self._group_files_by_family()
        self.translation_memory: dict[str, dict[EntryKey, TranslationValue]] = {}
        self._rebuild_translation_memory()
        self._populate_initial_stats()

    def _discover_po_files(self) -> list[POFileContext]:
        """Encuentra y carga los .po que coinciden con los locales solicitados."""
        contexts: list[POFileContext] = []

        for path in sorted(self.origen.rglob("*.po")):
            locale = self._locale_from_filename(path)
            if locale not in self.locales:
                continue

            relative_path = path.relative_to(self.origen)
            contexts.append(
                POFileContext(
                    source_path=path,
                    relative_path=relative_path,
                    locale=locale,
                    family_key=self._build_family_key(relative_path, locale),
                    po=polib.pofile(str(path)),
                ),
            )

        return contexts

    @staticmethod
    def _locale_from_filename(path: pathlib.Path) -> str:
        """Obtiene el locale a partir del nombre del archivo."""
        return path.stem.split("-")[-1]

    @staticmethod
    def _base_lang(locale: str) -> str:
        """Obtiene el idioma base de un locale."""
        return locale.split("_")[0].lower()

    def _group_locales_by_base(self) -> dict[str, list[str]]:
        """Agrupa locales por idioma base respetando el orden de entrada."""
        groups: dict[str, list[str]] = defaultdict(list)
        for locale in self.locales:
            groups[self._base_lang(locale)].append(locale)
        return dict(groups)

    def _group_files_by_family(self) -> dict[str, list[POFileContext]]:
        """Agrupa archivos por familia (theme/plugin + ruta relativa)."""
        groups: dict[str, list[POFileContext]] = defaultdict(list)
        for context in self.file_contexts:
            groups[context.family_key].append(context)

        for contexts in groups.values():
            contexts.sort(key=lambda item: self.locales.index(item.locale))

        return dict(groups)

    @staticmethod
    def _build_family_key(relative_path: pathlib.Path, locale: str) -> str:
        """Construye una clave de familia removiendo el sufijo del locale."""
        stem = relative_path.stem
        suffix = f"-{locale}"
        family_stem = stem[:-len(suffix)] if stem.endswith(suffix) else stem
        return str(relative_path.with_name(family_stem))

    @staticmethod
    def _entry_key(entry: polib.POEntry) -> EntryKey:
        """Clave real gettext teniendo en cuenta contexto y plural."""
        return entry.msgctxt, entry.msgid, entry.msgid_plural

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Corrige placeholders y llaves para evitar roturas frecuentes."""
        sanitized = text.replace("{", "{{").replace("}", "}}")
        return re.sub(r"%\s*(\d+)\s*\$\s*(\w)", r"%\1$\2", sanitized)

    @staticmethod
    def _normalize_plural_map(msgstr_plural: dict[int | str, str]) -> PluralMap:
        """Normaliza las claves del plural a string para comparar y persistir."""
        normalized: PluralMap = {}
        for key, value in msgstr_plural.items():
            clean_value = str(value).strip()
            if not clean_value:
                continue
            normalized[str(key)] = str(value)
        return normalized

    @staticmethod
    def _is_translated(entry: polib.POEntry) -> bool:
        """Indica si la entrada tiene traducción completa."""
        if entry.msgid_plural:
            if not entry.msgstr_plural:
                return False
            normalized = POTranslationProcessor._normalize_plural_map(entry.msgstr_plural)
            return bool(normalized) and all(value.strip() for value in normalized.values())

        return bool(entry.msgstr.strip())

    @staticmethod
    def _is_effectively_empty_translation(translation: TranslationValue | None) -> bool:
        """Indica si una traducción candidata está vacía."""
        if translation is None:
            return True

        if isinstance(translation, dict):
            return not any(value.strip() for value in translation.values())

        return not translation.strip()

    def _translation_from_entry(self, entry: polib.POEntry) -> TranslationValue:
        """Devuelve la traducción normalizada de una entrada."""
        if entry.msgid_plural:
            return self._normalize_plural_map(entry.msgstr_plural)
        return entry.msgstr

    def _rebuild_translation_memory(self) -> None:
        """Reconstruye la memoria de traducciones cargadas en memoria."""
        self.translation_memory = defaultdict(dict)
        for context in self.file_contexts:
            for entry in context.po:
                if not self._is_translated(entry):
                    continue
                self.translation_memory[context.locale][self._entry_key(entry)] = self._translation_from_entry(entry)

    def _populate_initial_stats(self) -> None:
        """Carga estadísticas iniciales a partir de los archivos encontrados."""
        self.stats.files_found = len(self.file_contexts)
        self.stats.families_found = len(self.family_groups)

        for context in self.file_contexts:
            for entry in context.po:
                self.stats.entries_total += 1
                if entry.fuzzy:
                    self.stats.entries_fuzzy += 1
                if not self._is_translated(entry):
                    self.stats.entries_missing += 1

    def _iter_all_entries(
        self,
        contexts: list[POFileContext],
    ) -> dict[EntryKey, dict[str, polib.POEntry]]:
        """Indexa las entradas de una familia por locale."""
        entry_map: dict[EntryKey, dict[str, polib.POEntry]] = defaultdict(dict)
        for context in contexts:
            for entry in context.po:
                entry_map[self._entry_key(entry)][context.locale] = entry
        return dict(entry_map)

    def _related_locales(self, locale: str) -> list[str]:
        """Devuelve otras variantes del mismo idioma base."""
        base_lang = self._base_lang(locale)
        return [candidate for candidate in self.locale_groups.get(base_lang, []) if candidate != locale]

    def _copy_translation(self, source_entry: polib.POEntry, target_entry: polib.POEntry) -> None:
        """Copia la traducción de una entrada a otra respetando singular/plural."""
        if source_entry.msgid_plural:
            target_entry.msgstr_plural = self._normalize_plural_map(source_entry.msgstr_plural)
            target_entry.msgstr = ""
            return

        target_entry.msgstr = source_entry.msgstr

    def _sync_family_translations(self, family_contexts: list[POFileContext]) -> int:
        """Sincroniza traducciones ya existentes entre variantes de la misma familia.

        Solo completa faltantes. Nunca pisa traducciones ya existentes, aunque
        difieran entre variantes regionales.
        """
        entry_map = self._iter_all_entries(family_contexts)
        changes = 0

        for entry_key, entries_by_locale in entry_map.items():
            for locale in self.locales:
                source_entry = entries_by_locale.get(locale)
                if source_entry is None or not self._is_translated(source_entry):
                    continue

                for related_locale in self._related_locales(locale):
                    target_entry = entries_by_locale.get(related_locale)
                    if target_entry is None or self._is_translated(target_entry):
                        continue

                    self._copy_translation(source_entry, target_entry)
                    self.translation_memory.setdefault(related_locale, {})[entry_key] = self._translation_from_entry(target_entry)
                    changes += 1
                break

        return changes

    def _candidate_translation_from_memory(
        self,
        locale: str,
        entry_key: EntryKey,
    ) -> TranslationValue | None:
        """Busca una traducción existente en otras variantes del mismo idioma."""
        for related_locale in self._related_locales(locale):
            candidate = self.translation_memory.get(related_locale, {}).get(entry_key)
            if self._is_effectively_empty_translation(candidate):
                continue
            return candidate

        return None

    async def _translate_text(self, text: str, locale: str) -> tuple[str, str]:
        """Traduce un texto usando idioma base y caché persistente.

        Retorna ``(texto_traducido, fuente)`` donde fuente es ``cache`` o ``api``.
        """
        base_lang = self._base_lang(locale)
        cached = self.cache.get(base_lang, text)
        if cached is not None:
            return cached, "cache"

        translated: Translated = await self.translator.translate(
            self._sanitize_text(text).replace(".", ". "),
            dest=base_lang,
        )
        sanitized_translated = self._sanitize_text(translated.text)
        self.cache.set(base_lang, text, sanitized_translated)
        return sanitized_translated, "api"

    async def _translate_entry(
        self,
        entry: polib.POEntry,
        locale: str,
        nplurals: int,
    ) -> tuple[TranslationValue, str]:
        """Traduce una entrada singular o plural."""
        if entry.msgid_plural:
            singular, singular_source = await self._translate_text(entry.msgid, locale)
            plural, plural_source = await self._translate_text(entry.msgid_plural, locale)
            translated_plural: PluralMap = {"0": singular}
            for index in range(1, nplurals):
                translated_plural[str(index)] = plural

            source = "cache" if singular_source == "cache" and plural_source == "cache" else "api"
            return translated_plural, source

        translated_text, source = await self._translate_text(entry.msgid, locale)
        return translated_text, source

    def _entries_to_process(self, po: polib.POFile) -> list[polib.POEntry]:
        """Obtiene las entradas que deben procesarse."""
        if self.solo_fuzzy:
            return list(po.fuzzy_entries())

        entry_map: dict[EntryKey, polib.POEntry] = {}
        for entry in po.fuzzy_entries() + po.untranslated_entries():
            entry_map[self._entry_key(entry)] = entry
        return list(entry_map.values())

    def _propagate_translation_to_family(
        self,
        family_contexts: list[POFileContext],
        source_locale: str,
        entry_key: EntryKey,
        translation: TranslationValue,
    ) -> None:
        """Propaga una traducción a las variantes faltantes de la misma familia."""
        translation_base = self._base_lang(source_locale)
        normalized_plural: PluralMap | None = None
        if isinstance(translation, dict):
            normalized_plural = self._normalize_plural_map(translation)

        for context in family_contexts:
            if self._base_lang(context.locale) != translation_base:
                continue

            target_entry = context.po.find(entry_key[1], msgctxt=entry_key[0])
            if target_entry is None:
                continue

            if target_entry.msgid_plural != entry_key[2]:
                continue

            if self._is_translated(target_entry):
                continue

            if normalized_plural is not None:
                target_entry.msgstr_plural = dict(normalized_plural)
                target_entry.msgstr = ""
                self.translation_memory.setdefault(context.locale, {})[entry_key] = dict(normalized_plural)
                continue

            target_entry.msgstr = translation
            self.translation_memory.setdefault(context.locale, {})[entry_key] = translation

    def _nplurals_for_po(self, po: polib.POFile) -> int:
        """Extrae la cantidad de plurales desde ``Plural-Forms``."""
        plural_forms = po.metadata.get("Plural-Forms", "")
        match = re.search(r"nplurals\s*=\s*(\d+)", plural_forms)
        if match is None:
            return 2
        return int(match.group(1))

    async def _translate_missing_entries_in_family(
        self,
        family_contexts: list[POFileContext],
    ) -> None:
        """Completa entradas faltantes desde memoria, caché o traductor."""
        for context in family_contexts:
            nplurals = self._nplurals_for_po(context.po)
            for entry in self._entries_to_process(context.po):
                if self._is_translated(entry):
                    continue

                entry_key = self._entry_key(entry)
                candidate = self._candidate_translation_from_memory(context.locale, entry_key)
                if candidate is not None:
                    if isinstance(candidate, dict):
                        entry.msgstr_plural = dict(candidate)
                        entry.msgstr = ""
                    else:
                        entry.msgstr = candidate

                    self.translation_memory.setdefault(context.locale, {})[entry_key] = candidate
                    self._propagate_translation_to_family(
                        family_contexts=family_contexts,
                        source_locale=context.locale,
                        entry_key=entry_key,
                        translation=candidate,
                    )
                    self.stats.entries_reused_from_other_variant += 1
                    continue

                if self.sync_only:
                    self.stats.entries_skipped_sync_only += 1
                    continue

                translation, translation_source = await self._translate_entry(entry, context.locale, nplurals)
                if isinstance(translation, dict):
                    entry.msgstr_plural = dict(translation)
                    entry.msgstr = ""
                else:
                    entry.msgstr = translation

                self.translation_memory.setdefault(context.locale, {})[entry_key] = translation
                self._propagate_translation_to_family(
                    family_contexts=family_contexts,
                    source_locale=context.locale,
                    entry_key=entry_key,
                    translation=translation,
                )
                if translation_source == "cache":
                    self.stats.entries_translated_from_cache += 1
                else:
                    self.stats.entries_translated_from_api += 1

    def _destination_path(self, relative_path: pathlib.Path) -> pathlib.Path:
        """Obtiene la ruta de destino preservando la estructura del origen."""
        return self.destino / relative_path

    def _save_context(self, context: POFileContext) -> None:
        """Guarda el .po y opcionalmente su .mo asociado en la estructura destino."""
        destination_path = self._destination_path(context.relative_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        context.po.save(str(destination_path))
        self.stats.files_written += 1
        if self.compile_mo:
            context.po.save_as_mofile(str(destination_path.with_suffix(".mo")))
            self.stats.mo_compiled += 1

    def _detect_variant_differences(self, family_key: str, family_contexts: list[POFileContext]) -> None:
        """Reporta diferencias entre variantes solo si se solicita explícitamente."""
        if not self.report_inconsistencies:
            return

        entry_map = self._iter_all_entries(family_contexts)
        for entry_key, entries_by_locale in entry_map.items():
            translated_values: dict[str, TranslationValue] = {}
            for locale, entry in entries_by_locale.items():
                if not self._is_translated(entry):
                    continue
                translated_values[locale] = self._translation_from_entry(entry)

            if len(translated_values) < 2:
                continue

            canonical_values = {
                locale: self._canonical_translation_value(value)
                for locale, value in translated_values.items()
            }
            unique_values = set(canonical_values.values())
            if len(unique_values) <= 1:
                continue

            context_label = entry_key[0] if entry_key[0] is not None else "<sin contexto>"
            detail = (
                "Diferencia entre variantes: "
                f"{family_key} | msgctxt='{context_label}' | msgid='{entry_key[1]}' | "
                f"locales={', '.join(sorted(translated_values))}"
            )
            self.stats.variant_differences_found += 1
            self.stats.variant_difference_details.append(detail)

    @staticmethod
    def _canonical_translation_value(value: TranslationValue) -> str:
        """Serializa una traducción para comparaciones consistentes."""
        if isinstance(value, dict):
            parts = [f"{key}={value[key]}" for key in sorted(value)]
            return "\x1f".join(parts)
        return value

    def _print_stats(self) -> None:
        """Imprime un resumen de estadísticas."""
        print("📊 Estadísticas")
        print(f"  - Archivos encontrados: {self.stats.files_found}")
        print(f"  - Familias encontradas: {self.stats.families_found}")
        print(f"  - Familias procesadas: {self.stats.families_processed}")
        print(f"  - Entradas totales: {self.stats.entries_total}")
        print(f"  - Entradas faltantes: {self.stats.entries_missing}")
        print(f"  - Entradas fuzzy: {self.stats.entries_fuzzy}")
        print(f"  - Completadas por sincronización inicial: {self.stats.entries_completed_from_sync}")
        print(
            "  - Reutilizadas desde otra variante: "
            f"{self.stats.entries_reused_from_other_variant}",
        )
        print(f"  - Traducidas desde caché: {self.stats.entries_translated_from_cache}")
        print(f"  - Traducidas vía API: {self.stats.entries_translated_from_api}")
        print(f"  - Omitidas por --sync-only: {self.stats.entries_skipped_sync_only}")
        print(f"  - Archivos escritos: {self.stats.files_written}")
        print(f"  - .mo compilados: {self.stats.mo_compiled}")
        if self.report_inconsistencies:
            print(
                "  - Diferencias entre variantes reportadas: "
                f"{self.stats.variant_differences_found}",
            )
            for detail in self.stats.variant_difference_details:
                print(f"    * {detail}")

    async def run(self) -> None:
        """Ejecuta el proceso completo."""
        if not self.file_contexts:
            print("⚠️ No se encontraron archivos .po para los locales indicados.")
            return

        self.cache.open()
        try:
            for family_key, family_contexts in self.family_groups.items():
                self.stats.families_processed += 1
                print(f"📁 Procesando familia: {family_key}")
                synced = self._sync_family_translations(family_contexts)
                self.stats.entries_completed_from_sync += synced
                await self._translate_missing_entries_in_family(family_contexts)
                self._detect_variant_differences(family_key, family_contexts)

                if self.stats_only:
                    continue

                if self.dry_run:
                    for context in family_contexts:
                        print(f"🧪 Dry-run: no se escribe {context.relative_path}")
                    continue

                for context in family_contexts:
                    destination_path = self._destination_path(context.relative_path)
                    if self.resume and destination_path.exists():
                        print(
                            "🔄 Omitiendo guardado de "
                            f"{context.relative_path}, ya existe en destino.",
                        )
                        continue
                    self._save_context(context)
                    print(f"💾 Guardado: {context.relative_path}")

            self._print_stats()
        finally:
            self.cache.close()


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Traducir y sincronizar archivos .po entre variantes del mismo idioma, "
            "preservando la estructura de directorios."
        ),
    )
    parser.add_argument(
        "--locales",
        required=True,
        help="Locales separados por coma. Ejemplo: es_ES,es_AR",
    )
    parser.add_argument(
        "--origen",
        default="public_html",
        help="Directorio raíz de origen desde donde buscar archivos .po.",
    )
    parser.add_argument(
        "--destino",
        default="public_html_traducido",
        help="Directorio raíz de salida donde guardar la misma estructura.",
    )
    parser.add_argument(
        "--solo-fuzzy",
        action="store_true",
        help="Procesar solo entradas fuzzy.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="No sobrescribir archivos ya existentes en destino.",
    )
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Solo completar faltantes desde otras variantes, sin traducir externamente.",
    )
    parser.add_argument(
        "--compile-mo",
        action="store_true",
        help="Compilar también archivos .mo junto a cada .po generado.",
    )
    parser.add_argument(
        "--cache-path",
        default=".po_translation_cache",
        help="Ruta base para la caché persistente de traducciones.",
    )
    parser.add_argument(
        "--disable-cache",
        action="store_true",
        help="Deshabilitar la caché persistente.",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Mostrar estadísticas sin escribir archivos.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular el procesamiento sin escribir archivos.",
    )
    parser.add_argument(
        "--report-inconsistencies",
        action="store_true",
        help=(
            "Reportar diferencias entre variantes ya traducidas. "
            "Por defecto se ignoran porque suelen ser regionalismos válidos."
        ),
    )
    return parser


def parse_args() -> argparse.Namespace:
    """Parsea los argumentos CLI."""
    parser = build_parser()
    return parser.parse_args()


async def main() -> None:
    """Punto de entrada principal."""
    args = parse_args()
    processor = POTranslationProcessor(
        locales=args.locales.split(","),
        origen=args.origen,
        destino=args.destino,
        solo_fuzzy=args.solo_fuzzy,
        resume=args.resume,
        sync_only=args.sync_only,
        compile_mo=args.compile_mo,
        cache_path=args.cache_path,
        disable_cache=args.disable_cache,
        stats_only=args.stats_only,
        dry_run=args.dry_run,
        report_inconsistencies=args.report_inconsistencies,
    )
    await processor.run()


if __name__ == "__main__":
    asyncio.run(main())
