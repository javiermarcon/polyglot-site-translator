"""Explicit sync-domain errors."""

from __future__ import annotations


class SyncConfigurationError(ValueError):
    """Raised when a sync workflow is configured incorrectly."""


class SyncOperationError(RuntimeError):
    """Raised when a sync operation fails at runtime."""
