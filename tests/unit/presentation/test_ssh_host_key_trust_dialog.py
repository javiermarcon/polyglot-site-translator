"""Tests for the shared SSH host-key confirmation dialog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from pytest import MonkeyPatch

from polyglot_site_translator.presentation.kivy.widgets.ssh_host_key_trust_dialog import (
    open_ssh_host_key_trust_confirmation,
)


@dataclass
class _FakeTrustPopup:
    title: str = ""
    size_hint: tuple[float, float] | None = None
    auto_dismiss: bool = False
    content: object | None = None
    opened: bool = False
    dismissed: bool = False

    def open(self) -> None:
        self.opened = True

    def dismiss(self) -> None:
        self.dismissed = True


def test_open_ssh_host_key_trust_confirmation_builds_modal(
    monkeypatch: MonkeyPatch,
) -> None:
    built: list[_FakeTrustPopup] = []

    def build_popup(
        *,
        title: str,
        size_hint: tuple[float, float],
        auto_dismiss: bool,
    ) -> Any:
        popup = _FakeTrustPopup(
            title=title,
            size_hint=size_hint,
            auto_dismiss=auto_dismiss,
        )
        built.append(popup)
        return popup

    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.ssh_host_key_trust_dialog.Popup",
        build_popup,
    )

    open_ssh_host_key_trust_confirmation(on_trust=lambda: None, purpose="connection_test")

    assert len(built) == 1
    assert built[0].title == "Trust SSH Host Key?"
    assert built[0].opened is True


def test_open_ssh_host_key_trust_confirmation_callbacks_work(
    monkeypatch: MonkeyPatch,
) -> None:
    built: list[_FakeTrustPopup] = []
    trust_calls: list[str] = []

    def build_popup(
        *,
        title: str,
        size_hint: tuple[float, float],
        auto_dismiss: bool,
    ) -> Any:
        popup = _FakeTrustPopup(
            title=title,
            size_hint=size_hint,
            auto_dismiss=auto_dismiss,
        )
        built.append(popup)
        return popup

    monkeypatch.setattr(
        "polyglot_site_translator.presentation.kivy.widgets.ssh_host_key_trust_dialog.Popup",
        build_popup,
    )

    open_ssh_host_key_trust_confirmation(
        on_trust=lambda: trust_calls.append("trusted"),
        purpose="sync",
    )

    popup = built[0]
    container = popup.content
    actions = cast(Any, container).children[0]
    accept_button = actions.children[1]
    cancel_button = actions.children[0]

    accept_button.dispatch("on_release")
    assert popup.dismissed is True
    assert trust_calls == ["trusted"]

    popup.dismissed = False
    cancel_button.dispatch("on_release")
    assert popup.dismissed is True
