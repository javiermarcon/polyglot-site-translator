"""Contracts for site registry persistence."""

from __future__ import annotations

from typing import Protocol

from polyglot_site_translator.domain.site_registry.models import RegisteredSite


class SiteRegistryRepository(Protocol):
    """Persistence contract for site registry records.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def create_site(self, site: RegisteredSite) -> RegisteredSite:
        """Persist a new site and return the saved record.

        Args:
            site (RegisteredSite): Value supplied to this callable.

        Returns:
            RegisteredSite: Structured value returned by this callable.
        """

    def list_sites(self) -> list[RegisteredSite]:
        """Return all persisted site records.

        Returns:
            list[RegisteredSite]: Structured value returned by this callable.
        """

    def get_site(self, site_id: str) -> RegisteredSite:
        """Return a single persisted site record by identifier.

        Args:
            site_id (str): Value supplied to this callable.

        Returns:
            RegisteredSite: Structured value returned by this callable.
        """

    def update_site(self, site: RegisteredSite) -> RegisteredSite:
        """Persist modifications for an existing site.

        Args:
            site (RegisteredSite): Value supplied to this callable.

        Returns:
            RegisteredSite: Structured value returned by this callable.
        """

    def delete_site(self, site_id: str) -> None:
        """Delete a persisted site record.

        Args:
            site_id (str): Value supplied to this callable.

        Returns:
            None: This callable does not return a value.
        """
