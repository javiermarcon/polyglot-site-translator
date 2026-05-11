"""Service contracts consumed by the presentation layer."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from polyglot_site_translator.domain.po_processing.models import POProcessingProgress
from polyglot_site_translator.domain.sync.models import SyncProgressEvent
from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    AuditSummaryViewModel,
    POProcessingSummaryViewModel,
    ProjectDetailViewModel,
    ProjectEditorStateViewModel,
    ProjectSummaryViewModel,
    RemoteConnectionTestResultViewModel,
    SettingsStateViewModel,
    SiteEditorViewModel,
    SyncStatusViewModel,
    TranslationWorkflowRequestViewModel,
)


class ProjectCatalogService(Protocol):
    """Read-only project catalog interface for the UI.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def list_projects(self) -> list[ProjectSummaryViewModel]:
        """Return registered projects for list screens.

        Returns:
            list[ProjectSummaryViewModel]: Structured value returned by this callable.
        """

    def get_project_detail(self, project_id: str) -> ProjectDetailViewModel:
        """Return project detail data for the selected project.

        Args:
            project_id (str): Value supplied to this callable.

        Returns:
            ProjectDetailViewModel: Structured value returned by this callable.
        """


class ProjectWorkflowService(Protocol):
    """Workflow actions exposed to the UI.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def start_sync(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Start or preview a sync workflow for a project.

        Args:
            project_id (str): Value supplied to this callable.
            progress_callback (Callable[[SyncProgressEvent], None] | None): Value supplied to this
        callable.

        Returns:
            SyncStatusViewModel: Structured value returned by this callable.
        """

    def start_sync_to_remote(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Start a local-to-remote sync workflow for a project.

        Args:
            project_id (str): Value supplied to this callable.
            progress_callback (Callable[[SyncProgressEvent], None] | None): Value supplied to this
        callable.

        Returns:
            SyncStatusViewModel: Structured value returned by this callable.
        """

    def trust_remote_host_key(self, project_id: str) -> RemoteConnectionTestResultViewModel:
        """Trust the configured SSH host key for a project after user confirmation.

        Args:
            project_id (str): Value supplied to this callable.

        Returns:
            RemoteConnectionTestResultViewModel: Structured value returned by this callable.
        """

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        """Start an audit workflow for a project.

        Args:
            project_id (str): Value supplied to this callable.

        Returns:
            AuditSummaryViewModel: Structured value returned by this callable.
        """

    def start_po_processing(
        self,
        project_id: str,
        request: TranslationWorkflowRequestViewModel | None = None,
        progress_callback: Callable[[POProcessingProgress], None] | None = None,
    ) -> POProcessingSummaryViewModel:
        """Start a PO processing workflow for a project.

        Args:
            project_id (str): Value supplied to this callable.
            request (TranslationWorkflowRequestViewModel | None): Value supplied to this callable.
            progress_callback (Callable[[POProcessingProgress], None] | None): Value supplied to
        this
            callable.

        Returns:
            POProcessingSummaryViewModel: Structured value returned by this callable.
        """


class SettingsService(Protocol):
    """Settings operations exposed to the UI.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def load_settings(self) -> SettingsStateViewModel:
        """Return the current settings state.

        Returns:
            SettingsStateViewModel: Structured value returned by this callable.
        """

    def save_settings(self, app_settings: AppSettingsViewModel) -> SettingsStateViewModel:
        """Persist frontend settings and return the saved state.

        Args:
            app_settings (AppSettingsViewModel): Value supplied to this callable.

        Returns:
            SettingsStateViewModel: Structured value returned by this callable.
        """

    def reset_settings(self) -> SettingsStateViewModel:
        """Restore frontend settings defaults.

        Returns:
            SettingsStateViewModel: Structured value returned by this callable.
        """


class ProjectRegistryManagementService(Protocol):
    """Create and update project registry records exposed to the UI.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def build_create_project_editor(self) -> ProjectEditorStateViewModel:
        """Return the initial project editor state for create flows.

        Returns:
            ProjectEditorStateViewModel: Structured value returned by this callable.
        """

    def build_edit_project_editor(self, project_id: str) -> ProjectEditorStateViewModel:
        """Return the initial project editor state for edit flows.

        Args:
            project_id (str): Value supplied to this callable.

        Returns:
            ProjectEditorStateViewModel: Structured value returned by this callable.
        """

    def create_project(self, editor: SiteEditorViewModel) -> ProjectDetailViewModel:
        """Create a new project registry record and return its detail view.

        Args:
            editor (SiteEditorViewModel): Value supplied to this callable.

        Returns:
            ProjectDetailViewModel: Structured value returned by this callable.
        """

    def update_project(
        self,
        project_id: str,
        editor: SiteEditorViewModel,
    ) -> ProjectDetailViewModel:
        """Update a project registry record and return its detail view.

        Args:
            project_id (str): Value supplied to this callable.
            editor (SiteEditorViewModel): Value supplied to this callable.

        Returns:
            ProjectDetailViewModel: Structured value returned by this callable.
        """

    def test_remote_connection(
        self,
        editor: SiteEditorViewModel,
    ) -> RemoteConnectionTestResultViewModel:
        """Test the current remote connection draft and return the result.

        Args:
            editor (SiteEditorViewModel): Value supplied to this callable.

        Returns:
            RemoteConnectionTestResultViewModel: Structured value returned by this callable.
        """

    def preview_project_editor(
        self,
        editor: SiteEditorViewModel,
        *,
        mode: str,
    ) -> ProjectEditorStateViewModel:
        """Rebuild the project editor state for a modified draft without persisting it.

        Args:
            editor (SiteEditorViewModel): Value supplied to this callable.
            mode (str): Value supplied to this callable.

        Returns:
            ProjectEditorStateViewModel: Structured value returned by this callable.
        """


@dataclass(frozen=True)
class FrontendServices:
    """Injectable service bundle consumed by the presentation layer.

    Attributes:
        catalog (ProjectCatalogService): Documented attribute exposed by this type.
        workflows (ProjectWorkflowService): Documented attribute exposed by this type.
        settings (SettingsService): Documented attribute exposed by this type.
        registry (ProjectRegistryManagementService): Documented attribute exposed by this type.
    """

    catalog: ProjectCatalogService
    workflows: ProjectWorkflowService
    settings: SettingsService
    registry: ProjectRegistryManagementService
