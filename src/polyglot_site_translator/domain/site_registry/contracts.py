"""Contracts for site registry persistence."""

from __future__ import annotations

from typing import Protocol

from polyglot_site_translator.domain.site_registry.models import RegisteredSite


class SiteRegistryRepository(Protocol):
    """Persistence contract for site registry records.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    def create_site(self, site: RegisteredSite) -> RegisteredSite:
        """Persist a new site and return the saved record.

        Args:
            self:
                Value supplied to this callable.
            site:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def list_sites(self) -> list[RegisteredSite]:
        """Return all persisted site records.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def get_site(self, site_id: str) -> RegisteredSite:
        """Return a single persisted site record by identifier.

        Args:
            self:
                Value supplied to this callable.
            site_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def update_site(self, site: RegisteredSite) -> RegisteredSite:
        """Persist modifications for an existing site.

        Args:
            self:
                Value supplied to this callable.
            site:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def delete_site(self, site_id: str) -> None:
        """Delete a persisted site record.

        Args:
            self:
                Value supplied to this callable.
            site_id:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
