"""Tests for fake service contracts used by the Kivy frontend."""

from __future__ import annotations

from polyglot_site_translator.presentation.contracts import ProjectCatalogService
from tests.support.frontend_doubles import build_empty_services, build_seeded_services


def test_seeded_catalog_matches_ui_contract() -> None:
    """Verify seeded catalog matches ui contract.

    Returns:
        value:
            Structured value returned by this callable.
    """
    services = build_seeded_services()

    catalog: ProjectCatalogService = services.catalog
    projects = catalog.list_projects()
    detail = catalog.get_project_detail("wp-site")

    assert len(projects) == 2
    assert detail.project.id == "wp-site"
    assert detail.project.framework == "WordPress"


def test_empty_catalog_returns_no_projects() -> None:
    """Verify empty catalog returns no projects.

    Returns:
        value:
            Structured value returned by this callable.
    """
    services = build_empty_services()

    assert services.catalog.list_projects() == []
