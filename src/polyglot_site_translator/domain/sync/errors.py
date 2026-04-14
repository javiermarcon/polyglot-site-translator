"""Explicit sync-domain errors."""

from __future__ import annotations


class SyncConfigurationError(ValueError):
    """Raised when a sync workflow is configured incorrectly."""


class SyncScopePersistenceError(RuntimeError):
    """Raised when persisted sync scope settings cannot be loaded or saved."""


class SyncOperationError(RuntimeError):
    """Raised when a sync operation fails at runtime."""
