"""Test configuration shared across the suite."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


@pytest.fixture(autouse=True)
def isolate_user_config_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Force tests to use an isolated user config directory."""
    monkeypatch.setenv("POLYGLOT_SITE_TRANSLATOR_CONFIG_DIR", str(tmp_path))
