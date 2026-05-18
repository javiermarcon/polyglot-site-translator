"""Unit tests for UI localization catalogs and helpers."""

from __future__ import annotations

import gettext

import pytest

from polyglot_site_translator.presentation.ui_localization import (
    DEFAULT_UI_LANGUAGE,
    available_ui_language_options,
    build_translation,
    is_supported_ui_language,
    set_active_ui_language,
    tr,
    tr_ui_text,
)
from polyglot_site_translator.presentation.view_models import (
    build_navigation_menu_state,
)


def test_available_ui_languages_are_loaded_from_gettext_catalogs() -> None:
    """Verify UI languages are discovered from packaged gettext catalogs.

    Returns:
        value:
            Structured value returned by this callable.
    """
    options = available_ui_language_options()

    assert [option.value for option in options] == ["en", "es"]
    assert [option.label for option in options] == ["English", "Castellano"]


def test_default_language_uses_english_gettext_catalog() -> None:
    """Verify the default language uses the English gettext catalog.

    Returns:
        value:
            Structured value returned by this callable.
    """
    translation = build_translation(DEFAULT_UI_LANGUAGE)

    assert isinstance(translation, gettext.NullTranslations)
    assert translation.gettext("Dashboard") == "Dashboard"
    assert is_supported_ui_language(DEFAULT_UI_LANGUAGE) is True


def test_spanish_language_translates_visible_shell_copy() -> None:
    """Verify Spanish gettext catalogs translate visible UI copy.

    Returns:
        value:
            Structured value returned by this callable.
    """
    translation = build_translation("es")

    assert translation.gettext("Dashboard") == "Inicio"
    assert translation.gettext("Open Projects") == "Abrir proyectos"
    assert translation.gettext("Sync Remote to Local") == "Sincronizar remoto a local"
    assert is_supported_ui_language("es") is True


def test_active_language_controls_tr_helper() -> None:
    """Verify the active language controls the translation helper.

    Returns:
        value:
            Structured value returned by this callable.
    """
    set_active_ui_language("es")
    assert tr("Settings") == "Configuracion"

    set_active_ui_language("en")
    assert tr("Settings") == "Settings"


def test_visible_ui_text_translates_static_fragments() -> None:
    """Verify visible dynamic UI text translates known static fragments.

    Returns:
        value:
            Structured value returned by this callable.
    """
    try:
        set_active_ui_language("es")

        assert tr_ui_text("Open api_django") == "Abrir api_django"
        assert tr_ui_text("Status: running") == "Estado: en ejecucion"
        assert tr_ui_text("Remote user: javier | Sync mode: full") == (
            "Usuario remoto: javier | Modo de sincronizacion: completo"
        )
        assert tr_ui_text(
            "Django via django_adapter (manage.py is present at the project root.; "
            "settings.py was found in the Django configuration package.)"
        ) == (
            "Django mediante adaptador_django (manage.py esta presente en la raiz "
            "del proyecto.; settings.py se encontro en el paquete de configuracion "
            "de Django.)"
        )
        assert tr_ui_text(
            "Files found: 0\nFamilies processed: 0\nTranslated via provider: 0"
        ) == (
            "Archivos encontrados: 0\nFamilias procesadas: 0\n"
            "Traducidas mediante proveedor: 0"
        )
    finally:
        set_active_ui_language("en")


def test_navigation_menu_copy_uses_active_language() -> None:
    """Verify navigation menu copy is rebuilt in the active UI language.

    Returns:
        value:
            Structured value returned by this callable.
    """
    try:
        set_active_ui_language("es")

        state = build_navigation_menu_state(
            active_route_key="dashboard",
            operations_enabled=False,
            is_open=True,
        )
    finally:
        set_active_ui_language("en")

    assert state.sections[0].items[0].title == "Inicio"
    assert state.sections[0].items[0].description == (
        "Resumen y puntos de entrada de la aplicacion."
    )
    assert state.sections[2].items[0].description == (
        "Configuracion de aplicacion, UI y sistema futuro."
    )


def test_unsupported_language_raises_value_error() -> None:
    """Verify unsupported languages fail explicitly.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        ValueError:
            Raised when the helper accepts an unsupported language.
    """
    with pytest.raises(ValueError, match="Unsupported UI language: fr"):
        set_active_ui_language("fr")
