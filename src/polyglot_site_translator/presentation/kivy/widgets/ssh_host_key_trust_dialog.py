"""Shared SSH host-key trust confirmation popup for sync and project editor flows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup

from polyglot_site_translator.presentation.kivy.widgets.common import AppButton, WrappedLabel

_PURPOSE_MESSAGES: dict[str, str] = {
    "sync": (
        "The remote SSH host key is not in known_hosts. Trust it only if "
        "you verified this server is expected, then retry sync."
    ),
    "connection_test": (
        "The remote SSH host key is not in known_hosts. Trust it only if "
        "you verified this server is expected, then retry the connection test."
    ),
}


def open_ssh_host_key_trust_confirmation(
    *,
    on_trust: Callable[[], None],
    purpose: Literal["sync", "connection_test"] = "sync",
) -> None:
    """Show the confirmation popup; call ``on_trust`` after the user accepts."""
    confirmation = Popup(
        title="Trust SSH Host Key?",
        size_hint=(0.72, 0.42),
        auto_dismiss=False,
    )
    container = BoxLayout(orientation="vertical", spacing=12, padding=12)
    container.add_widget(WrappedLabel(text=_PURPOSE_MESSAGES[purpose]))
    actions = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=48)
    accept_button = AppButton(text="Trust and Retry", primary=True)
    cancel_button = AppButton(text="Cancel", primary=False)

    def accept(_instance: object) -> None:
        confirmation.dismiss()
        on_trust()

    accept_button.bind(on_release=accept)
    cancel_button.bind(on_release=lambda *_event_args: confirmation.dismiss())
    actions.add_widget(accept_button)
    actions.add_widget(cancel_button)
    container.add_widget(actions)
    confirmation.content = container
    confirmation.open()
