"""Typed presentation models for the Kivy frontend."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardSectionViewModel:
    """A top-level workflow entry rendered in the dashboard."""

    key: str
    title: str
    description: str


@dataclass(frozen=True)
class ProjectSummaryViewModel:
    """Summary row rendered in the projects list."""

    id: str
    name: str
    framework: str
    local_path: str
    status: str


@dataclass(frozen=True)
class ProjectActionViewModel:
    """Action available from the project detail view."""

    key: str
    label: str
    description: str


@dataclass(frozen=True)
class ProjectDetailViewModel:
    """Detailed project information rendered by the UI."""

    project: ProjectSummaryViewModel
    configuration_summary: str
    metadata_summary: str
    actions: list[ProjectActionViewModel]


@dataclass(frozen=True)
class DashboardStateViewModel:
    """Dashboard state consumed by the dashboard screen."""

    sections: list[DashboardSectionViewModel]


@dataclass(frozen=True)
class ProjectsStateViewModel:
    """Projects list state consumed by the projects screen."""

    projects: list[ProjectSummaryViewModel]
    empty_message: str | None


@dataclass(frozen=True)
class ProjectDetailStateViewModel:
    """Project detail state consumed by the detail screen."""

    project: ProjectSummaryViewModel
    configuration_summary: str
    metadata_summary: str
    actions: list[ProjectActionViewModel]


@dataclass(frozen=True)
class SyncStatusViewModel:
    """Sync panel state."""

    status: str
    files_synced: int
    summary: str


@dataclass(frozen=True)
class AuditSummaryViewModel:
    """Audit panel state."""

    status: str
    findings_count: int
    findings_summary: str


@dataclass(frozen=True)
class POProcessingSummaryViewModel:
    """PO processing panel state."""

    status: str
    processed_families: int
    summary: str
