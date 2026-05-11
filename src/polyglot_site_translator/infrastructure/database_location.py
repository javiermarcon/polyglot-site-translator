"""Helpers for resolving the SQLite site registry location."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryConfigurationError,
)
from polyglot_site_translator.presentation.view_models import AppSettingsViewModel

DEFAULT_DATABASE_FILENAME = "site_registry.sqlite3"


@dataclass(frozen=True)
class SQLiteDatabaseLocation:
    """Resolved SQLite database location used by the site registry.

    Attributes:
        directory (Path): Documented attribute exposed by this type.
        filename (str): Documented attribute exposed by this type.
        database_path (Path): Documented attribute exposed by this type.
    """

    directory: Path
    filename: str
    database_path: Path


def normalize_database_filename(filename: str) -> str:
    """Return a normalized SQLite database filename.

    Args:
        filename (str): Value supplied to this callable.

    Returns:
        str: Structured value returned by this callable.

    Raises:
        SiteRegistryConfigurationError: Raised when this callable hits the corresponding error path.
    """
    normalized_filename = filename.strip()
    if not normalized_filename:
        msg = "Database filename must not be empty."
        raise SiteRegistryConfigurationError(msg)
    if Path(normalized_filename).name != normalized_filename:
        msg = "Database filename must not contain path separators."
        raise SiteRegistryConfigurationError(msg)
    if not Path(normalized_filename).suffix:
        normalized_filename = f"{normalized_filename}.sqlite3"
    return normalized_filename


def validate_database_directory(directory: str) -> Path:
    """Return the normalized SQLite database directory.

    Args:
        directory (str): Value supplied to this callable.

    Returns:
        Path: Structured value returned by this callable.

    Raises:
        SiteRegistryConfigurationError: Raised when this callable hits the corresponding error path.
    """
    normalized_directory = directory.strip()
    if not normalized_directory:
        msg = "Database directory must not be empty."
        raise SiteRegistryConfigurationError(msg)
    return Path(normalized_directory).expanduser()


def resolve_sqlite_database_location(
    app_settings: AppSettingsViewModel,
) -> SQLiteDatabaseLocation:
    """Resolve the physical SQLite database location from app settings.

    Args:
        app_settings (AppSettingsViewModel): Value supplied to this callable.

    Returns:
        SQLiteDatabaseLocation: Structured value returned by this callable.
    """
    directory = validate_database_directory(app_settings.database_directory)
    filename = normalize_database_filename(app_settings.database_filename)
    return SQLiteDatabaseLocation(
        directory=directory,
        filename=filename,
        database_path=directory / filename,
    )
