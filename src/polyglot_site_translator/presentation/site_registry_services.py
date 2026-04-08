"""Presentation adapters for the real site registry service."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from polyglot_site_translator.domain.framework_detection.errors import (
    FrameworkDetectionAmbiguityError,
)
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.site_registry.errors import (
    SiteRegistryConfigurationError,
    SiteRegistryConflictError,
    SiteRegistryNotFoundError,
    SiteRegistryPersistenceError,
    SiteRegistryValidationError,
)
from polyglot_site_translator.domain.site_registry.models import (
    RegisteredSite,
    SiteRegistrationInput,
)
from polyglot_site_translator.infrastructure.database_location import (
    resolve_sqlite_database_location,
)
from polyglot_site_translator.infrastructure.settings import TomlSettingsService
from polyglot_site_translator.presentation.contracts import (
    ProjectCatalogService,
    ProjectRegistryManagementService,
    ProjectWorkflowService,
)
from polyglot_site_translator.presentation.errors import ControlledServiceError
from polyglot_site_translator.presentation.view_models import (
    AuditSummaryViewModel,
    POProcessingSummaryViewModel,
    ProjectDetailViewModel,
    ProjectEditorStateViewModel,
    ProjectSummaryViewModel,
    SiteEditorViewModel,
    SyncStatusViewModel,
    build_default_site_editor,
    build_framework_type_options_from_descriptors,
    build_project_editor_state,
)
from polyglot_site_translator.services.site_registry import SiteRegistryService


class SiteRegistryPresentationCatalogService(ProjectCatalogService):
    """Expose real site registry records as project summary/detail view models."""

    def __init__(self, service: SiteRegistryService) -> None:
        self._service = service

    def list_projects(self) -> list[ProjectSummaryViewModel]:
        """Return project summaries backed by SQLite."""
        try:
            sites = self._service.list_sites()
        except (
            SiteRegistryConfigurationError,
            SiteRegistryPersistenceError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        return [_build_project_summary(site) for site in sites]

    def get_project_detail(self, project_id: str) -> ProjectDetailViewModel:
        """Return project detail information backed by SQLite."""
        try:
            site = self._service.get_site(project_id)
            detection_result = self._service.detect_framework(site.local_path)
        except (
            SiteRegistryNotFoundError,
            SiteRegistryPersistenceError,
            SiteRegistryConfigurationError,
            FrameworkDetectionAmbiguityError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        return _build_project_detail(site, detection_result)


class SiteRegistryPresentationManagementService(ProjectRegistryManagementService):
    """Expose create and update site registry workflows to the UI."""

    def __init__(
        self,
        *,
        service: SiteRegistryService,
        settings_service: TomlSettingsService,
    ) -> None:
        self._service = service
        self._settings_service = settings_service

    def build_create_project_editor(self) -> ProjectEditorStateViewModel:
        """Return the initial create-project editor state."""
        editor = replace(
            build_default_site_editor(),
            local_path=str(self._default_workspace_root() / "site"),
        )
        return build_project_editor_state(
            mode="create",
            editor=editor,
            framework_options=build_framework_type_options_from_descriptors(
                self._service.list_supported_frameworks()
            ),
            status="editing",
            status_message="Provide the project metadata to register a new site.",
        )

    def build_edit_project_editor(self, project_id: str) -> ProjectEditorStateViewModel:
        """Return the initial edit-project editor state."""
        try:
            site = self._service.get_site(project_id)
        except (
            SiteRegistryNotFoundError,
            SiteRegistryPersistenceError,
            SiteRegistryConfigurationError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        return build_project_editor_state(
            mode="edit",
            editor=_build_site_editor(site),
            framework_options=build_framework_type_options_from_descriptors(
                self._service.list_supported_frameworks()
            ),
            status="editing",
            status_message="Update the persisted site registry record.",
        )

    def create_project(self, editor: SiteEditorViewModel) -> ProjectDetailViewModel:
        """Create a site registry record from the editor state."""
        try:
            site = self._service.create_site(_build_service_payload(editor))
            detection_result = self._service.detect_framework(site.local_path)
        except (
            ValueError,
            FrameworkDetectionAmbiguityError,
            SiteRegistryValidationError,
            SiteRegistryConflictError,
            SiteRegistryConfigurationError,
            SiteRegistryPersistenceError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        return _build_project_detail(site, detection_result)

    def update_project(
        self,
        project_id: str,
        editor: SiteEditorViewModel,
    ) -> ProjectDetailViewModel:
        """Update a site registry record from the editor state."""
        try:
            site = self._service.update_site(
                site_id=project_id,
                registration=_build_service_payload(editor),
            )
            detection_result = self._service.detect_framework(site.local_path)
        except (
            ValueError,
            FrameworkDetectionAmbiguityError,
            SiteRegistryValidationError,
            SiteRegistryConflictError,
            SiteRegistryNotFoundError,
            SiteRegistryConfigurationError,
            SiteRegistryPersistenceError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        return _build_project_detail(site, detection_result)

    def _default_workspace_root(self) -> Path:
        try:
            settings_state = self._settings_service.load_settings()
            location = resolve_sqlite_database_location(settings_state.app_settings)
        except (
            ControlledServiceError,
            SiteRegistryConfigurationError,
            SiteRegistryPersistenceError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        return location.directory


class SiteRegistryPresentationWorkflowService(ProjectWorkflowService):
    """Expose runtime workflow previews backed by persisted project context."""

    def __init__(self, *, service: SiteRegistryService) -> None:
        self._service = service

    def start_sync(self, project_id: str) -> SyncStatusViewModel:
        """Return the current sync preview placeholder."""
        return SyncStatusViewModel(
            status="completed",
            files_synced=12,
            summary="Synchronized 12 files into the local workspace preview.",
        )

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        """Return a framework-aware audit preview for the selected project."""
        try:
            site = self._service.get_site(project_id)
            detection_result = self._service.detect_framework(site.local_path)
        except (
            SiteRegistryNotFoundError,
            SiteRegistryPersistenceError,
            SiteRegistryConfigurationError,
            FrameworkDetectionAmbiguityError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        if detection_result.matched:
            return AuditSummaryViewModel(
                status="completed",
                findings_count=len(detection_result.evidence),
                findings_summary="; ".join(detection_result.evidence),
            )
        warning_text = "; ".join(detection_result.warnings) or (
            "No supported framework markers were detected."
        )
        return AuditSummaryViewModel(
            status="completed",
            findings_count=0,
            findings_summary=(
                f"No supported framework was detected for this project. {warning_text}"
            ),
        )

    def start_po_processing(self, project_id: str) -> POProcessingSummaryViewModel:
        """Return the current PO processing preview placeholder."""
        return POProcessingSummaryViewModel(
            status="completed",
            processed_families=4,
            summary="Prepared 4 locale families for future PO synchronization.",
        )


def _build_service_payload(editor: SiteEditorViewModel) -> SiteRegistrationInput:
    return SiteRegistrationInput(
        name=editor.name,
        framework_type=editor.framework_type,
        local_path=editor.local_path,
        default_locale=editor.default_locale,
        ftp_host=editor.ftp_host,
        ftp_port=int(editor.ftp_port),
        ftp_username=editor.ftp_username,
        ftp_password=editor.ftp_password,
        ftp_remote_path=editor.ftp_remote_path,
        is_active=editor.is_active,
    )


def _build_project_summary(site: RegisteredSite) -> ProjectSummaryViewModel:
    return ProjectSummaryViewModel(
        id=site.id,
        name=site.name,
        framework=_format_framework_name(site.framework_type),
        local_path=site.local_path,
        status="Active" if site.is_active else "Inactive",
    )


def _build_project_detail(
    site: RegisteredSite,
    detection_result: FrameworkDetectionResult | None = None,
) -> ProjectDetailViewModel:
    return ProjectDetailViewModel(
        project=_build_project_summary(site),
        configuration_summary=(
            f"Locale: {site.default_locale} | FTP host: {site.ftp_host} "
            f"| Remote path: {site.ftp_remote_path}"
        ),
        metadata_summary=_build_metadata_summary(site, detection_result),
        actions=[],
    )


def _build_site_editor(site: RegisteredSite) -> SiteEditorViewModel:
    return SiteEditorViewModel(
        site_id=site.id,
        name=site.name,
        framework_type=site.framework_type,
        local_path=site.local_path,
        default_locale=site.default_locale,
        ftp_host=site.ftp_host,
        ftp_port=str(site.ftp_port),
        ftp_username=site.ftp_username,
        ftp_password=site.ftp_password,
        ftp_remote_path=site.ftp_remote_path,
        is_active=site.is_active,
    )


def _format_framework_name(framework_type: str) -> str:
    framework_map = {
        "wordpress": "WordPress",
        "django": "Django",
        "flask": "Flask",
    }
    return framework_map.get(framework_type, framework_type.title())


def _build_metadata_summary(
    site: RegisteredSite,
    detection_result: FrameworkDetectionResult | None,
) -> str:
    summary = (
        f"Framework: {_format_framework_name(site.framework_type)} | "
        f"FTP user: {site.ftp_username} | FTP port: {site.ftp_port}"
    )
    if detection_result is None:
        return summary
    if detection_result.matched:
        evidence = "; ".join(detection_result.evidence)
        return (
            f"{summary} | Framework detection: "
            f"{_format_framework_name(detection_result.framework_type)} via "
            f"{detection_result.adapter_name} ({evidence})"
        )
    warning_text = "; ".join(detection_result.warnings) or (
        "No supported framework markers were detected."
    )
    return f"{summary} | No framework detected. {warning_text}"
