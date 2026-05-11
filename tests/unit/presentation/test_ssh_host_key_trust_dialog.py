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
    """Test helper for FakeTrustPopup.

    Attributes:
        title (str): Documented attribute exposed by this type.
        size_hint (tuple[float, float] | None): Documented attribute exposed by this type.
        auto_dismiss (bool): Documented attribute exposed by this type.
        content (object | None): Documented attribute exposed by this type.
        opened (bool): Documented attribute exposed by this type.
        dismissed (bool): Documented attribute exposed by this type.
    """

    title: str = ""
    size_hint: tuple[float, float] | None = None
    auto_dismiss: bool = False
    content: object | None = None
    opened: bool = False
    dismissed: bool = False

    def open(self) -> None:
        """Handle open.

        Returns:
            None: This callable does not return a value.
        """
        self.opened = True

    def dismiss(self) -> None:
        """Handle dismiss.

        Returns:
            None: This callable does not return a value.
        """
        self.dismissed = True


def test_open_ssh_host_key_trust_confirmation_builds_modal(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify open ssh host key trust confirmation builds modal.

    Args:
        monkeypatch (MonkeyPatch): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    built: list[_FakeTrustPopup] = []

    def build_popup(
        *,
        title: str,
        size_hint: tuple[float, float],
        auto_dismiss: bool,
    ) -> Any:
        """Handle build popup.

        Args:
            title (str): Value supplied to this callable.
            size_hint (tuple[float, float]): Value supplied to this callable.
            auto_dismiss (bool): Value supplied to this callable.

        Returns:
            Any: Structured value returned by this callable.
        """
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
    """Verify open ssh host key trust confirmation callbacks work.

    Args:
        monkeypatch (MonkeyPatch): Value supplied to this callable.

    Returns:
        None: This callable does not return a value.
    """
    built: list[_FakeTrustPopup] = []
    trust_calls: list[str] = []

    def build_popup(
        *,
        title: str,
        size_hint: tuple[float, float],
        auto_dismiss: bool,
    ) -> Any:
        """Handle build popup.

        Args:
            title (str): Value supplied to this callable.
            size_hint (tuple[float, float]): Value supplied to this callable.
            auto_dismiss (bool): Value supplied to this callable.

        Returns:
            Any: Structured value returned by this callable.
        """
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
