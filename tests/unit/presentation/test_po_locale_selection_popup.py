"""Tests for the PO locale selection popup."""

from __future__ import annotations

from pytest import MonkeyPatch

from polyglot_site_translator.presentation.kivy.widgets.po_locale_selection_popup import (
    POLocaleSelectionPopup,
)


def test_po_locale_selection_popup_preloads_default_locales() -> None:
    popup = POLocaleSelectionPopup(
        default_locales="es_ES,es_AR",
        default_compile_mo=True,
        on_confirm=lambda _locales, _compile_mo: None,
    )

    assert popup.title == "Translate Project"
    assert popup._locales_input.text == "es_ES,es_AR"
    assert popup._compile_mo_switch.active is True


def test_po_locale_selection_popup_normalizes_and_confirms_locales(
    monkeypatch: MonkeyPatch,
) -> None:
    popup = POLocaleSelectionPopup(
        default_locales="es_ES",
        default_compile_mo=False,
        on_confirm=lambda _locales, _compile_mo: None,
    )
    confirmed: list[tuple[str, bool]] = []
    dismiss_calls: list[str] = []

    def record_confirm(locales: str, compile_mo: bool) -> None:
        confirmed.append((locales, compile_mo))

    monkeypatch.setattr(popup, "_on_confirm", record_confirm)
    monkeypatch.setattr(popup, "dismiss", lambda: dismiss_calls.append("dismiss"))
    popup._locales_input.text = "es_ES, es_AR"
    popup._compile_mo_switch.active = True

    popup._submit()

    assert confirmed == [("es_ES,es_AR", True)]
    assert dismiss_calls == ["dismiss"]


def test_po_locale_selection_popup_keeps_open_when_locales_are_invalid() -> None:
    popup = POLocaleSelectionPopup(
        default_locales="es_ES",
        default_compile_mo=True,
        on_confirm=lambda _locales, _compile_mo: None,
    )
    popup._locales_input.text = "asad@"

    popup._submit()

    assert popup._error_label.text == (
        "Selected locales must be a valid locale or a comma-separated list of valid "
        "locales. Invalid values: asad@."
    )
