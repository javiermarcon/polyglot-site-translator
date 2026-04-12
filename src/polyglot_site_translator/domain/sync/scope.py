"""Typed models for adapter-driven synchronization scopes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SyncFilterType(StrEnum):
    """Supported sync filter matching strategies."""

    DIRECTORY = "directory"
    FILE = "file"


class SyncRuleBehavior(StrEnum):
    """Supported rule behaviors for sync scope entries."""

    INCLUDE = "include"
    EXCLUDE = "exclude"


class SyncRuleSource(StrEnum):
    """Origin of a resolved sync rule."""

    ADAPTER = "adapter"
    PROJECT = "project"


class SyncScopeStatus(StrEnum):
    """Explicit outcomes for framework sync scope resolution."""

    FILTERED = "filtered"
    NO_FILTERS = "no_filters"
    FRAMEWORK_UNRESOLVED = "framework_unresolved"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"


@dataclass(frozen=True)
class AdapterSyncScope:
    """Adapter-owned include/exclude rules for synchronization."""

    filters: tuple[SyncFilterSpec, ...] = ()
    excludes: tuple[SyncFilterSpec, ...] = ()

    @property
    def is_empty(self) -> bool:
        """Return whether the adapter provides no sync rules."""
        return self.filters == () and self.excludes == ()


@dataclass(frozen=True)
class ProjectSyncRuleOverride:
    """Persisted project-specific override or custom sync rule."""

    rule_key: str
    relative_path: str
    filter_type: SyncFilterType
    behavior: SyncRuleBehavior
    is_enabled: bool
    description: str = ""
    target_rule_key: str | None = None

    @property
    def is_custom(self) -> bool:
        """Return whether the override introduces a custom project rule."""
        return self.target_rule_key is None


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
class ResolvedSyncRule:
    """A resolved rule surfaced to services and UI catalogs."""

    rule_key: str
    relative_path: str
    filter_type: SyncFilterType
    behavior: SyncRuleBehavior
    description: str
    source: SyncRuleSource
    is_enabled: bool

    def as_filter_spec(self) -> SyncFilterSpec:
        """Return the matching filter spec for this rule."""
        return SyncFilterSpec(
            relative_path=self.relative_path,
            filter_type=self.filter_type,
            description=self.description,
        )


@dataclass(frozen=True)
class ResolvedSyncScope:
    """Resolved adapter scope reused by both sync directions."""

    framework_type: str
    adapter_name: str | None
    status: SyncScopeStatus
    filters: tuple[SyncFilterSpec, ...]
    message: str
    excludes: tuple[SyncFilterSpec, ...] = ()
    catalog_rules: tuple[ResolvedSyncRule, ...] = ()

    @property
    def is_filtered(self) -> bool:
        """Return whether the scope actively restricts synchronized paths."""
        return self.status is SyncScopeStatus.FILTERED and (
            self.filters != () or self.excludes != ()
        )

    def includes(self, relative_path: str) -> bool:
        """Return whether a relative path belongs to the resolved scope."""
        if any(sync_filter.matches(relative_path) for sync_filter in self.excludes):
            return False
        if not self.is_filtered:
            return True
        return any(sync_filter.matches(relative_path) for sync_filter in self.filters)


def _normalize_relative_path(value: str) -> str:
    return value.strip().strip("/")


def build_sync_rule_key(
    *,
    relative_path: str,
    filter_type: SyncFilterType,
    behavior: SyncRuleBehavior,
) -> str:
    """Build the stable rule key used by adapter rules and project overrides."""
    normalized_path = _normalize_relative_path(relative_path)
    return f"{behavior.value}:{filter_type.value}:{normalized_path}"
