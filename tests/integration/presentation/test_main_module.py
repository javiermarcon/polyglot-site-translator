"""Integration tests for the executable module entrypoint."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import runpy
import sys
from types import ModuleType

from pytest import MonkeyPatch


def test_main_function_runs_the_created_app(monkeypatch: MonkeyPatch) -> None:
    """Verify main function runs the created app.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    main_module = importlib.import_module("polyglot_site_translator.__main__")

    calls: list[str] = []

    class FakeApp:
        """Test helper for FakeApp.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        def run(self) -> None:
            """Handle run.

            Args:
                self:
                    Value supplied to this callable.

            Returns:
                value:
                    Structured value returned by this callable.
            """
            calls.append("run")

    def _create_fake_app() -> FakeApp:
        """Handle create fake app.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return FakeApp()

    monkeypatch.setattr(main_module, "create_kivy_app", _create_fake_app)

    main_module.main()

    assert calls == ["run"]


def test_running_module_as_main_sets_kivy_filelog_default_and_executes_main(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify running module as main sets kivy filelog default and executes main.

    Args:
        monkeypatch:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    fake_app_module = ModuleType("polyglot_site_translator.app")
    calls: list[str] = []

    class FakeApp:
        """Test helper for FakeApp.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        def run(self) -> None:
            """Handle run.

            Args:
                self:
                    Value supplied to this callable.

            Returns:
                value:
                    Structured value returned by this callable.
            """
            calls.append("run")

    def _create_fake_app() -> FakeApp:
        """Handle create fake app.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return FakeApp()

    fake_app_module.create_kivy_app = _create_fake_app  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "polyglot_site_translator.app", fake_app_module)
    monkeypatch.delenv("KIVY_NO_FILELOG", raising=False)
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "src"))
    sys.modules.pop("polyglot_site_translator.__main__", None)

    runpy.run_module("polyglot_site_translator.__main__", run_name="__main__")

    assert calls == ["run"]
    assert os.environ["KIVY_NO_FILELOG"] == "1"
