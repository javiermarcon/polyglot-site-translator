"""Executable module for the Kivy frontend shell."""

from __future__ import annotations

from typing import Any, cast

from polyglot_site_translator.app import create_kivy_app


def main() -> None:
    """Start the Kivy application."""
    cast(Any, create_kivy_app()).run()


if __name__ == "__main__":
    main()
