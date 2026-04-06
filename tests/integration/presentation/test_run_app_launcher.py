"""Integration tests for the local launcher script."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def test_run_app_launcher_imports_package_entrypoint() -> None:
    launcher_path = Path(__file__).resolve().parents[3] / "run_app.py"
    spec = importlib.util.spec_from_file_location("run_app", launcher_path)

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert hasattr(module, "main")
