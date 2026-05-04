"""Unit tests for framework adapter sync scope resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.adapters.wordpress import WordPressFrameworkAdapter
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.domain.sync.errors import (
    SyncConfigurationError,
    SyncScopePersistenceError,
)
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScope,
    AdapterSyncScopeSettings,
    ConfiguredSyncRule,
    FrameworkSyncRuleSet,
    ProjectSyncRuleOverride,
    SyncFilterSpec,
    SyncFilterType,
    SyncRuleBehavior,
    SyncRuleSource,
    SyncScopeStatus,
    build_sync_rule_key,
)
from polyglot_site_translator.services.framework_sync_scope import (
    FrameworkSyncScopeService,
    _build_configured_rule_key,
    _is_gitignore_override_key,
    _resolve_scope_rules,
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


def test_framework_sync_scope_service_uses_project_rules_when_no_adapter_exists(
    tmp_path: Path,
) -> None:
    service = FrameworkSyncScopeService(registry=FrameworkAdapterRegistry.discover_installed())

    resolved_scope = service.resolve_for_framework(
        framework_type="customapp",
        project_path=tmp_path / "customapp",
        project_rule_overrides=(
            ProjectSyncRuleOverride(
                rule_key=build_sync_rule_key(
                    relative_path="locale_custom",
                    filter_type=SyncFilterType.DIRECTORY,
                    behavior=SyncRuleBehavior.INCLUDE,
                ),
                target_rule_key=None,
                relative_path="locale_custom",
                filter_type=SyncFilterType.DIRECTORY,
                behavior=SyncRuleBehavior.INCLUDE,
                is_enabled=True,
                description="Project locale override",
            ),
        ),
    )

    assert resolved_scope.status is SyncScopeStatus.FILTERED
    assert resolved_scope.includes("locale_custom/es/messages.po") is True


def test_framework_sync_scope_service_applies_global_settings_rules(tmp_path: Path) -> None:
    service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.discover_installed(),
        sync_scope_settings_provider=lambda: AdapterSyncScopeSettings(
            global_rules=(
                ConfiguredSyncRule(
                    relative_path=".git",
                    filter_type=SyncFilterType.DIRECTORY,
                    behavior=SyncRuleBehavior.EXCLUDE,
                    description="Ignore Git metadata.",
                    is_enabled=True,
                ),
            ),
            framework_rule_sets=(),
            use_gitignore_rules=False,
        ),
    )

    resolved_scope = service.resolve_for_site(_build_site(tmp_path, framework_type="wordpress"))

    assert resolved_scope.includes(".git/HEAD") is False


def test_framework_sync_scope_service_applies_framework_settings_rules(tmp_path: Path) -> None:
    service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.discover_installed(),
        sync_scope_settings_provider=lambda: AdapterSyncScopeSettings(
            global_rules=(),
            framework_rule_sets=(
                FrameworkSyncRuleSet(
                    framework_type="django",
                    rules=(
                        ConfiguredSyncRule(
                            relative_path=".ruff_cache",
                            filter_type=SyncFilterType.DIRECTORY,
                            behavior=SyncRuleBehavior.EXCLUDE,
                            description="Ignore Ruff cache.",
                            is_enabled=True,
                        ),
                    ),
                ),
            ),
            use_gitignore_rules=False,
        ),
    )

    resolved_scope = service.resolve_for_site(_build_site(tmp_path, framework_type="django"))

    assert resolved_scope.includes(".ruff_cache/check") is False


def test_framework_sync_scope_service_applies_gitignore_rules_when_enabled(
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "django"
    local_root.mkdir()
    (local_root / ".gitignore").write_text("__snapshots__/\n*.pyc\n", encoding="utf-8")
    service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.discover_installed(),
        sync_scope_settings_provider=lambda: AdapterSyncScopeSettings(
            global_rules=(),
            framework_rule_sets=(),
            use_gitignore_rules=True,
        ),
    )

    resolved_scope = service.resolve_for_site(
        RegisteredSite(
            project=SiteProject(
                id="django-site",
                name="django-site",
                framework_type="django",
                local_path=str(local_root),
                default_locale="en",
                is_active=True,
            ),
            remote_connection=None,
        )
    )

    assert resolved_scope.includes("__snapshots__/message.txt") is False
    assert resolved_scope.includes("locale/__pycache__/settings.cpython-312.pyc") is False


def test_framework_sync_scope_service_respects_gitignore_precedence_over_project_overrides(
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "custom"
    local_root.mkdir()
    (local_root / ".gitignore").write_text("keep/\n", encoding="utf-8")
    service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.discover_installed(),
        sync_scope_settings_provider=lambda: AdapterSyncScopeSettings(
            global_rules=(),
            framework_rule_sets=(),
            use_gitignore_rules=True,
        ),
    )

    resolved_scope = service.resolve_for_framework(
        framework_type="customapp",
        project_path=local_root,
        project_rule_overrides=(
            ProjectSyncRuleOverride(
                rule_key=build_sync_rule_key(
                    relative_path="keep",
                    filter_type=SyncFilterType.DIRECTORY,
                    behavior=SyncRuleBehavior.INCLUDE,
                ),
                target_rule_key=None,
                relative_path="keep",
                filter_type=SyncFilterType.DIRECTORY,
                behavior=SyncRuleBehavior.INCLUDE,
                is_enabled=True,
                description="Project override keeps a folder.",
            ),
        ),
    )

    assert resolved_scope.includes("keep/secret.txt") is False


def test_framework_sync_scope_service_ignores_gitignore_rules_when_disabled(
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "customapp"
    local_root.mkdir()
    (local_root / ".gitignore").write_text("__snapshots__/\n", encoding="utf-8")
    service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.discover_installed(),
        sync_scope_settings_provider=lambda: AdapterSyncScopeSettings(
            global_rules=(),
            framework_rule_sets=(),
            use_gitignore_rules=False,
        ),
    )

    resolved_scope = service.resolve_for_framework(
        framework_type="customapp",
        project_path=local_root,
    )

    assert resolved_scope.includes("__snapshots__/message.txt") is True


def test_framework_sync_scope_service_wraps_adapter_scope_resolution_failures(
    tmp_path: Path,
) -> None:
    @dataclass(frozen=True)
    class _FailingAdapter:
        framework_type: str = "broken"
        adapter_name: str = "broken_adapter"
        display_name: str = "Broken"

        def detect(self, project_path: Path) -> FrameworkDetectionResult:
            return FrameworkDetectionResult.unmatched(project_path=str(project_path))

        def get_sync_scope(self, project_path: Path) -> AdapterSyncScope:
            msg = f"cannot inspect {project_path}"
            raise OSError(msg)

        def get_sync_filters(self, project_path: Path) -> tuple[SyncFilterSpec, ...]:
            del project_path
            return ()

    service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.default_registry(adapters=[_FailingAdapter()])
    )

    with pytest.raises(
        SyncConfigurationError,
        match=r"Framework adapter 'broken_adapter' failed while resolving sync scope",
    ):
        service.resolve_for_framework(
            framework_type="broken",
            project_path=tmp_path / "broken-project",
        )


def test_framework_sync_scope_service_wraps_settings_and_gitignore_loading_failures(
    tmp_path: Path,
) -> None:
    def _raise_settings_error() -> AdapterSyncScopeSettings:
        msg = "settings boom"
        raise OSError(msg)

    settings_service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.discover_installed(),
        sync_scope_settings_provider=_raise_settings_error,
    )

    with pytest.raises(
        SyncConfigurationError,
        match=r"Shared sync scope settings could not be loaded",
    ):
        settings_service.resolve_for_framework(
            framework_type="wordpress",
            project_path=tmp_path / "wp-settings",
        )

    def _raise_gitignore_error(_path: Path) -> tuple[ConfiguredSyncRule, ...]:
        msg = "gitignore boom"
        raise OSError(msg)

    gitignore_service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.discover_installed(),
        sync_scope_settings_provider=lambda: AdapterSyncScopeSettings(
            global_rules=(),
            framework_rule_sets=(),
            use_gitignore_rules=True,
        ),
        gitignore_rule_loader=_raise_gitignore_error,
    )

    with pytest.raises(
        SyncConfigurationError,
        match=r"Project gitignore sync rules could not be resolved",
    ):
        gitignore_service.resolve_for_framework(
            framework_type="wordpress",
            project_path=tmp_path / "wp-gitignore",
        )


def test_framework_sync_scope_service_reraises_sync_scope_persistence_failures(
    tmp_path: Path,
) -> None:
    def _raise_settings_persistence() -> AdapterSyncScopeSettings:
        msg = "settings persistence"
        raise SyncScopePersistenceError(msg)

    settings_service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.discover_installed(),
        sync_scope_settings_provider=_raise_settings_persistence,
    )

    with pytest.raises(SyncScopePersistenceError, match="settings persistence"):
        settings_service.resolve_for_framework(
            framework_type="wordpress",
            project_path=tmp_path / "wp-settings-persistence",
        )

    def _raise_gitignore_persistence(_path: Path) -> tuple[ConfiguredSyncRule, ...]:
        msg = "gitignore persistence"
        raise SyncScopePersistenceError(msg)

    gitignore_service = FrameworkSyncScopeService(
        registry=FrameworkAdapterRegistry.discover_installed(),
        sync_scope_settings_provider=lambda: AdapterSyncScopeSettings(
            global_rules=(),
            framework_rule_sets=(),
            use_gitignore_rules=True,
        ),
        gitignore_rule_loader=_raise_gitignore_persistence,
    )

    with pytest.raises(SyncScopePersistenceError, match="gitignore persistence"):
        gitignore_service.resolve_for_framework(
            framework_type="wordpress",
            project_path=tmp_path / "wp-gitignore-persistence",
        )


def test_framework_sync_scope_service_private_adapter_scope_errors_and_rule_key_validation(
    tmp_path: Path,
) -> None:
    service = FrameworkSyncScopeService(registry=FrameworkAdapterRegistry.discover_installed())

    with pytest.raises(
        SyncConfigurationError,
        match=r"No installed framework adapter can provide sync filters",
    ):
        service._load_adapter_scope(
            framework_type="customapp",
            adapter_name="missing_adapter",
            project_path=tmp_path / "custom",
        )

    configured_rule = ConfiguredSyncRule(
        relative_path="locale",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.INCLUDE,
        description="Locale rule",
        is_enabled=True,
    )

    with pytest.raises(ValueError, match=r"Framework-configured rules require a framework type"):
        _build_configured_rule_key(
            configured_rule,
            source=SyncRuleSource.FRAMEWORK,
        )

    with pytest.raises(ValueError, match=r"Unsupported configured sync rule source"):
        _build_configured_rule_key(
            configured_rule,
            source=cast(SyncRuleSource, SimpleNamespace(value="unsupported")),
        )


def test_framework_sync_scope_helpers_cover_override_skip_and_gitignore_key_detection() -> None:
    overrides = (
        ProjectSyncRuleOverride(
            rule_key="project:disabled-adapter",
            target_rule_key="adapter:locale",
            relative_path="locale",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.INCLUDE,
            is_enabled=False,
            description="Disable adapter rule",
        ),
        ProjectSyncRuleOverride(
            rule_key="project:gitignore-derived",
            target_rule_key="gitignore:keep",
            relative_path="keep",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.INCLUDE,
            is_enabled=True,
            description="Should be skipped as override target",
        ),
        ProjectSyncRuleOverride(
            rule_key="project:standalone",
            target_rule_key=None,
            relative_path="locale_custom",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.INCLUDE,
            is_enabled=True,
            description="Project standalone rule",
        ),
    )

    resolved = _resolve_scope_rules(
        framework_type="wordpress",
        adapter_scope=AdapterSyncScope(),
        global_rules=(),
        framework_rules=(),
        project_rule_overrides=overrides,
        gitignore_rules=(),
    )

    assert len(resolved) == 1
    assert resolved[0].is_enabled is True
    assert resolved[0].rule_key == "project:standalone"
    assert _is_gitignore_override_key("gitignore:keep") is True
    assert _is_gitignore_override_key("project:keep") is False


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
