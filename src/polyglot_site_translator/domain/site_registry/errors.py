"""Domain errors for site registry workflows."""

from __future__ import annotations


class SiteRegistryValidationError(ValueError):
    """Raised when a site registry command contains invalid values."""


class SiteRegistryConflictError(ValueError):
    """Raised when a site registry record conflicts with an existing one."""


class SiteRegistryNotFoundError(LookupError):
    """Raised when a requested site registry record does not exist."""


class SiteRegistryConfigurationError(ValueError):
    """Raised when the configured SQLite database location is invalid."""


class SiteRegistryPersistenceError(RuntimeError):
    """Raised when SQLite persistence fails in a controlled way."""
