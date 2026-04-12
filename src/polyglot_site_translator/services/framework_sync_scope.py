"""Application service for adapter-driven sync scope resolution."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScope,
    ProjectSyncRuleOverride,
    ResolvedSyncRule,
    ResolvedSyncScope,
    SyncFilterSpec,
    SyncRuleBehavior,
    SyncRuleSource,
    SyncScopeStatus,
    build_sync_rule_key,
)

UNKNOWN_FRAMEWORK_TYPE = "unknown"


class FrameworkSyncScopeService:
    """Resolve framework-defined sync filters for registered sites."""

    def __init__(self, *, registry: FrameworkAdapterRegistry) -> None:
        self._registry = registry

    def resolve_for_site(self, site: RegisteredSite) -> ResolvedSyncScope:
        """Resolve the sync scope for a persisted site."""
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
        """Resolve the sync scope for a framework type and project path."""
        normalized_framework_type = framework_type.strip().lower()
        project_only_rules = _resolve_scope_rules(
            adapter_scope=AdapterSyncScope(),
            project_rule_overrides=project_rule_overrides,
        )
        if normalized_framework_type in {"", UNKNOWN_FRAMEWORK_TYPE}:
            if project_only_rules != ():
                return _build_scope_from_rules(
                    framework_type=normalized_framework_type or UNKNOWN_FRAMEWORK_TYPE,
                    adapter_name=None,
                    resolved_rules=project_only_rules,
                    no_rules_status=SyncScopeStatus.FRAMEWORK_UNRESOLVED,
                    no_rules_message=(
                        "The project does not expose a supported framework type and "
                        "no project-specific sync rules are active."
                    ),
                    active_rules_message=(
                        "Framework type is unresolved; using active project-specific "
                        "sync rules only."
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
            if project_only_rules != ():
                return _build_scope_from_rules(
                    framework_type=normalized_framework_type,
                    adapter_name=None,
                    resolved_rules=project_only_rules,
                    no_rules_status=SyncScopeStatus.ADAPTER_UNAVAILABLE,
                    no_rules_message=(
                        "No installed framework adapter can provide sync filters for "
                        f"'{normalized_framework_type}' and no project-specific sync "
                        "rules are active."
                    ),
                    active_rules_message=(
                        "No installed framework adapter is available; using active "
                        "project-specific sync rules only."
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
        resolved_rules = _resolve_scope_rules(
            adapter_scope=adapter.get_sync_scope(Path(project_path)),
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


def _build_scope_from_rules(  # noqa: PLR0913
    *,
    framework_type: str,
    adapter_name: str | None,
    resolved_rules: tuple[ResolvedSyncRule, ...],
    no_rules_status: SyncScopeStatus,
    no_rules_message: str,
    active_rules_message: str,
) -> ResolvedSyncScope:
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


def _resolve_scope_rules(
    *,
    adapter_scope: AdapterSyncScope,
    project_rule_overrides: tuple[ProjectSyncRuleOverride, ...],
) -> tuple[ResolvedSyncRule, ...]:
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
    ]
    overrides_by_target = {
        override.target_rule_key: override
        for override in project_rule_overrides
        if override.target_rule_key is not None
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
    return tuple(resolved_rules)


def _build_resolved_rules(
    *,
    filter_specs: tuple[SyncFilterSpec, ...],
    behavior: SyncRuleBehavior,
    source: SyncRuleSource,
) -> list[ResolvedSyncRule]:
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
