"""Typed models for adapter-driven synchronization scopes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SyncFilterType(StrEnum):
    """Supported sync filter matching strategies."""

    DIRECTORY = "directory"
    FILE = "file"


class SyncScopeStatus(StrEnum):
    """Explicit outcomes for framework sync scope resolution."""

    FILTERED = "filtered"
    NO_FILTERS = "no_filters"
    FRAMEWORK_UNRESOLVED = "framework_unresolved"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"


@dataclass(frozen=True)
class SyncFilterSpec:
    """A single adapter-defined sync filter."""

    relative_path: str
    filter_type: SyncFilterType
    description: str

    def matches(self, relative_path: str) -> bool:
        """Return whether the filter includes the given relative path."""
        normalized_filter = _normalize_relative_path(self.relative_path)
        normalized_path = _normalize_relative_path(relative_path)
        if self.filter_type is SyncFilterType.FILE:
            return normalized_path == normalized_filter
        if normalized_path == normalized_filter:
            return True
        return normalized_path.startswith(f"{normalized_filter}/")


@dataclass(frozen=True)
class ResolvedSyncScope:
    """Resolved adapter scope reused by both sync directions."""

    framework_type: str
    adapter_name: str | None
    status: SyncScopeStatus
    filters: tuple[SyncFilterSpec, ...]
    message: str

    @property
    def is_filtered(self) -> bool:
        """Return whether the scope actively restricts synchronized paths."""
        return self.status is SyncScopeStatus.FILTERED and self.filters != ()

    def includes(self, relative_path: str) -> bool:
        """Return whether a relative path belongs to the resolved scope."""
        if not self.is_filtered:
            return True
        return any(sync_filter.matches(relative_path) for sync_filter in self.filters)


def _normalize_relative_path(value: str) -> str:
    return value.strip().strip("/")
