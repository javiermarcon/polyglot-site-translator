"""Tests for the PO locale selection popup."""

from __future__ import annotations

from pytest import MonkeyPatch

from polyglot_site_translator.presentation.kivy.widgets.po_locale_selection_popup import (
    POLocaleSelectionPopup,
)
from polyglot_site_translator.presentation.view_models import (
    TranslationOptionsViewModel,
    TranslationWorkflowRequestViewModel,
)


def _build_options() -> TranslationOptionsViewModel:
    """Handle build options.

    Returns:
        TranslationOptionsViewModel: Structured value returned by this callable.
    """
    return TranslationOptionsViewModel(
        compile_mo=True,
        use_external_translator=False,
        use_translation_cache=False,
        only_fuzzy=True,
        dry_run=True,
        stats_only=False,
        report_inconsistencies=True,
    )


def test_po_locale_selection_popup_preloads_default_locales() -> None:
    """Verify po locale selection popup preloads default locales.

    Returns:
        None: This callable does not return a value.
    """
    popup = POLocaleSelectionPopup(
        default_locales="es_ES,es_AR",
        default_options=_build_options(),
        on_confirm=lambda _request: None,
    )

    assert popup.title == "Translate Project"
    assert popup._locales_input.text == "es_ES,es_AR"
    assert popup._compile_mo_switch.active is True
    assert popup._use_external_translator_switch.active is False
    assert popup._use_translation_cache_switch.active is False
    assert popup._only_fuzzy_switch.active is True
    assert popup._dry_run_switch.active is True
    assert popup._stats_only_switch.active is False
    assert popup._report_inconsistencies_switch.active is True
    assert tuple(popup.size_hint) == (0.86, 0.9)
    assert len(popup._toggle_rows) == 7
    assert popup._toggle_rows[0].height == 58
    assert popup._toggle_rows[0].children[-1].children[-1].text == "Compile MO Files"


def test_po_locale_selection_popup_normalizes_and_confirms_locales(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify po locale selection popup normalizes and confirms locales.

    Args:
        monkeypatch (MonkeyPatch): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    popup = POLocaleSelectionPopup(
        default_locales="es_ES",
        default_options=TranslationOptionsViewModel(
            compile_mo=False,
            use_external_translator=False,
            use_translation_cache=False,
            only_fuzzy=False,
            dry_run=False,
            stats_only=False,
            report_inconsistencies=False,
        ),
        on_confirm=lambda _request: None,
    )
    confirmed: list[TranslationWorkflowRequestViewModel] = []
    dismiss_calls: list[str] = []

    def record_confirm(request: TranslationWorkflowRequestViewModel) -> None:
        """Handle record confirm.

        Args:
            request (TranslationWorkflowRequestViewModel): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
        confirmed.append(request)

    monkeypatch.setattr(popup, "_on_confirm", record_confirm)
    monkeypatch.setattr(popup, "dismiss", lambda: dismiss_calls.append("dismiss"))
    popup._locales_input.text = "es_ES, es_AR"
    popup._compile_mo_switch.active = True
    popup._use_external_translator_switch.active = True
    popup._use_translation_cache_switch.active = True
    popup._only_fuzzy_switch.active = True
    popup._dry_run_switch.active = True
    popup._stats_only_switch.active = True
    popup._report_inconsistencies_switch.active = True

    popup._submit()

    assert confirmed == [
        TranslationWorkflowRequestViewModel(
            locales="es_ES,es_AR",
            options=TranslationOptionsViewModel(
                compile_mo=True,
                use_external_translator=True,
                use_translation_cache=True,
                only_fuzzy=True,
                dry_run=True,
                stats_only=True,
                report_inconsistencies=True,
            ),
        )
    ]
    assert dismiss_calls == ["dismiss"]


def test_po_locale_selection_popup_keeps_open_when_locales_are_invalid() -> None:
    """Verify po locale selection popup keeps open when locales are invalid.

    Returns:
        None: This callable does not return a value.
    """
    popup = POLocaleSelectionPopup(
        default_locales="es_ES",
        default_options=TranslationOptionsViewModel(),
        on_confirm=lambda _request: None,
    )
    popup._locales_input.text = "asad@"

    popup._submit()

    assert popup._error_label.text == (
        "Selected locales must be a valid locale or a comma-separated list of valid "
        "locales. Invalid values: asad@."
    )


def test_po_locale_selection_popup_builds_consistent_toggle_row_copy() -> None:
    """Verify po locale selection popup builds consistent toggle row copy.

    Returns:
        None: This callable does not return a value.
    """
    popup = POLocaleSelectionPopup(
        default_locales="es_ES",
        default_options=TranslationOptionsViewModel(),
        on_confirm=lambda _request: None,
    )

    titles = [row.children[-1].children[-1].text for row in popup._toggle_rows]

    assert titles == [
        "Compile MO Files",
        "Use External Translator",
        "Use Translation Cache",
        "Only Fuzzy Entries",
        "Dry-run",
        "Stats Only",
        "Report Inconsistencies",
    ]
    assert popup.content.children[-1] is popup._options_container
