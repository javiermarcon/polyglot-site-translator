"""Unit tests for typed sync scope models."""

from __future__ import annotations

from polyglot_site_translator.domain.sync.scope import (
    ResolvedSyncScope,
    SyncFilterSpec,
    SyncFilterType,
    SyncScopeStatus,
)


def test_sync_filter_spec_matches_directory_prefixes() -> None:
    filter_spec = SyncFilterSpec(
        relative_path="locale",
        filter_type=SyncFilterType.DIRECTORY,
        description="Django locale catalogs.",
    )

    assert filter_spec.matches("locale/es/LC_MESSAGES/django.po") is True
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
