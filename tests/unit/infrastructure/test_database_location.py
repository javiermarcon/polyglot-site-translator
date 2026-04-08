"""Unit tests for SQLite database location resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from polyglot_site_translator.infrastructure.database_location import (
    SQLiteDatabaseLocation,
    resolve_sqlite_database_location,
)
from polyglot_site_translator.presentation.view_models import AppSettingsViewModel


def test_resolve_sqlite_database_location_joins_directory_and_filename() -> None:
    settings = AppSettingsViewModel(
        database_directory="/var/tmp/polyglot",
        database_filename="registry.sqlite3",
    )

    location = resolve_sqlite_database_location(settings)

    assert location == SQLiteDatabaseLocation(
        directory=Path("/var/tmp/polyglot"),
        filename="registry.sqlite3",
        database_path=Path("/var/tmp/polyglot/registry.sqlite3"),
    )


def test_resolve_sqlite_database_location_adds_sqlite_extension_when_missing() -> None:
    settings = AppSettingsViewModel(
        database_directory="/var/tmp/polyglot",
        database_filename="registry",
    )

    location = resolve_sqlite_database_location(settings)

    assert location.filename == "registry.sqlite3"
    assert location.database_path == Path("/var/tmp/polyglot/registry.sqlite3")


@pytest.mark.parametrize(
    ("directory", "filename", "expected_message"),
    [
        ("", "registry.sqlite3", r"Database directory must not be empty\."),
        ("/var/tmp/polyglot", "", r"Database filename must not be empty\."),
        (
            "/var/tmp/polyglot",
            "../registry.sqlite3",
            r"Database filename must not contain path separators\.",
        ),
    ],
)
def test_resolve_sqlite_database_location_rejects_invalid_values(
    directory: str,
    filename: str,
    expected_message: str,
) -> None:
    settings = AppSettingsViewModel(
        database_directory=directory,
        database_filename=filename,
    )

    with pytest.raises(ValueError, match=expected_message):
        resolve_sqlite_database_location(settings)
