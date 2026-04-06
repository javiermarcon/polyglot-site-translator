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
class SettingsSectionViewModel:
    """A settings category rendered in the settings screen."""

    key: str
    title: str
    description: str
    is_available: bool


@dataclass(frozen=True)
class AppSettingsViewModel:
    """Editable frontend settings related to Kivy and UI behavior."""

    theme_mode: str
    window_width: int
    window_height: int
    remember_last_screen: bool
    developer_mode: bool
    ui_language: str


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
class SettingsStateViewModel:
    """Settings state consumed by the settings screen."""

    sections: list[SettingsSectionViewModel]
    selected_section_key: str
    app_settings: AppSettingsViewModel
    status: str
    status_message: str | None


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


def build_settings_sections() -> list[SettingsSectionViewModel]:
    """Return the initial extensible settings sections."""
    return [
        SettingsSectionViewModel(
            key="app-ui-kivy",
            title="App / UI / Kivy Settings",
            description="Frontend behavior, navigation and window defaults.",
            is_available=True,
        ),
        SettingsSectionViewModel(
            key="translation",
            title="Translation Settings",
            description="Reserved for translation-provider and locale workflow options.",
            is_available=False,
        ),
        SettingsSectionViewModel(
            key="frameworks",
            title="Framework / Adapter Settings",
            description="Reserved for future framework-specific configuration.",
            is_available=False,
        ),
        SettingsSectionViewModel(
            key="ftp-reporting",
            title="FTP / Reporting Settings",
            description="Reserved for future sync and reporting configuration.",
            is_available=False,
        ),
    ]


def build_default_app_settings() -> AppSettingsViewModel:
    """Return the default frontend settings."""
    return AppSettingsViewModel(
        theme_mode="system",
        window_width=1280,
        window_height=720,
        remember_last_screen=False,
        developer_mode=False,
        ui_language="en",
    )


def build_settings_state(
    *,
    app_settings: AppSettingsViewModel,
    status: str,
    status_message: str | None,
    selected_section_key: str = "app-ui-kivy",
) -> SettingsStateViewModel:
    """Return the settings screen state for the current frontend configuration."""
    return SettingsStateViewModel(
        sections=build_settings_sections(),
        selected_section_key=selected_section_key,
        app_settings=app_settings,
        status=status,
        status_message=status_message,
    )
