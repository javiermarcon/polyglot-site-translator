"""Unit tests for the WordPress framework adapter."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.adapters.wordpress import WordPressFrameworkAdapter
from polyglot_site_translator.domain.sync.scope import SyncFilterType


def test_wordpress_adapter_detects_a_typical_wordpress_layout(tmp_path: Path) -> None:
    (tmp_path / "wp-config.php").write_text("<?php\n", encoding="utf-8")
    (tmp_path / "wp-content").mkdir()
    (tmp_path / "wp-includes").mkdir()

    result = WordPressFrameworkAdapter().detect(tmp_path)

    assert result.matched is True
    assert result.framework_type == "wordpress"
    assert any("wp-config.php" in evidence for evidence in result.evidence)
    assert str(tmp_path / "wp-config.php") in result.config_files


def test_wordpress_adapter_returns_unmatched_for_generic_projects(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()

    result = WordPressFrameworkAdapter().detect(tmp_path)

    assert result.matched is False
    assert result.framework_type == "unknown"


def test_wordpress_adapter_reports_partial_evidence_without_matching(tmp_path: Path) -> None:
    (tmp_path / "wp-content").mkdir()

    result = WordPressFrameworkAdapter().detect(tmp_path)

    assert result.matched is False
    assert result.warnings != []
    assert any("partial" in warning.lower() for warning in result.warnings)


def test_wordpress_adapter_includes_wp_admin_when_present(tmp_path: Path) -> None:
    (tmp_path / "wp-content").mkdir()
    (tmp_path / "wp-includes").mkdir()
    (tmp_path / "wp-admin").mkdir()

    result = WordPressFrameworkAdapter().detect(tmp_path)

    assert result.matched is True
    assert str(tmp_path / "wp-admin") in result.relevant_paths


def test_wordpress_adapter_exposes_sync_filters() -> None:
    filters = WordPressFrameworkAdapter().get_sync_filters(Path("/workspace/site"))

    assert [sync_filter.relative_path for sync_filter in filters] == [
        "wp-content/languages",
        "wp-content/themes",
        "wp-content/plugins",
    ]
    assert all(sync_filter.filter_type is SyncFilterType.DIRECTORY for sync_filter in filters)
