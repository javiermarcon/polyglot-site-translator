"""Application service for adapter-driven sync scope resolution."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.domain.sync.errors import (
    SyncConfigurationError,
    SyncScopePersistenceError,
)
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScope,
    AdapterSyncScopeSettings,
    ConfiguredSyncRule,
    ProjectSyncRuleOverride,
    ResolvedSyncRule,
    ResolvedSyncScope,
    SyncFilterSpec,
    SyncRuleBehavior,
    SyncRuleSource,
    SyncScopeStatus,
    build_framework_sync_rule_key,
    build_gitignore_sync_rule_key,
    build_global_sync_rule_key,
    build_sync_rule_key,
)
from polyglot_site_translator.infrastructure.sync_gitignore import (
    load_gitignore_sync_rules,
)

UNKNOWN_FRAMEWORK_TYPE = "unknown"


class FrameworkSyncScopeService:
    """Resolve framework-defined sync filters for registered sites.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def __init__(
        self,
        *,
        registry: FrameworkAdapterRegistry,
        sync_scope_settings_provider: Callable[[], AdapterSyncScopeSettings] | None = None,
        gitignore_rule_loader: Callable[[Path], tuple[ConfiguredSyncRule, ...]] | None = None,
    ) -> None:
        """Store adapter, settings, and gitignore collaborators for scope resolution.

        Args:
            registry (FrameworkAdapterRegistry): Value supplied to this callable.
            sync_scope_settings_provider (Callable[[], AdapterSyncScopeSettings] | None): Value
        supplied to
            this callable.
            gitignore_rule_loader (Callable[[Path], tuple[ConfiguredSyncRule, ...]] | None): Value
        supplied
            to this callable.

        Returns:
            None: This callable does not return a value.
        """
        self._registry = registry
        self._sync_scope_settings_provider = (
            sync_scope_settings_provider or AdapterSyncScopeSettings
        )
        self._gitignore_rule_loader = gitignore_rule_loader or load_gitignore_sync_rules

    def resolve_for_site(self, site: RegisteredSite) -> ResolvedSyncScope:
        """Resolve the sync scope for a persisted site.

        Args:
            site (RegisteredSite): Value supplied to this callable.

        Returns:
            ResolvedSyncScope: Structured value returned by this callable.
        """
        return self.resolve_for_framework(
            framework_type=site.framework_type,
            project_path=Path(site.local_path),
            project_rule_overrides=(
                ()
                if site.remote_connection is None
                else site.remote_connection.flags.sync_rule_overrides
            ),
        )

    def resolve_for_framework(
        self,
        *,
        framework_type: str,
        project_path: Path | str,
        project_rule_overrides: tuple[ProjectSyncRuleOverride, ...] = (),
    ) -> ResolvedSyncScope:
        """Resolve the sync scope for a framework type and project path.

        Args:
            framework_type (str): Value supplied to this callable.
            project_path (Path | str): Value supplied to this callable.
            project_rule_overrides (tuple[ProjectSyncRuleOverride, ...]): Value supplied to this
        callable.

        Returns:
            ResolvedSyncScope: Structured value returned by this callable.
        """
        normalized_framework_type = framework_type.strip().lower()
        sync_scope_settings = self._load_sync_scope_settings()
        gitignore_rules = self._load_project_gitignore_rules(
            sync_scope_settings=sync_scope_settings,
            project_path=Path(project_path),
        )
        resolved_shared_rules = _resolve_scope_rules(
            framework_type=normalized_framework_type,
            adapter_scope=AdapterSyncScope(),
            global_rules=sync_scope_settings.global_rules,
            framework_rules=sync_scope_settings.rules_for_framework(normalized_framework_type),
            gitignore_rules=gitignore_rules,
            project_rule_overrides=project_rule_overrides,
        )
        if normalized_framework_type in {"", UNKNOWN_FRAMEWORK_TYPE}:
            if resolved_shared_rules != ():
                return _build_scope_from_rules(
                    framework_type=normalized_framework_type or UNKNOWN_FRAMEWORK_TYPE,
                    adapter_name=None,
                    resolved_rules=resolved_shared_rules,
                    no_rules_status=SyncScopeStatus.FRAMEWORK_UNRESOLVED,
                    no_rules_message=(
                        "The project does not expose a supported framework type and "
                        "no active global, project or gitignore sync rules are available."
                    ),
                    active_rules_message=(
                        "Framework type is unresolved; using active global, project or "
                        "gitignore sync rules only."
                    ),
                )
            return ResolvedSyncScope(
                framework_type=normalized_framework_type or UNKNOWN_FRAMEWORK_TYPE,
                adapter_name=None,
                status=SyncScopeStatus.FRAMEWORK_UNRESOLVED,
                filters=(),
                excludes=(),
                message="The project does not expose a supported framework type.",
                catalog_rules=(),
            )
        adapter = self._registry.find_adapter(normalized_framework_type)
        if adapter is None:
            if resolved_shared_rules != ():
                return _build_scope_from_rules(
                    framework_type=normalized_framework_type,
                    adapter_name=None,
                    resolved_rules=resolved_shared_rules,
                    no_rules_status=SyncScopeStatus.ADAPTER_UNAVAILABLE,
                    no_rules_message=(
                        "No installed framework adapter can provide sync filters for "
                        f"'{normalized_framework_type}' and no active global, framework, "
                        "project or gitignore sync rules are available."
                    ),
                    active_rules_message=(
                        "No installed framework adapter is available; using active "
                        "global, framework, project or gitignore sync rules only."
                    ),
                )
            return ResolvedSyncScope(
                framework_type=normalized_framework_type,
                adapter_name=None,
                status=SyncScopeStatus.ADAPTER_UNAVAILABLE,
                filters=(),
                excludes=(),
                message=(
                    "No installed framework adapter can provide sync filters for "
                    f"'{normalized_framework_type}'."
                ),
                catalog_rules=(),
            )
        adapter_scope = self._load_adapter_scope(
            framework_type=normalized_framework_type,
            adapter_name=adapter.adapter_name,
            project_path=Path(project_path),
        )
        resolved_rules = _resolve_scope_rules(
            framework_type=normalized_framework_type,
            adapter_scope=adapter_scope,
            global_rules=sync_scope_settings.global_rules,
            framework_rules=sync_scope_settings.rules_for_framework(normalized_framework_type),
            gitignore_rules=gitignore_rules,
            project_rule_overrides=project_rule_overrides,
        )
        return _build_scope_from_rules(
            framework_type=normalized_framework_type,
            adapter_name=adapter.adapter_name,
            resolved_rules=resolved_rules,
            no_rules_status=SyncScopeStatus.NO_FILTERS,
            no_rules_message=(
                f"The adapter '{adapter.adapter_name}' does not define any active sync "
                "include or exclude rules for this framework."
            ),
            active_rules_message=(
                "Resolved "
                "{include_count} active includes and "
                "{exclude_count} active exclusions from adapter "
                f"'{adapter.adapter_name}'."
            ),
        )

    def _load_sync_scope_settings(self) -> AdapterSyncScopeSettings:
        """Load sync scope settings.

        Returns:
            AdapterSyncScopeSettings: Structured value returned by this callable.

        Raises:
            SyncConfigurationError: Raised when this callable hits the corresponding error path.
        """
        try:
            return self._sync_scope_settings_provider()
        except SyncScopePersistenceError:
            raise
        except (LookupError, OSError, RuntimeError, ValueError) as error:
            msg = f"Shared sync scope settings could not be loaded. Cause: {error}"
            raise SyncConfigurationError(msg) from error

    def _load_project_gitignore_rules(
        self,
        *,
        sync_scope_settings: AdapterSyncScopeSettings,
        project_path: Path,
    ) -> tuple[ConfiguredSyncRule, ...]:
        """Load project gitignore rules.

        Args:
            sync_scope_settings (AdapterSyncScopeSettings): Value supplied to this callable.
            project_path (Path): Value supplied to this callable.

        Returns:
            tuple[ConfiguredSyncRule, ...]: Structured value returned by this callable.

        Raises:
            SyncConfigurationError: Raised when this callable hits the corresponding error path.
        """
        try:
            return _load_gitignore_rules(
                sync_scope_settings=sync_scope_settings,
                project_path=project_path,
                gitignore_rule_loader=self._gitignore_rule_loader,
            )
        except SyncScopePersistenceError:
            raise
        except (LookupError, OSError, RuntimeError, ValueError) as error:
            msg = (
                f"Project gitignore sync rules could not be resolved for '{project_path}'. "
                f"Cause: {error}"
            )
            raise SyncConfigurationError(msg) from error

    def _load_adapter_scope(
        self,
        *,
        framework_type: str,
        adapter_name: str,
        project_path: Path,
    ) -> AdapterSyncScope:
        """Load adapter scope.

        Args:
            framework_type (str): Value supplied to this callable.
            adapter_name (str): Value supplied to this callable.
            project_path (Path): Value supplied to this callable.

        Returns:
            AdapterSyncScope: Structured value returned by this callable.

        Raises:
            SyncConfigurationError: Raised when this callable hits the corresponding error path.
        """
        adapter = self._registry.find_adapter(framework_type)
        if adapter is None:
            msg = f"No installed framework adapter can provide sync filters for '{framework_type}'."
            raise SyncConfigurationError(msg)
        try:
            return adapter.get_sync_scope(project_path)
        except (LookupError, OSError, RuntimeError, ValueError) as error:
            msg = (
                f"Framework adapter '{adapter_name}' failed while resolving sync scope for "
                f"'{project_path}'. Cause: {error}"
            )
            raise SyncConfigurationError(msg) from error


def _build_scope_from_rules(  # noqa: PLR0913
    *,
    framework_type: str,
    adapter_name: str | None,
    resolved_rules: tuple[ResolvedSyncRule, ...],
    no_rules_status: SyncScopeStatus,
    no_rules_message: str,
    active_rules_message: str,
) -> ResolvedSyncScope:
    """Build scope from rules.

    Args:
        framework_type (str): Value supplied to this callable.
        adapter_name (str | None): Value supplied to this callable.
        resolved_rules (tuple[ResolvedSyncRule, ...]): Value supplied to this callable.
        no_rules_status (SyncScopeStatus): Value supplied to this callable.
        no_rules_message (str): Value supplied to this callable.
        active_rules_message (str): Value supplied to this callable.

    Returns:
        ResolvedSyncScope: Structured value returned by this callable.
    """
    include_filters = tuple(
        rule.as_filter_spec()
        for rule in resolved_rules
        if rule.is_enabled and rule.behavior is SyncRuleBehavior.INCLUDE
    )
    exclude_filters = tuple(
        rule.as_filter_spec()
        for rule in resolved_rules
        if rule.is_enabled and rule.behavior is SyncRuleBehavior.EXCLUDE
    )
    if include_filters == () and exclude_filters == ():
        return ResolvedSyncScope(
            framework_type=framework_type,
            adapter_name=adapter_name,
            status=no_rules_status,
            filters=(),
            excludes=(),
            message=no_rules_message,
            catalog_rules=resolved_rules,
        )
    return ResolvedSyncScope(
        framework_type=framework_type,
        adapter_name=adapter_name,
        status=SyncScopeStatus.FILTERED,
        filters=include_filters,
        excludes=exclude_filters,
        message=active_rules_message.format(
            include_count=len(include_filters),
            exclude_count=len(exclude_filters),
        ),
        catalog_rules=resolved_rules,
    )


def _resolve_scope_rules(  # noqa: PLR0913
    *,
    framework_type: str,
    adapter_scope: AdapterSyncScope,
    global_rules: tuple[ConfiguredSyncRule, ...],
    framework_rules: tuple[ConfiguredSyncRule, ...],
    gitignore_rules: tuple[ConfiguredSyncRule, ...],
    project_rule_overrides: tuple[ProjectSyncRuleOverride, ...],
) -> tuple[ResolvedSyncRule, ...]:
    """Resolve scope rules.

    Args:
        framework_type (str): Value supplied to this callable.
        adapter_scope (AdapterSyncScope): Value supplied to this callable.
        global_rules (tuple[ConfiguredSyncRule, ...]): Value supplied to this callable.
        framework_rules (tuple[ConfiguredSyncRule, ...]): Value supplied to this callable.
        gitignore_rules (tuple[ConfiguredSyncRule, ...]): Value supplied to this callable.
        project_rule_overrides (tuple[ProjectSyncRuleOverride, ...]): Value supplied to this
    callable.

    Returns:
        tuple[ResolvedSyncRule, ...]: Structured value returned by this callable.
    """
    adapter_rules = [
        *_build_resolved_rules(
            filter_specs=adapter_scope.filters,
            behavior=SyncRuleBehavior.INCLUDE,
            source=SyncRuleSource.ADAPTER,
        ),
        *_build_resolved_rules(
            filter_specs=adapter_scope.excludes,
            behavior=SyncRuleBehavior.EXCLUDE,
            source=SyncRuleSource.ADAPTER,
        ),
        *_build_resolved_rules_from_configured(
            configured_rules=global_rules,
            source=SyncRuleSource.GLOBAL,
        ),
        *_build_resolved_rules_from_configured(
            configured_rules=framework_rules,
            source=SyncRuleSource.FRAMEWORK,
            framework_type=framework_type,
        ),
    ]
    overrides_by_target = {
        override.target_rule_key: override
        for override in project_rule_overrides
        if override.target_rule_key is not None
        and not _is_gitignore_override_key(override.target_rule_key)
    }
    resolved_rules: list[ResolvedSyncRule] = []
    for rule in adapter_rules:
        target_override = overrides_by_target.get(rule.rule_key)
        resolved_rules.append(
            ResolvedSyncRule(
                rule_key=rule.rule_key,
                relative_path=rule.relative_path,
                filter_type=rule.filter_type,
                behavior=rule.behavior,
                description=rule.description,
                source=rule.source,
                is_enabled=(
                    rule.is_enabled if target_override is None else target_override.is_enabled
                ),
            )
        )
    for override in project_rule_overrides:
        if override.target_rule_key is not None:
            continue
        resolved_rules.append(
            ResolvedSyncRule(
                rule_key=override.rule_key,
                relative_path=override.relative_path,
                filter_type=override.filter_type,
                behavior=override.behavior,
                description=override.description,
                source=SyncRuleSource.PROJECT,
                is_enabled=override.is_enabled,
            )
        )
    resolved_rules.extend(
        _build_resolved_rules_from_configured(
            configured_rules=gitignore_rules,
            source=SyncRuleSource.GITIGNORE,
        )
    )
    return tuple(resolved_rules)


def _build_resolved_rules(
    *,
    filter_specs: tuple[SyncFilterSpec, ...],
    behavior: SyncRuleBehavior,
    source: SyncRuleSource,
) -> list[ResolvedSyncRule]:
    """Build resolved rules.

    Args:
        filter_specs (tuple[SyncFilterSpec, ...]): Value supplied to this callable.
        behavior (SyncRuleBehavior): Value supplied to this callable.
        source (SyncRuleSource): Value supplied to this callable.

    Returns:
        list[ResolvedSyncRule]: Structured value returned by this callable.
    """
    return [
        ResolvedSyncRule(
            rule_key=build_sync_rule_key(
                relative_path=filter_spec.relative_path,
                filter_type=filter_spec.filter_type,
                behavior=behavior,
            ),
            relative_path=filter_spec.relative_path,
            filter_type=filter_spec.filter_type,
            behavior=behavior,
            description=filter_spec.description,
            source=source,
            is_enabled=True,
        )
        for filter_spec in filter_specs
    ]


def _build_resolved_rules_from_configured(
    *,
    configured_rules: tuple[ConfiguredSyncRule, ...],
    source: SyncRuleSource,
    framework_type: str | None = None,
) -> list[ResolvedSyncRule]:
    """Build resolved rules from configured.

    Args:
        configured_rules (tuple[ConfiguredSyncRule, ...]): Value supplied to this callable.
        source (SyncRuleSource): Value supplied to this callable.
        framework_type (str | None): Value supplied to this callable.

    Returns:
        list[ResolvedSyncRule]: Structured value returned by this callable.
    """
    resolved_rules: list[ResolvedSyncRule] = []
    for configured_rule in configured_rules:
        rule_key = _build_configured_rule_key(
            configured_rule=configured_rule,
            source=source,
            framework_type=framework_type,
        )
        resolved_rules.append(
            ResolvedSyncRule(
                rule_key=rule_key,
                relative_path=configured_rule.relative_path,
                filter_type=configured_rule.filter_type,
                behavior=configured_rule.behavior,
                description=configured_rule.description,
                source=source,
                is_enabled=configured_rule.is_enabled,
            )
        )
    return resolved_rules


def _build_configured_rule_key(
    configured_rule: ConfiguredSyncRule,
    *,
    source: SyncRuleSource,
    framework_type: str | None = None,
) -> str:
    """Build configured rule key.

    Args:
        configured_rule (ConfiguredSyncRule): Value supplied to this callable.
        source (SyncRuleSource): Value supplied to this callable.
        framework_type (str | None): Value supplied to this callable.

    Returns:
        str: Structured value returned by this callable.

    Raises:
        ValueError: Raised when this callable hits the corresponding error path.
    """
    if source is SyncRuleSource.GLOBAL:
        return build_global_sync_rule_key(
            relative_path=configured_rule.relative_path,
            filter_type=configured_rule.filter_type,
            behavior=configured_rule.behavior,
        )
    if source is SyncRuleSource.GITIGNORE:
        return build_gitignore_sync_rule_key(pattern=configured_rule.relative_path)
    if source is SyncRuleSource.FRAMEWORK:
        if framework_type is None:
            msg = "Framework-configured rules require a framework type."
            raise ValueError(msg)
        return build_framework_sync_rule_key(
            framework_type=framework_type,
            relative_path=configured_rule.relative_path,
            filter_type=configured_rule.filter_type,
            behavior=configured_rule.behavior,
        )
    msg = f"Unsupported configured sync rule source: {source.value}"
    raise ValueError(msg)


def _load_gitignore_rules(
    *,
    sync_scope_settings: AdapterSyncScopeSettings,
    project_path: Path,
    gitignore_rule_loader: Callable[[Path], tuple[ConfiguredSyncRule, ...]],
) -> tuple[ConfiguredSyncRule, ...]:
    """Load gitignore rules.

    Args:
        sync_scope_settings (AdapterSyncScopeSettings): Value supplied to this callable.
        project_path (Path): Value supplied to this callable.
        gitignore_rule_loader (Callable[[Path], tuple[ConfiguredSyncRule, ...]]): Value supplied to
    this
        callable.

    Returns:
        tuple[ConfiguredSyncRule, ...]: Structured value returned by this callable.
    """
    if not sync_scope_settings.use_gitignore_rules:
        return ()
    return gitignore_rule_loader(project_path)


def _is_gitignore_override_key(rule_key: str) -> bool:
    """Handle is gitignore override key.

    Args:
        rule_key (str): Value supplied to this callable.

    Returns:
        bool: Structured value returned by this callable.
    """
    return rule_key.startswith(f"{SyncRuleSource.GITIGNORE.value}:")


class SyncScopeResolutionService(FrameworkSyncScopeService):
    """Alias for the sync scope composition service.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """
