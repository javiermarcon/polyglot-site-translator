"""Local launcher for the src-layout application package."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys

os.environ.setdefault("KIVY_NO_FILELOG", "1")

SRC_PATH = Path(__file__).resolve().parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def main() -> None:
    """Run the application through the package entrypoint."""
    package_main = importlib.import_module("polyglot_site_translator.__main__").main
    package_main()


if __name__ == "__main__":
    main()
