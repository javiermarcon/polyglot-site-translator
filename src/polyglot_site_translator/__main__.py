"""Executable module for the Kivy frontend shell."""

from __future__ import annotations

import os
from typing import Any, cast

os.environ.setdefault("KIVY_NO_FILELOG", "1")

from polyglot_site_translator.app import create_kivy_app


def main() -> None:
    """Start the Kivy application."""
    cast(Any, create_kivy_app()).run()


if __name__ == "__main__":
    main()
