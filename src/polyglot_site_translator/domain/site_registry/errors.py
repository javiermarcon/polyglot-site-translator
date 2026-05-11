"""Domain errors for site registry workflows."""

from __future__ import annotations


class SiteRegistryValidationError(ValueError):
    """Raised when a site registry command contains invalid values.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class SiteRegistryConflictError(ValueError):
    """Raised when a site registry record conflicts with an existing one.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class SiteRegistryNotFoundError(LookupError):
    """Raised when a requested site registry record does not exist.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class SiteRegistryConfigurationError(ValueError):
    """Raised when the configured SQLite database location is invalid.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class SiteRegistryPersistenceError(RuntimeError):
    """Raised when SQLite persistence fails in a controlled way.

    Attributes:
        None: This type does not declare class-level attributes.
    """
