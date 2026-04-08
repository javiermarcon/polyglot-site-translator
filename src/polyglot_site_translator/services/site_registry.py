"""Application service for the site registry use cases."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDescriptor,
    FrameworkDetectionResult,
    unknown_framework_descriptor,
)
from polyglot_site_translator.domain.site_registry.contracts import SiteRegistryRepository
from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryValidationError,
)
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteRegistrationInput,
)
from polyglot_site_translator.services.framework_detection import FrameworkDetectionService


class SiteRegistryService:
    """Orchestrate site registry validation and CRUD workflows."""

    def __init__(
        self,
        repository: SiteRegistryRepository,
        framework_detection_service: FrameworkDetectionService | None = None,
    ) -> None:
        self._repository = repository
        self._framework_detection_service = framework_detection_service

    def create_site(self, registration: SiteRegistrationInput) -> RegisteredSite:
        """Validate and create a new site registry record."""
        framework_type = _resolve_framework_type(
            registration=registration,
            framework_detection_service=self._framework_detection_service,
        )
        validated_site = RegisteredSite(
            id=f"site-{uuid4().hex}",
            name=_require_text(registration.name, "Site name"),
            framework_type=framework_type,
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
        framework_type = _resolve_framework_type(
            registration=registration,
            framework_detection_service=self._framework_detection_service,
        )
        validated_site = RegisteredSite(
            id=existing_site.id,
            name=_require_text(registration.name, "Site name"),
            framework_type=framework_type,
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

    def detect_framework(self, project_path: str) -> FrameworkDetectionResult:
        """Return the current framework detection result for a local path."""
        if self._framework_detection_service is None:
            return FrameworkDetectionResult.unmatched(
                project_path=project_path,
                warnings=["Framework detection is not configured."],
            )
        return self._framework_detection_service.detect_project(Path(project_path))

    def list_supported_frameworks(self) -> list[FrameworkDescriptor]:
        """Return framework metadata from the configured detection service."""
        if self._framework_detection_service is None:
            return [unknown_framework_descriptor()]
        return self._framework_detection_service.list_supported_frameworks()


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


def _resolve_framework_type(
    *,
    registration: SiteRegistrationInput,
    framework_detection_service: FrameworkDetectionService | None,
) -> str:
    provided_framework_type = _require_text(registration.framework_type, "Framework type")
    if framework_detection_service is None:
        return provided_framework_type
    detected = framework_detection_service.detect_project(registration.local_path)
    if detected.matched:
        return detected.framework_type
    return provided_framework_type
