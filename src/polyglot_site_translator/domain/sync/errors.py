"""Explicit sync-domain errors."""

from __future__ import annotations


class SyncConfigurationError(ValueError):
    """Raised when a sync workflow is configured incorrectly.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """


class SyncScopePersistenceError(RuntimeError):
    """Raised when persisted sync scope settings cannot be loaded or saved.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """


class SyncOperationError(RuntimeError):
    """Raised when a sync operation fails at runtime.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """
