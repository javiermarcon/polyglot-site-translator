"""Unit tests for Kivy widget localization behavior."""

from __future__ import annotations

from polyglot_site_translator.presentation.kivy.widgets.common import (
    AppButton,
    WrappedLabel,
)
from polyglot_site_translator.presentation.ui_localization import (
    set_active_ui_language,
)


def test_static_widget_text_uses_active_ui_language() -> None:
    """Verify reusable widgets translate static operator-facing copy.

    Returns:
        value:
            Structured value returned by this callable.
    """
    try:
        set_active_ui_language("es")
        label = WrappedLabel(text="Settings")
        button = AppButton(text="Open Projects")
        project_button = AppButton(text="Open api_django")
        evidence_label = WrappedLabel(
            text=(
                "Framework detection: Django via django_adapter "
                "(manage.py is present at the project root.)"
            )
        )
    finally:
        set_active_ui_language("en")

    assert label.text == "Configuracion"
    assert button.text == "Abrir proyectos"
    assert project_button.text == "Abrir api_django"
    assert evidence_label.text == (
        "Deteccion de framework: Django mediante adaptador_django "
        "(manage.py esta presente en la raiz del proyecto.)"
    )
