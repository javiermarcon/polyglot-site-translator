"""Unit tests for framework adapter sync scope resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.adapters.wordpress import WordPressFrameworkAdapter
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScope,
    SyncFilterSpec,
    SyncScopeStatus,
)
from polyglot_site_translator.services.framework_sync_scope import (
    FrameworkSyncScopeService,
)


@dataclass(frozen=True)
class _NoFilterAdapter:
    framework_type: str = "nofilter"
    adapter_name: str = "no_filter_adapter"
    display_name: str = "NoFilter"

    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        return FrameworkDetectionResult.unmatched(project_path=str(project_path))

    def get_sync_scope(self, project_path: Path) -> AdapterSyncScope:
        return AdapterSyncScope()

    def get_sync_filters(self, project_path: Path) -> tuple[SyncFilterSpec, ...]:
        return ()


def test_framework_sync_scope_service_resolves_wordpress_filters(tmp_path: Path) -> None:
    service = FrameworkSyncScopeService(registry=FrameworkAdapterRegistry.discover_installed())

    resolved_scope = service.resolve_for_site(_build_site(tmp_path, framework_type="wordpress"))

    assert resolved_scope.status is SyncScopeStatus.FILTERED
    assert [sync_filter.relative_path for sync_filter in resolved_scope.filters] == [
        "wp-content/languages",
        "wp-content/themes",
        "wp-content/plugins",
    ]
    assert resolved_scope.excludes == ()


def test_framework_sync_scope_service_returns_adapter_unavailable_when_missing(
    tmp_path: Path,
) -> None:
    service = FrameworkSyncScopeService(registry=FrameworkAdapterRegistry.discover_installed())

    resolved_scope = service.resolve_for_site(_build_site(tmp_path, framework_type="customapp"))

    assert resolved_scope.status is SyncScopeStatus.ADAPTER_UNAVAILABLE
    assert resolved_scope.filters == ()


def test_framework_sync_scope_service_returns_framework_unresolved_for_unknown_framework(
    tmp_path: Path,
) -> None:
    service = FrameworkSyncScopeService(registry=FrameworkAdapterRegistry.discover_installed())

    resolved_scope = service.resolve_for_site(_build_site(tmp_path, framework_type="unknown"))

    assert resolved_scope.status is SyncScopeStatus.FRAMEWORK_UNRESOLVED
    assert resolved_scope.filters == ()


def test_framework_sync_scope_service_returns_explicit_no_filters_when_adapter_defines_none(
    tmp_path: Path,
) -> None:
    service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.default_registry(
            adapters=[_NoFilterAdapter(), WordPressFrameworkAdapter()]
        )
    )

    resolved_scope = service.resolve_for_site(_build_site(tmp_path, framework_type="nofilter"))

    assert resolved_scope.status is SyncScopeStatus.NO_FILTERS
    assert resolved_scope.filters == ()


def test_framework_sync_scope_service_resolves_from_an_explicit_project_path(
    tmp_path: Path,
) -> None:
    service = FrameworkSyncScopeService(registry=FrameworkAdapterRegistry.discover_installed())
    project_path = tmp_path / "flask-site"
    project_path.mkdir()

    resolved_scope = service.resolve_for_framework(
        framework_type="flask",
        project_path=project_path,
    )

    assert resolved_scope.status is SyncScopeStatus.FILTERED
    assert resolved_scope.includes("translations/es/LC_MESSAGES/messages.po") is True
    assert resolved_scope.includes("templates/base.html") is False


def test_framework_sync_scope_service_resolves_django_exclusions(tmp_path: Path) -> None:
    service = FrameworkSyncScopeService(registry=FrameworkAdapterRegistry.discover_installed())

    resolved_scope = service.resolve_for_site(_build_site(tmp_path, framework_type="django"))

    assert resolved_scope.status is SyncScopeStatus.FILTERED
    assert ".venv" in [sync_filter.relative_path for sync_filter in resolved_scope.excludes]
    assert "__pycache__" in [sync_filter.relative_path for sync_filter in resolved_scope.excludes]
    assert resolved_scope.includes("locale/es/LC_MESSAGES/django.po") is True
    assert resolved_scope.includes(".venv/lib/python3.12/site.py") is False
    assert resolved_scope.includes("__pycache__/settings.cpython-312.pyc") is False


def _build_site(tmp_path: Path, *, framework_type: str) -> RegisteredSite:
    local_root = tmp_path / framework_type
    local_root.mkdir(exist_ok=True)
    return RegisteredSite(
        project=SiteProject(
            id=f"{framework_type}-site",
            name=f"{framework_type}-site",
            framework_type=framework_type,
            local_path=str(local_root),
            default_locale="en",
            is_active=True,
        ),
        remote_connection=None,
    )
