"""Tests for fake service contracts used by the Kivy frontend."""

from __future__ import annotations

from polyglot_site_translator.presentation.contracts import ProjectCatalogService
from polyglot_site_translator.presentation.fakes import build_empty_services, build_seeded_services


def test_seeded_catalog_matches_ui_contract() -> None:
    services = build_seeded_services()

    catalog: ProjectCatalogService = services.catalog
    projects = catalog.list_projects()
    detail = catalog.get_project_detail("wp-site")

    assert len(projects) == 2
    assert detail.project.id == "wp-site"
    assert detail.project.framework == "WordPress"


def test_empty_catalog_returns_no_projects() -> None:
    services = build_empty_services()

    assert services.catalog.list_projects() == []
