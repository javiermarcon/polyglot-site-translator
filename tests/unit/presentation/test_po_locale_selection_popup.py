"""Tests for the PO locale selection popup."""

from __future__ import annotations

from pytest import MonkeyPatch

from polyglot_site_translator.presentation.kivy.widgets.po_locale_selection_popup import (
    POLocaleSelectionPopup,
)


def test_po_locale_selection_popup_preloads_default_locales() -> None:
    popup = POLocaleSelectionPopup(default_locales="es_ES,es_AR", on_confirm=lambda _v: None)

    assert popup.title == "Process PO"
    assert popup._locales_input.text == "es_ES,es_AR"


def test_po_locale_selection_popup_normalizes_and_confirms_locales(
    monkeypatch: MonkeyPatch,
) -> None:
    popup = POLocaleSelectionPopup(default_locales="es_ES", on_confirm=lambda _v: None)
    confirmed: list[str] = []
    dismiss_calls: list[str] = []

    def record_confirm(locales: str) -> None:
        confirmed.append(locales)

    monkeypatch.setattr(popup, "_on_confirm", record_confirm)
    monkeypatch.setattr(popup, "dismiss", lambda: dismiss_calls.append("dismiss"))
    popup._locales_input.text = "es_ES, es_AR"

    popup._submit()

    assert confirmed == ["es_ES,es_AR"]
    assert dismiss_calls == ["dismiss"]


def test_po_locale_selection_popup_keeps_open_when_locales_are_invalid() -> None:
    popup = POLocaleSelectionPopup(default_locales="es_ES", on_confirm=lambda _v: None)
    popup._locales_input.text = "asad@"

    popup._submit()

    assert popup._error_label.text == (
        "Selected locales must be a valid locale or a comma-separated list of valid "
        "locales. Invalid values: asad@."
    )
