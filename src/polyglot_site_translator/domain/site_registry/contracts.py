"""Contracts for site registry persistence."""

from __future__ import annotations

from typing import Protocol

from polyglot_site_translator.domain.site_registry.models import RegisteredSite


class SiteRegistryRepository(Protocol):
    """Persistence contract for site registry records."""

    def create_site(self, site: RegisteredSite) -> RegisteredSite:
        """Persist a new site and return the saved record."""

    def list_sites(self) -> list[RegisteredSite]:
        """Return all persisted site records."""

    def get_site(self, site_id: str) -> RegisteredSite:
        """Return a single persisted site record by identifier."""

    def update_site(self, site: RegisteredSite) -> RegisteredSite:
        """Persist modifications for an existing site."""

    def delete_site(self, site_id: str) -> None:
        """Delete a persisted site record."""
