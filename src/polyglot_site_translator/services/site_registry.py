"""Application service for the site registry use cases."""

from __future__ import annotations

from uuid import uuid4

from polyglot_site_translator.domain.site_registry.contracts import SiteRegistryRepository
from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryValidationError,
)
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteRegistrationInput,
)


class SiteRegistryService:
    """Orchestrate site registry validation and CRUD workflows."""

    def __init__(self, repository: SiteRegistryRepository) -> None:
        self._repository = repository

    def create_site(self, registration: SiteRegistrationInput) -> RegisteredSite:
        """Validate and create a new site registry record."""
        validated_site = RegisteredSite(
            id=f"site-{uuid4().hex}",
            name=_require_text(registration.name, "Site name"),
            framework_type=_require_text(registration.framework_type, "Framework type"),
            local_path=_require_text(registration.local_path, "Local path"),
            default_locale=_require_text(registration.default_locale, "Default locale"),
            ftp_host=_require_text(registration.ftp_host, "FTP host"),
            ftp_port=_require_port(registration.ftp_port),
            ftp_username=_require_text(registration.ftp_username, "FTP username"),
            ftp_password=_require_text(registration.ftp_password, "FTP password"),
            ftp_remote_path=_require_text(registration.ftp_remote_path, "FTP remote path"),
            is_active=registration.is_active,
        )
        return self._repository.create_site(validated_site)

    def list_sites(self) -> list[RegisteredSite]:
        """Return persisted site registry records."""
        return self._repository.list_sites()

    def get_site(self, site_id: str) -> RegisteredSite:
        """Return a persisted site registry record."""
        return self._repository.get_site(site_id)

    def update_site(
        self,
        *,
        site_id: str,
        registration: SiteRegistrationInput,
    ) -> RegisteredSite:
        """Validate and update an existing site registry record."""
        existing_site = self._repository.get_site(site_id)
        validated_site = RegisteredSite(
            id=existing_site.id,
            name=_require_text(registration.name, "Site name"),
            framework_type=_require_text(registration.framework_type, "Framework type"),
            local_path=_require_text(registration.local_path, "Local path"),
            default_locale=_require_text(registration.default_locale, "Default locale"),
            ftp_host=_require_text(registration.ftp_host, "FTP host"),
            ftp_port=_require_port(registration.ftp_port),
            ftp_username=_require_text(registration.ftp_username, "FTP username"),
            ftp_password=_require_text(registration.ftp_password, "FTP password"),
            ftp_remote_path=_require_text(registration.ftp_remote_path, "FTP remote path"),
            is_active=registration.is_active,
        )
        return self._repository.update_site(validated_site)

    def delete_site(self, site_id: str) -> None:
        """Delete a persisted site registry record."""
        self._repository.delete_site(site_id)


def _require_text(value: str, label: str) -> str:
    normalized_value = value.strip()
    if normalized_value:
        return normalized_value
    msg = f"{label} must not be empty."
    raise SiteRegistryValidationError(msg)


def _require_port(ftp_port: int) -> int:
    if ftp_port > 0:
        return ftp_port
    msg = "FTP port must be a positive integer."
    raise SiteRegistryValidationError(msg)
