"""Application service for the site registry use cases."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDescriptor,
    FrameworkDetectionResult,
    unknown_framework_descriptor,
)
from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionTestResult,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.site_registry.contracts import SiteRegistryRepository
from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryValidationError,
)
from polyglot_site_translator.domain.site_registry.locales import (
    normalize_default_locale,
)
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteProject,
    SiteRegistrationInput,
)
from polyglot_site_translator.services.framework_detection import FrameworkDetectionService
from polyglot_site_translator.services.remote_connections import RemoteConnectionService


class SiteRegistryService:
    """Orchestrate site registry validation and CRUD workflows."""

    def __init__(
        self,
        repository: SiteRegistryRepository,
        framework_detection_service: FrameworkDetectionService | None = None,
        remote_connection_service: RemoteConnectionService | None = None,
    ) -> None:
        self._repository = repository
        self._framework_detection_service = framework_detection_service
        self._remote_connection_service = remote_connection_service

    def create_site(self, registration: SiteRegistrationInput) -> RegisteredSite:
        """Validate and create a new site registry record."""
        site_id = f"site-{uuid4().hex}"
        return self._repository.create_site(
            RegisteredSite(
                project=SiteProject(
                    id=site_id,
                    name=_require_text(registration.name, "Site name"),
                    framework_type=_resolve_framework_type(
                        registration=registration,
                        framework_detection_service=self._framework_detection_service,
                    ),
                    local_path=_require_text(registration.local_path, "Local path"),
                    default_locale=normalize_default_locale(registration.default_locale),
                    compile_mo=registration.compile_mo,
                    is_active=registration.is_active,
                ),
                remote_connection=_resolve_remote_connection(
                    site_project_id=site_id,
                    registration=registration,
                    remote_connection_service=self._remote_connection_service,
                ),
            )
        )

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
        return self._repository.update_site(
            RegisteredSite(
                project=SiteProject(
                    id=existing_site.id,
                    name=_require_text(registration.name, "Site name"),
                    framework_type=_resolve_framework_type(
                        registration=registration,
                        framework_detection_service=self._framework_detection_service,
                    ),
                    local_path=_require_text(registration.local_path, "Local path"),
                    default_locale=normalize_default_locale(registration.default_locale),
                    compile_mo=registration.compile_mo,
                    is_active=registration.is_active,
                ),
                remote_connection=_resolve_remote_connection(
                    site_project_id=existing_site.id,
                    registration=registration,
                    remote_connection_service=self._remote_connection_service,
                ),
            )
        )

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

    def list_supported_connection_types(self) -> list[RemoteConnectionTypeDescriptor]:
        """Return the discoverable remote connection catalog."""
        if self._remote_connection_service is None:
            return []
        return self._remote_connection_service.list_supported_connection_types()

    def can_test_remote_connection(self, registration: SiteRegistrationInput) -> bool:
        """Return whether the given registration has a complete remote config."""
        if self._remote_connection_service is None:
            return False
        return self._remote_connection_service.can_test_connection(registration.remote_connection)

    def test_remote_connection(
        self,
        registration: SiteRegistrationInput,
    ) -> RemoteConnectionTestResult:
        """Validate and test a remote connection draft without persisting it."""
        if self._remote_connection_service is None:
            msg = "Remote connection testing is not configured."
            raise SiteRegistryValidationError(msg)
        remote_connection = self._remote_connection_service.validate_optional_config(
            registration.remote_connection
        )
        if remote_connection is None:
            msg = "Remote connection test requires a configured remote connection."
            raise SiteRegistryValidationError(msg)
        return self._remote_connection_service.test_connection(remote_connection)


def _require_text(value: str, label: str) -> str:
    normalized_value = value.strip()
    if normalized_value:
        return normalized_value
    msg = f"{label} must not be empty."
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


def _resolve_remote_connection(
    *,
    site_project_id: str,
    registration: SiteRegistrationInput,
    remote_connection_service: RemoteConnectionService | None,
) -> RemoteConnectionConfig | None:
    if remote_connection_service is None:
        return None
    validated_config = remote_connection_service.validate_optional_config(
        registration.remote_connection
    )
    if validated_config is None:
        return None
    return RemoteConnectionConfig(
        id=f"remote-{site_project_id}",
        site_project_id=site_project_id,
        connection_type=validated_config.connection_type,
        host=validated_config.host,
        port=validated_config.port,
        username=validated_config.username,
        password=validated_config.password,
        remote_path=validated_config.remote_path,
        flags=validated_config.flags,
    )
