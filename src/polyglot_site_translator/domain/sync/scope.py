"""Typed models for adapter-driven synchronization scopes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fnmatch import fnmatch


class SyncFilterType(StrEnum):
    """Supported sync filter matching strategies.

    Attributes:
        DIRECTORY:
            Documented attribute exposed by this type.
        FILE:
            Documented attribute exposed by this type.
        GLOB:
            Documented attribute exposed by this type.
    """

    DIRECTORY = "directory"
    FILE = "file"
    GLOB = "glob"


class SyncRuleBehavior(StrEnum):
    """Supported rule behaviors for sync scope entries.

    Attributes:
        INCLUDE:
            Documented attribute exposed by this type.
        EXCLUDE:
            Documented attribute exposed by this type.
    """

    INCLUDE = "include"
    EXCLUDE = "exclude"


class SyncRuleSource(StrEnum):
    """Origin of a resolved sync rule.

    Attributes:
        ADAPTER:
            Documented attribute exposed by this type.
        GLOBAL:
            Documented attribute exposed by this type.
        FRAMEWORK:
            Documented attribute exposed by this type.
        GITIGNORE:
            Documented attribute exposed by this type.
        PROJECT:
            Documented attribute exposed by this type.
    """

    ADAPTER = "adapter"
    GLOBAL = "global"
    FRAMEWORK = "framework"
    GITIGNORE = "gitignore"
    PROJECT = "project"


class SyncScopeStatus(StrEnum):
    """Explicit outcomes for framework sync scope resolution.

    Attributes:
        FILTERED:
            Documented attribute exposed by this type.
        NO_FILTERS:
            Documented attribute exposed by this type.
        FRAMEWORK_UNRESOLVED:
            Documented attribute exposed by this type.
        ADAPTER_UNAVAILABLE:
            Documented attribute exposed by this type.
    """

    FILTERED = "filtered"
    NO_FILTERS = "no_filters"
    FRAMEWORK_UNRESOLVED = "framework_unresolved"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"


@dataclass(frozen=True)
class AdapterSyncScope:
    """Adapter-owned include/exclude rules for synchronization.

    Attributes:
        filters:
            Documented attribute exposed by this type.
        excludes:
            Documented attribute exposed by this type.
    """

    filters: tuple[SyncFilterSpec, ...] = ()
    excludes: tuple[SyncFilterSpec, ...] = ()

    @property
    def is_empty(self) -> bool:
        """Return whether the adapter provides no sync rules.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.filters == () and self.excludes == ()


@dataclass(frozen=True)
class ConfiguredSyncRule:
    """A persisted sync rule configured outside a specific project.

    Attributes:
        relative_path:
            Documented attribute exposed by this type.
        filter_type:
            Documented attribute exposed by this type.
        behavior:
            Documented attribute exposed by this type.
        description:
            Documented attribute exposed by this type.
        is_enabled:
            Documented attribute exposed by this type.
    """

    relative_path: str
    filter_type: SyncFilterType
    behavior: SyncRuleBehavior
    description: str
    is_enabled: bool = True


@dataclass(frozen=True)
class FrameworkSyncRuleSet:
    """A persisted set of sync rules attached to a framework type.

    Attributes:
        framework_type:
            Documented attribute exposed by this type.
        rules:
            Documented attribute exposed by this type.
    """

    framework_type: str
    rules: tuple[ConfiguredSyncRule, ...] = ()

    def normalized_framework_type(self) -> str:
        """Return the canonical lowercase framework type.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.framework_type.strip().lower()


@dataclass(frozen=True)
class AdapterSyncScopeSettings:
    """Persisted sync-scope settings shared across projects.

    Attributes:
        global_rules:
            Documented attribute exposed by this type.
        framework_rule_sets:
            Documented attribute exposed by this type.
        use_gitignore_rules:
            Documented attribute exposed by this type.
    """

    global_rules: tuple[ConfiguredSyncRule, ...] = ()
    framework_rule_sets: tuple[FrameworkSyncRuleSet, ...] = ()
    use_gitignore_rules: bool = False

    def rules_for_framework(
        self, framework_type: str
    ) -> tuple[ConfiguredSyncRule, ...]:
        """Return persisted rules configured for the given framework type.

        Args:
            self:
                Value supplied to this callable.
            framework_type:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        normalized_framework_type = framework_type.strip().lower()
        for rule_set in self.framework_rule_sets:
            if rule_set.normalized_framework_type() == normalized_framework_type:
                return rule_set.rules
        return ()


@dataclass(frozen=True)
class ProjectSyncRuleOverride:
    """Persisted project-specific override or custom sync rule.

    Attributes:
        rule_key:
            Documented attribute exposed by this type.
        relative_path:
            Documented attribute exposed by this type.
        filter_type:
            Documented attribute exposed by this type.
        behavior:
            Documented attribute exposed by this type.
        is_enabled:
            Documented attribute exposed by this type.
        description:
            Documented attribute exposed by this type.
        target_rule_key:
            Documented attribute exposed by this type.
    """

    rule_key: str
    relative_path: str
    filter_type: SyncFilterType
    behavior: SyncRuleBehavior
    is_enabled: bool
    description: str = ""
    target_rule_key: str | None = None

    @property
    def is_custom(self) -> bool:
        """Return whether the override introduces a custom project rule.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.target_rule_key is None


@dataclass(frozen=True)
class SyncFilterSpec:
    """A single adapter-defined sync filter.

    Attributes:
        relative_path:
            Documented attribute exposed by this type.
        filter_type:
            Documented attribute exposed by this type.
        description:
            Documented attribute exposed by this type.
    """

    relative_path: str
    filter_type: SyncFilterType
    description: str

    def matches(self, relative_path: str) -> bool:
        """Return whether the filter includes the given relative path.

        Args:
            self:
                Value supplied to this callable.
            relative_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        normalized_filter = _normalize_relative_path(self.relative_path)
        normalized_path = _normalize_relative_path(relative_path)
        if self.filter_type is SyncFilterType.GLOB:
            return _match_glob_pattern(
                pattern=normalized_filter,
                relative_path=normalized_path,
            )
        if self.filter_type is SyncFilterType.FILE:
            return normalized_path == normalized_filter
        if normalized_path == normalized_filter:
            return True
        return normalized_path.startswith(f"{normalized_filter}/")


@dataclass(frozen=True)
class ResolvedSyncRule:
    """A resolved rule surfaced to services and UI catalogs.

    Attributes:
        rule_key:
            Documented attribute exposed by this type.
        relative_path:
            Documented attribute exposed by this type.
        filter_type:
            Documented attribute exposed by this type.
        behavior:
            Documented attribute exposed by this type.
        description:
            Documented attribute exposed by this type.
        source:
            Documented attribute exposed by this type.
        is_enabled:
            Documented attribute exposed by this type.
    """

    rule_key: str
    relative_path: str
    filter_type: SyncFilterType
    behavior: SyncRuleBehavior
    description: str
    source: SyncRuleSource
    is_enabled: bool

    def as_filter_spec(self) -> SyncFilterSpec:
        """Return the matching filter spec for this rule.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return SyncFilterSpec(
            relative_path=self.relative_path,
            filter_type=self.filter_type,
            description=self.description,
        )


@dataclass(frozen=True)
class ResolvedSyncScope:
    """Resolved adapter scope reused by both sync directions.

    Attributes:
        framework_type:
            Documented attribute exposed by this type.
        adapter_name:
            Documented attribute exposed by this type.
        status:
            Documented attribute exposed by this type.
        filters:
            Documented attribute exposed by this type.
        message:
            Documented attribute exposed by this type.
        excludes:
            Documented attribute exposed by this type.
        catalog_rules:
            Documented attribute exposed by this type.
    """

    framework_type: str
    adapter_name: str | None
    status: SyncScopeStatus
    filters: tuple[SyncFilterSpec, ...]
    message: str
    excludes: tuple[SyncFilterSpec, ...] = ()
    catalog_rules: tuple[ResolvedSyncRule, ...] = ()

    @property
    def is_filtered(self) -> bool:
        """Return whether the scope actively restricts synchronized paths.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.status is SyncScopeStatus.FILTERED and (
            self.filters != () or self.excludes != ()
        )

    def includes(self, relative_path: str) -> bool:
        """Return whether a relative path belongs to the resolved scope.

        Args:
            self:
                Value supplied to this callable.
            relative_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        if any(sync_filter.matches(relative_path) for sync_filter in self.excludes):
            return False
        if not self.is_filtered:
            return True
        return any(sync_filter.matches(relative_path) for sync_filter in self.filters)


def _normalize_relative_path(value: str) -> str:
    """Normalize relative path.

    Args:
        value:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return value.strip().strip("/")


def build_sync_rule_key(
    *,
    relative_path: str,
    filter_type: SyncFilterType,
    behavior: SyncRuleBehavior,
) -> str:
    """Build the stable rule key used by adapter rules and project overrides.

    Args:
        relative_path:
            Value supplied to this callable.
        filter_type:
            Value supplied to this callable.
        behavior:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    normalized_path = _normalize_relative_path(relative_path)
    return f"{behavior.value}:{filter_type.value}:{normalized_path}"


def build_global_sync_rule_key(
    *,
    relative_path: str,
    filter_type: SyncFilterType,
    behavior: SyncRuleBehavior,
) -> str:
    """Build the stable rule key used by global sync rules.

    Args:
        relative_path:
            Value supplied to this callable.
        filter_type:
            Value supplied to this callable.
        behavior:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    base_rule_key = build_sync_rule_key(
        relative_path=relative_path,
        filter_type=filter_type,
        behavior=behavior,
    )
    return f"global:{base_rule_key}"


def build_framework_sync_rule_key(
    *,
    framework_type: str,
    relative_path: str,
    filter_type: SyncFilterType,
    behavior: SyncRuleBehavior,
) -> str:
    """Build the stable rule key used by framework-level sync rules.

    Args:
        framework_type:
            Value supplied to this callable.
        relative_path:
            Value supplied to this callable.
        filter_type:
            Value supplied to this callable.
        behavior:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    normalized_framework_type = framework_type.strip().lower()
    base_rule_key = build_sync_rule_key(
        relative_path=relative_path,
        filter_type=filter_type,
        behavior=behavior,
    )
    return f"framework:{normalized_framework_type}:{base_rule_key}"


def build_gitignore_sync_rule_key(
    *,
    pattern: str,
) -> str:
    """Build the stable rule key used by gitignore-derived rules.

    Args:
        pattern:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return f"gitignore:{pattern.strip()}"


def build_default_sync_scope_settings() -> AdapterSyncScopeSettings:
    """Return the default persisted sync-scope settings.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return AdapterSyncScopeSettings(
        global_rules=(
            ConfiguredSyncRule(
                relative_path=".git",
                filter_type=SyncFilterType.DIRECTORY,
                behavior=SyncRuleBehavior.EXCLUDE,
                description="Ignore Git metadata directories.",
                is_enabled=True,
            ),
        ),
        framework_rule_sets=(),
        use_gitignore_rules=False,
    )


def _match_glob_pattern(*, pattern: str, relative_path: str) -> bool:
    """Handle match glob pattern.

    Args:
        pattern:
            Value supplied to this callable.
        relative_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    segments = relative_path.split("/")
    basename = relative_path.rsplit("/", maxsplit=1)[-1]
    if fnmatch(relative_path, pattern):
        return True
    if "/" not in pattern:
        if pattern in segments:
            return True
        if fnmatch(basename, pattern):
            return True
        if any(fnmatch(segment, pattern) for segment in segments):
            return True
    return any(
        fnmatch("/".join(segments[index:]), pattern)
        for index in range(1, len(segments))
    )
