"""Presentation adapters for the real site registry service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from polyglot_site_translator.domain.framework_detection.errors import (
    FrameworkDetectionAmbiguityError,
)
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.remote_connections.models import (
    NO_REMOTE_CONNECTION_VALUE,
    RemoteConnectionConfigInput,
    RemoteConnectionFlags,
    RemoteConnectionTestResult,
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
from polyglot_site_translator.domain.sync.models import (
    SyncDirection,
    SyncProgressEvent,
    SyncResult,
)
from polyglot_site_translator.domain.sync.scope import (
    ProjectSyncRuleOverride,
    ResolvedSyncRule,
    ResolvedSyncScope,
    SyncFilterType,
    SyncRuleBehavior,
    SyncRuleSource,
    SyncScopeStatus,
    build_sync_rule_key,
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
    RemoteConnectionTestResultViewModel,
    SiteEditorViewModel,
    SyncRuleEditorItemViewModel,
    SyncStatusViewModel,
    build_connection_type_options,
    build_default_site_editor,
    build_framework_type_options_from_descriptors,
    build_project_editor_state,
    build_sync_rule_behavior_options,
    build_sync_rule_filter_type_options,
)
from polyglot_site_translator.services.framework_sync_scope import FrameworkSyncScopeService
from polyglot_site_translator.services.site_registry import SiteRegistryService


class SiteRegistryWorkflowService(Protocol):
    """Subset of site-registry behavior required by workflow presentation adapters."""

    def get_site(self, site_id: str) -> RegisteredSite:
        """Return a persisted site registry record."""

    def detect_framework(self, project_path: str) -> FrameworkDetectionResult:
        """Return framework detection data for a local path."""

    def test_remote_connection(
        self,
        registration: SiteRegistrationInput,
    ) -> RemoteConnectionTestResult:
        """Test a remote connection from site registration input."""


class ProjectSyncWorkflowService(Protocol):
    """Sync orchestration contract consumed by workflow presentation adapters."""

    def sync_remote_to_local(
        self,
        site: RegisteredSite,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncResult:
        """Synchronize the remote project into the local workspace."""

    def sync_local_to_remote(
        self,
        site: RegisteredSite,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncResult:
        """Synchronize the local workspace into the remote project."""


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
        framework_sync_scope_service: FrameworkSyncScopeService | None = None,
    ) -> None:
        self._service = service
        self._settings_service = settings_service
        self._framework_sync_scope_service = framework_sync_scope_service

    def build_create_project_editor(self) -> ProjectEditorStateViewModel:
        """Return the initial create-project editor state."""
        editor = replace(
            build_default_site_editor(),
            local_path=str(self._default_workspace_root() / "site"),
        )
        return _build_editor_state(
            service=self._service,
            framework_sync_scope_service=self._framework_sync_scope_service,
            mode="create",
            editor=editor,
            status="editing",
            status_message="Provide the project metadata to register a new site.",
            connection_test_result=None,
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
        return _build_editor_state(
            service=self._service,
            framework_sync_scope_service=self._framework_sync_scope_service,
            mode="edit",
            editor=_build_site_editor(site),
            status="editing",
            status_message="Update the persisted site registry record.",
            connection_test_result=None,
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

    def test_remote_connection(
        self,
        editor: SiteEditorViewModel,
    ) -> RemoteConnectionTestResultViewModel:
        """Test the current remote connection draft from the editor."""
        try:
            result = self._service.test_remote_connection(_build_service_payload(editor))
        except (
            ValueError,
            SiteRegistryValidationError,
            SiteRegistryConfigurationError,
            SiteRegistryPersistenceError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        return RemoteConnectionTestResultViewModel(
            success=result.success,
            message=result.message,
            error_code=result.error_code,
        )

    def preview_project_editor(
        self,
        editor: SiteEditorViewModel,
        *,
        mode: str,
    ) -> ProjectEditorStateViewModel:
        """Rebuild the editor state for the current draft without persisting changes."""
        try:
            return _build_editor_state(
                service=self._service,
                framework_sync_scope_service=self._framework_sync_scope_service,
                mode=mode,
                editor=editor,
                status="editing",
                status_message="Project editor draft updated.",
                connection_test_result=None,
            )
        except ValueError as error:
            raise ControlledServiceError(str(error)) from error

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

    def __init__(
        self,
        *,
        service: SiteRegistryWorkflowService,
        project_sync_service: ProjectSyncWorkflowService,
    ) -> None:
        self._service = service
        self._project_sync_service = project_sync_service

    def start_sync(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Run remote-to-local sync for the selected project."""
        try:
            site = self._service.get_site(project_id)
        except (
            SiteRegistryNotFoundError,
            SiteRegistryPersistenceError,
            SiteRegistryConfigurationError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        result = self._project_sync_service.sync_remote_to_local(
            site,
            progress_callback=progress_callback,
        )
        return _build_sync_status(result)

    def start_sync_to_remote(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Run local-to-remote sync for the selected project."""
        try:
            site = self._service.get_site(project_id)
        except (
            SiteRegistryNotFoundError,
            SiteRegistryPersistenceError,
            SiteRegistryConfigurationError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        result = self._project_sync_service.sync_local_to_remote(
            site,
            progress_callback=progress_callback,
        )
        return _build_sync_status(result)

    def trust_remote_host_key(self, project_id: str) -> RemoteConnectionTestResultViewModel:
        """Trust a selected project's SSH host key after explicit UI confirmation."""
        try:
            site = self._service.get_site(project_id)
            _require_remote_connection_for_host_key_trust(site)
            remote_connection = site.remote_connection
            if remote_connection is None:
                msg = "Remote connection unexpectedly missing after validation."
                raise AssertionError(msg)
            result = self._service.test_remote_connection(
                SiteRegistrationInput(
                    name=site.name,
                    framework_type=site.framework_type,
                    local_path=site.local_path,
                    default_locale=site.default_locale,
                    remote_connection=RemoteConnectionConfigInput(
                        connection_type=remote_connection.connection_type,
                        host=remote_connection.host,
                        port=remote_connection.port,
                        username=remote_connection.username,
                        password=remote_connection.password,
                        remote_path=remote_connection.remote_path,
                        flags=replace(remote_connection.flags, verify_host=False),
                    ),
                    is_active=site.is_active,
                )
            )
        except (
            ValueError,
            SiteRegistryValidationError,
            SiteRegistryNotFoundError,
            SiteRegistryPersistenceError,
            SiteRegistryConfigurationError,
        ) as error:
            raise ControlledServiceError(str(error)) from error
        return RemoteConnectionTestResultViewModel(
            success=result.success,
            message=result.message,
            error_code=result.error_code,
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


def _build_editor_state(  # noqa: PLR0913
    *,
    service: SiteRegistryService,
    framework_sync_scope_service: FrameworkSyncScopeService | None,
    mode: str,
    editor: SiteEditorViewModel,
    status: str,
    status_message: str | None,
    connection_test_result: RemoteConnectionTestResultViewModel | None,
) -> ProjectEditorStateViewModel:
    resolved_scope = _resolve_editor_sync_scope(
        framework_sync_scope_service=framework_sync_scope_service,
        editor=editor,
    )
    editor_with_scope = _apply_resolved_scope_to_editor(editor, resolved_scope)
    return build_project_editor_state(
        mode=mode,
        editor=editor_with_scope,
        framework_options=build_framework_type_options_from_descriptors(
            service.list_supported_frameworks()
        ),
        connection_type_options=build_connection_type_options(
            descriptors=service.list_supported_connection_types()
        ),
        sync_rule_filter_type_options=build_sync_rule_filter_type_options(),
        sync_rule_behavior_options=build_sync_rule_behavior_options(),
        connection_test_enabled=service.can_test_remote_connection(
            _build_service_payload(editor_with_scope)
        ),
        connection_test_result=connection_test_result,
        sync_scope_status=resolved_scope.status.value,
        sync_scope_message=resolved_scope.message,
        status=status,
        status_message=status_message,
    )


def _require_remote_connection_for_host_key_trust(site: RegisteredSite) -> None:
    if site.remote_connection is not None:
        return
    msg = "Remote host-key trust requires a configured remote connection."
    raise SiteRegistryValidationError(msg)


def _build_service_payload(editor: SiteEditorViewModel) -> SiteRegistrationInput:
    remote_connection: RemoteConnectionConfigInput | None = None
    if editor.connection_type != NO_REMOTE_CONNECTION_VALUE:
        remote_connection = RemoteConnectionConfigInput(
            connection_type=editor.connection_type,
            host=editor.remote_host,
            port=int(editor.remote_port),
            username=editor.remote_username,
            password=editor.remote_password,
            remote_path=editor.remote_path,
            flags=RemoteConnectionFlags(
                verify_host=editor.remote_verify_host,
                use_adapter_sync_filters=editor.use_adapter_sync_filters,
                sync_rule_overrides=_build_project_rule_overrides(editor.sync_rule_items),
            ),
        )
    return SiteRegistrationInput(
        name=editor.name,
        framework_type=editor.framework_type,
        local_path=editor.local_path,
        default_locale=editor.default_locale,
        remote_connection=remote_connection,
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
        configuration_summary=_build_configuration_summary(site),
        metadata_summary=_build_metadata_summary(site, detection_result),
        actions=[],
    )


def _build_site_editor(site: RegisteredSite) -> SiteEditorViewModel:
    remote_connection = site.remote_connection
    if remote_connection is None:
        return SiteEditorViewModel(
            site_id=site.id,
            name=site.name,
            framework_type=site.framework_type,
            local_path=site.local_path,
            default_locale=site.default_locale,
            connection_type=NO_REMOTE_CONNECTION_VALUE,
            remote_host="",
            remote_port="",
            remote_username="",
            remote_password="",
            remote_path="",
            is_active=site.is_active,
            remote_verify_host=True,
            use_adapter_sync_filters=False,
            sync_rule_items=(),
        )
    return SiteEditorViewModel(
        site_id=site.id,
        name=site.name,
        framework_type=site.framework_type,
        local_path=site.local_path,
        default_locale=site.default_locale,
        connection_type=remote_connection.connection_type,
        remote_host=remote_connection.host,
        remote_port=str(remote_connection.port),
        remote_username=remote_connection.username,
        remote_password=remote_connection.password,
        remote_path=remote_connection.remote_path,
        is_active=site.is_active,
        remote_verify_host=remote_connection.flags.verify_host,
        use_adapter_sync_filters=remote_connection.flags.use_adapter_sync_filters,
        sync_rule_items=_build_override_editor_items(remote_connection.flags.sync_rule_overrides),
    )


def _format_framework_name(framework_type: str) -> str:
    framework_map = {
        "wordpress": "WordPress",
        "django": "Django",
        "flask": "Flask",
    }
    return framework_map.get(framework_type, framework_type.title())


def _build_configuration_summary(site: RegisteredSite) -> str:
    if site.remote_connection is None:
        return f"Locale: {site.default_locale} | Remote connection: None"
    sync_mode = "filtered" if site.remote_connection.flags.use_adapter_sync_filters else "full"
    return (
        f"Locale: {site.default_locale} | Remote: {site.remote_connection.connection_type} "
        f"{site.remote_connection.host}:{site.remote_connection.port} "
        f"| Path: {site.remote_connection.remote_path} | Sync mode: {sync_mode}"
    )


def _build_metadata_summary(
    site: RegisteredSite,
    detection_result: FrameworkDetectionResult | None,
) -> str:
    remote_summary = "Remote connection: none configured"
    if site.remote_connection is not None:
        remote_summary = (
            f"Remote user: {site.remote_connection.username} | "
            f"Connection type: {site.remote_connection.connection_type}"
        )
    summary = f"Framework: {_format_framework_name(site.framework_type)} | {remote_summary}"
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


def _build_sync_status(result: SyncResult) -> SyncStatusViewModel:
    if result.success:
        if result.direction is SyncDirection.LOCAL_TO_REMOTE:
            if result.summary.files_uploaded == 0:
                summary = "Local workspace is empty. No files were uploaded."
            else:
                summary = (
                    f"Uploaded {result.summary.files_uploaded} files from {result.local_path} "
                    "into the remote workspace."
                )
        elif result.summary.files_downloaded == 0:
            summary = "Remote workspace is empty. No files were downloaded."
        else:
            summary = (
                f"Downloaded {result.summary.files_downloaded} files into {result.local_path}."
            )
        return SyncStatusViewModel(
            status="completed",
            files_synced=(
                result.summary.files_uploaded
                if result.direction is SyncDirection.LOCAL_TO_REMOTE
                else result.summary.files_downloaded
            ),
            summary=summary,
            error_code=None,
        )
    error = result.error
    error_message = (
        f"Remote sync failed for project '{result.project_id}' using "
        f"{result.connection_type} into '{result.local_path}', but no detailed sync "
        "error was provided."
    )
    error_code = "sync_failed"
    if error is not None:
        error_message = error.message
        error_code = error.code
    return SyncStatusViewModel(
        status="failed",
        files_synced=(
            result.summary.files_uploaded
            if result.direction is SyncDirection.LOCAL_TO_REMOTE
            else result.summary.files_downloaded
        ),
        summary=error_message,
        error_code=error_code,
    )


def _resolve_editor_sync_scope(
    *,
    framework_sync_scope_service: FrameworkSyncScopeService | None,
    editor: SiteEditorViewModel,
) -> ResolvedSyncScope:
    framework_type = editor.framework_type.strip().lower()
    if framework_sync_scope_service is None:
        return ResolvedSyncScope(
            framework_type=framework_type or "unknown",
            adapter_name=None,
            status=SyncScopeStatus.ADAPTER_UNAVAILABLE,
            filters=(),
            excludes=(),
            message="Framework sync scope service is not available in this frontend runtime.",
            catalog_rules=_build_resolved_rules_from_editor_items(editor.sync_rule_items),
        )
    return framework_sync_scope_service.resolve_for_framework(
        framework_type=framework_type,
        project_path=editor.local_path,
        project_rule_overrides=_build_project_rule_overrides(editor.sync_rule_items),
    )


def _apply_resolved_scope_to_editor(
    editor: SiteEditorViewModel,
    resolved_scope: ResolvedSyncScope,
) -> SiteEditorViewModel:
    if resolved_scope.catalog_rules == ():
        return replace(editor, sync_rule_items=())
    return replace(
        editor,
        sync_rule_items=_build_editor_sync_rule_items(resolved_scope),
    )


def _build_editor_sync_rule_items(
    resolved_scope: ResolvedSyncScope,
) -> tuple[SyncRuleEditorItemViewModel, ...]:
    sorted_rules = sorted(
        resolved_scope.catalog_rules,
        key=lambda rule: (
            0 if rule.source is SyncRuleSource.ADAPTER else 1,
            0 if rule.behavior is SyncRuleBehavior.INCLUDE else 1,
            rule.relative_path,
        ),
    )
    return tuple(
        SyncRuleEditorItemViewModel(
            rule_key=rule.rule_key,
            target_rule_key=(rule.rule_key if rule.source is SyncRuleSource.ADAPTER else None),
            relative_path=rule.relative_path,
            filter_type=rule.filter_type.value,
            behavior=rule.behavior.value,
            description=rule.description,
            source=rule.source.value,
            is_enabled=rule.is_enabled,
            is_removable=rule.source is SyncRuleSource.PROJECT,
        )
        for rule in sorted_rules
    )


def _build_override_editor_items(
    overrides: tuple[ProjectSyncRuleOverride, ...],
) -> tuple[SyncRuleEditorItemViewModel, ...]:
    return tuple(
        SyncRuleEditorItemViewModel(
            rule_key=override.rule_key,
            target_rule_key=override.target_rule_key,
            relative_path=override.relative_path,
            filter_type=override.filter_type.value,
            behavior=override.behavior.value,
            description=override.description,
            source=(
                SyncRuleSource.PROJECT.value if override.is_custom else SyncRuleSource.ADAPTER.value
            ),
            is_enabled=override.is_enabled,
            is_removable=override.is_custom,
        )
        for override in overrides
    )


def _build_project_rule_overrides(
    items: tuple[SyncRuleEditorItemViewModel, ...],
) -> tuple[ProjectSyncRuleOverride, ...]:
    overrides: list[ProjectSyncRuleOverride] = []
    seen_rule_keys: set[str] = set()
    for item in items:
        relative_path = item.relative_path.strip().strip("/")
        if relative_path == "":
            msg = "Sync rule paths must not be blank."
            raise ValueError(msg)
        filter_type = SyncFilterType(item.filter_type)
        behavior = SyncRuleBehavior(item.behavior)
        source = SyncRuleSource(item.source)
        rule_key = item.rule_key
        target_rule_key = item.target_rule_key
        if source is SyncRuleSource.PROJECT:
            rule_key = build_sync_rule_key(
                relative_path=relative_path,
                filter_type=filter_type,
                behavior=behavior,
            )
            target_rule_key = None
        elif target_rule_key is None:
            target_rule_key = rule_key
        if rule_key in seen_rule_keys:
            msg = f"Duplicate sync rule detected for '{relative_path}'."
            raise ValueError(msg)
        seen_rule_keys.add(rule_key)
        overrides.append(
            ProjectSyncRuleOverride(
                rule_key=rule_key,
                target_rule_key=target_rule_key,
                relative_path=relative_path,
                filter_type=filter_type,
                behavior=behavior,
                is_enabled=item.is_enabled,
                description=item.description,
            )
        )
    return tuple(overrides)


def _build_resolved_rules_from_editor_items(
    items: tuple[SyncRuleEditorItemViewModel, ...],
) -> tuple[ResolvedSyncRule, ...]:
    return tuple(
        ResolvedSyncRule(
            rule_key=item.rule_key,
            relative_path=item.relative_path,
            filter_type=SyncFilterType(item.filter_type),
            behavior=SyncRuleBehavior(item.behavior),
            description=item.description,
            source=SyncRuleSource(item.source),
            is_enabled=item.is_enabled,
        )
        for item in items
    )
