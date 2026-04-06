"""Service contracts consumed by the presentation layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from polyglot_site_translator.presentation.view_models import (
    AppSettingsViewModel,
    AuditSummaryViewModel,
    POProcessingSummaryViewModel,
    ProjectDetailViewModel,
    ProjectSummaryViewModel,
    SettingsStateViewModel,
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

    def start_sync(self, project_id: str) -> SyncStatusViewModel:
        """Start or preview a sync workflow for a project."""

    def start_audit(self, project_id: str) -> AuditSummaryViewModel:
        """Start an audit workflow for a project."""

    def start_po_processing(self, project_id: str) -> POProcessingSummaryViewModel:
        """Start a PO processing workflow for a project."""


class SettingsService(Protocol):
    """Settings operations exposed to the UI."""

    def load_settings(self) -> SettingsStateViewModel:
        """Return the current settings state."""

    def save_settings(self, app_settings: AppSettingsViewModel) -> SettingsStateViewModel:
        """Persist frontend settings and return the saved state."""

    def reset_settings(self) -> SettingsStateViewModel:
        """Restore frontend settings defaults."""


@dataclass(frozen=True)
class FrontendServices:
    """Injectable service bundle consumed by the presentation layer."""

    catalog: ProjectCatalogService
    workflows: ProjectWorkflowService
    settings: SettingsService
