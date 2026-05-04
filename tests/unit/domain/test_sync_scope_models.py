"""Unit tests for typed sync scope models."""

from __future__ import annotations

from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScope,
    AdapterSyncScopeSettings,
    ConfiguredSyncRule,
    FrameworkSyncRuleSet,
    ProjectSyncRuleOverride,
    ResolvedSyncRule,
    ResolvedSyncScope,
    SyncFilterSpec,
    SyncFilterType,
    SyncRuleBehavior,
    SyncRuleSource,
    SyncScopeStatus,
    build_default_sync_scope_settings,
    build_framework_sync_rule_key,
    build_gitignore_sync_rule_key,
    build_global_sync_rule_key,
    build_sync_rule_key,
)


def test_sync_filter_spec_matches_directory_prefixes() -> None:
    filter_spec = SyncFilterSpec(
        relative_path="locale",
        filter_type=SyncFilterType.DIRECTORY,
        description="Django locale catalogs.",
    )

    assert filter_spec.matches("locale/es/LC_MESSAGES/django.po") is True
    assert filter_spec.matches("locale") is True
    assert filter_spec.matches("templates/base.html") is False


def test_sync_filter_spec_matches_exact_files() -> None:
    filter_spec = SyncFilterSpec(
        relative_path="babel.cfg",
        filter_type=SyncFilterType.FILE,
        description="Flask Babel configuration.",
    )

    assert filter_spec.matches("babel.cfg") is True
    assert filter_spec.matches("translations/es/messages.po") is False


def test_resolved_sync_scope_requires_no_filters_when_unresolved() -> None:
    scope = ResolvedSyncScope(
        framework_type="unknown",
        adapter_name=None,
        status=SyncScopeStatus.FRAMEWORK_UNRESOLVED,
        filters=(),
        message="The project does not expose a supported framework type.",
    )

    assert scope.is_filtered is False
    assert scope.includes("any/path.txt") is True


def test_resolved_sync_scope_applies_exclusions_after_inclusions() -> None:
    scope = ResolvedSyncScope(
        framework_type="django",
        adapter_name="django_adapter",
        status=SyncScopeStatus.FILTERED,
        filters=(
            SyncFilterSpec(
                relative_path="locale",
                filter_type=SyncFilterType.DIRECTORY,
                description="Django locale catalogs.",
            ),
        ),
        excludes=(
            SyncFilterSpec(
                relative_path="locale/__pycache__",
                filter_type=SyncFilterType.DIRECTORY,
                description="Python bytecode cache.",
            ),
        ),
        message="Resolved Django sync scope.",
    )

    assert scope.includes("locale/es/LC_MESSAGES/django.po") is True
    assert scope.includes("locale/__pycache__/messages.cpython-312.pyc") is False
    assert scope.catalog_rules == ()


def test_resolved_sync_scope_uses_only_exclusions_when_not_filtered() -> None:
    scope = ResolvedSyncScope(
        framework_type="django",
        adapter_name="django_adapter",
        status=SyncScopeStatus.NO_FILTERS,
        filters=(),
        excludes=(
            SyncFilterSpec(
                relative_path=".venv",
                filter_type=SyncFilterType.DIRECTORY,
                description="Virtual environment.",
            ),
        ),
        message="Resolved only exclusions.",
    )

    assert scope.includes("locale/es/LC_MESSAGES/django.po") is True
    assert scope.includes(".venv/lib/python3.12/site.py") is False


def test_sync_filter_spec_matches_glob_patterns() -> None:
    filter_spec = SyncFilterSpec(
        relative_path="*.pyc",
        filter_type=SyncFilterType.GLOB,
        description="Python bytecode files.",
    )

    assert filter_spec.matches("locale/__pycache__/settings.cpython-312.pyc") is True
    assert filter_spec.matches("locale/es/LC_MESSAGES/django.po") is False


def test_resolved_sync_rule_as_filter_spec_and_glob_helpers_cover_basename_and_segments() -> None:
    filter_from_rule = ConfiguredSyncRule(
        relative_path="locale",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.INCLUDE,
        description="Locale dir.",
        is_enabled=True,
    )
    glob_basename = SyncFilterSpec(
        relative_path="?essages.po",
        filter_type=SyncFilterType.GLOB,
        description="PO basenames.",
    )
    glob_segment = SyncFilterSpec(
        relative_path="cache*",
        filter_type=SyncFilterType.GLOB,
        description="Cache segments.",
    )

    resolved_rule = ResolvedSyncRule(
        rule_key="project:locale",
        relative_path=filter_from_rule.relative_path,
        filter_type=filter_from_rule.filter_type,
        behavior=filter_from_rule.behavior,
        description=filter_from_rule.description,
        source=SyncRuleSource.PROJECT,
        is_enabled=filter_from_rule.is_enabled,
    )

    assert resolved_rule.as_filter_spec() == SyncFilterSpec(
        relative_path="locale",
        filter_type=SyncFilterType.DIRECTORY,
        description="Locale dir.",
    )
    assert glob_basename.matches("nested/messages.po") is True
    assert glob_segment.matches("var/cache123/messages.txt") is True


def test_default_sync_scope_settings_include_global_git_exclusion() -> None:
    settings = build_default_sync_scope_settings()

    assert settings.use_gitignore_rules is False
    assert settings.global_rules == (
        ConfiguredSyncRule(
            relative_path=".git",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.EXCLUDE,
            description="Ignore Git metadata directories.",
            is_enabled=True,
        ),
    )


def test_adapter_sync_scope_settings_returns_rules_for_requested_framework() -> None:
    settings = AdapterSyncScopeSettings(
        global_rules=(),
        framework_rule_sets=(
            FrameworkSyncRuleSet(
                framework_type="django",
                rules=(
                    ConfiguredSyncRule(
                        relative_path=".venv",
                        filter_type=SyncFilterType.DIRECTORY,
                        behavior=SyncRuleBehavior.EXCLUDE,
                        description="Ignore virtualenv.",
                        is_enabled=True,
                    ),
                ),
            ),
        ),
        use_gitignore_rules=False,
    )

    assert settings.rules_for_framework("django")[0].relative_path == ".venv"
    assert settings.rules_for_framework("flask") == ()


def test_adapter_sync_scope_and_project_override_helpers_cover_simple_properties() -> None:
    empty_scope = AdapterSyncScope()
    non_empty_scope = AdapterSyncScope(
        filters=(
            SyncFilterSpec(
                relative_path="locale",
                filter_type=SyncFilterType.DIRECTORY,
                description="Locale catalogs.",
            ),
        )
    )
    custom_override = ProjectSyncRuleOverride(
        rule_key="project:locale",
        relative_path="locale",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.INCLUDE,
        is_enabled=True,
        description="Custom locale rule",
        target_rule_key=None,
    )
    targeted_override = ProjectSyncRuleOverride(
        rule_key="project:cache",
        relative_path="cache",
        filter_type=SyncFilterType.DIRECTORY,
        behavior=SyncRuleBehavior.EXCLUDE,
        is_enabled=False,
        description="Disable cache rule",
        target_rule_key="adapter:cache",
    )

    assert empty_scope.is_empty is True
    assert non_empty_scope.is_empty is False
    assert custom_override.is_custom is True
    assert targeted_override.is_custom is False


def test_sync_rule_key_builders_normalize_paths_and_framework_names() -> None:
    assert (
        build_sync_rule_key(
            relative_path="/locale/",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.INCLUDE,
        )
        == "include:directory:locale"
    )
    assert (
        build_global_sync_rule_key(
            relative_path="/cache/",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.EXCLUDE,
        )
        == "global:exclude:directory:cache"
    )
    assert (
        build_framework_sync_rule_key(
            framework_type=" Django ",
            relative_path="/locale/",
            filter_type=SyncFilterType.DIRECTORY,
            behavior=SyncRuleBehavior.INCLUDE,
        )
        == "framework:django:include:directory:locale"
    )
    assert build_gitignore_sync_rule_key(pattern=" *.pyc ") == "gitignore:*.pyc"


def test_sync_filter_glob_matching_covers_segment_and_suffix_paths() -> None:
    bare_pattern = SyncFilterSpec(
        relative_path="cache",
        filter_type=SyncFilterType.GLOB,
        description="Cache segments.",
    )
    suffix_pattern = SyncFilterSpec(
        relative_path="locale/*.po",
        filter_type=SyncFilterType.GLOB,
        description="PO files under locale.",
    )

    assert bare_pattern.matches("var/cache/messages.txt") is True
    assert suffix_pattern.matches("nested/locale/messages.po") is True
