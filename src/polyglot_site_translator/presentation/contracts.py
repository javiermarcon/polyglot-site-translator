"""Service contracts consumed by the presentation layer."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

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
)


class ProjectCatalogService(Protocol):
    """Read-only project catalog interface for the UI."""

    def list_projects(self) -> list[ProjectSummaryViewModel]:
        """Return registered projects for list screens."""

    def get_project_detail(self, project_id: str) -> ProjectDetailViewModel:
        """Return project detail data for the selected project."""


class ProjectWorkflowService(Protocol):
    """Workflow actions exposed to the UI."""

    def start_sync(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Start or preview a sync workflow for a project."""

    def start_sync_to_remote(
        self,
        project_id: str,
        progress_callback: Callable[[SyncProgressEvent], None] | None = None,
    ) -> SyncStatusViewModel:
        """Start a local-to-remote sync workflow for a project."""

    def trust_remote_host_key(self, project_id: str) -> RemoteConnectionTestResultViewModel:
        """Trust the configured SSH host key for a project after user confirmation."""

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        """Start an audit workflow for a project."""

    def start_po_processing(
        self,
        project_id: str,
        locales: str | None = None,
    ) -> POProcessingSummaryViewModel:
        """Start a PO processing workflow for a project."""


class SettingsService(Protocol):
    """Settings operations exposed to the UI."""

    def load_settings(self) -> SettingsStateViewModel:
        """Return the current settings state."""

    def save_settings(self, app_settings: AppSettingsViewModel) -> SettingsStateViewModel:
        """Persist frontend settings and return the saved state."""

    def reset_settings(self) -> SettingsStateViewModel:
        """Restore frontend settings defaults."""


class ProjectRegistryManagementService(Protocol):
    """Create and update project registry records exposed to the UI."""

    def build_create_project_editor(self) -> ProjectEditorStateViewModel:
        """Return the initial project editor state for create flows."""

    def build_edit_project_editor(self, project_id: str) -> ProjectEditorStateViewModel:
        """Return the initial project editor state for edit flows."""

    def create_project(self, editor: SiteEditorViewModel) -> ProjectDetailViewModel:
        """Create a new project registry record and return its detail view."""

    def update_project(
        self,
        project_id: str,
        editor: SiteEditorViewModel,
    ) -> ProjectDetailViewModel:
        """Update a project registry record and return its detail view."""

    def test_remote_connection(
        self,
        editor: SiteEditorViewModel,
    ) -> RemoteConnectionTestResultViewModel:
        """Test the current remote connection draft and return the result."""

    def preview_project_editor(
        self,
        editor: SiteEditorViewModel,
        *,
        mode: str,
    ) -> ProjectEditorStateViewModel:
        """Rebuild the project editor state for a modified draft without persisting it."""


@dataclass(frozen=True)
class FrontendServices:
    """Injectable service bundle consumed by the presentation layer."""

    catalog: ProjectCatalogService
    workflows: ProjectWorkflowService
    settings: SettingsService
    registry: ProjectRegistryManagementService
