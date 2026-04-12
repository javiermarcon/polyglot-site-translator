"""Application service for adapter-driven sync scope resolution."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.domain.site_registry.models import RegisteredSite
from polyglot_site_translator.domain.sync.scope import (
    ResolvedSyncScope,
    SyncScopeStatus,
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
        )

    def resolve_for_framework(
        self,
        *,
        framework_type: str,
        project_path: Path | str,
    ) -> ResolvedSyncScope:
        """Resolve the sync scope for a framework type and project path."""
        normalized_framework_type = framework_type.strip().lower()
        if normalized_framework_type in {"", UNKNOWN_FRAMEWORK_TYPE}:
            return ResolvedSyncScope(
                framework_type=normalized_framework_type or UNKNOWN_FRAMEWORK_TYPE,
                adapter_name=None,
                status=SyncScopeStatus.FRAMEWORK_UNRESOLVED,
                filters=(),
                excludes=(),
                message="The project does not expose a supported framework type.",
            )
        adapter = self._registry.find_adapter(normalized_framework_type)
        if adapter is None:
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
            )
        sync_scope = adapter.get_sync_scope(Path(project_path))
        if sync_scope.is_empty:
            return ResolvedSyncScope(
                framework_type=normalized_framework_type,
                adapter_name=adapter.adapter_name,
                status=SyncScopeStatus.NO_FILTERS,
                filters=(),
                excludes=(),
                message=(
                    f"The adapter '{adapter.adapter_name}' does not define sync include or "
                    "exclude rules for this framework."
                ),
            )
        return ResolvedSyncScope(
            framework_type=normalized_framework_type,
            adapter_name=adapter.adapter_name,
            status=(
                SyncScopeStatus.FILTERED if sync_scope.filters != () else SyncScopeStatus.NO_FILTERS
            ),
            filters=sync_scope.filters,
            excludes=sync_scope.excludes,
            message=(
                "Resolved "
                f"{len(sync_scope.filters)} include filters and "
                f"{len(sync_scope.excludes)} exclusions from adapter "
                f"'{adapter.adapter_name}'."
            ),
        )
