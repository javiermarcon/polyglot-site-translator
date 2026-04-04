"""Behave environment configuration."""

from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("KIVY_NO_FILELOG", "1")

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
