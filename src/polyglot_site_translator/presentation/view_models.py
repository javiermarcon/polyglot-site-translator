"""Typed presentation models for the Kivy frontend."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavigationMenuItemViewModel:
    """A navigation target rendered in the application menu."""

    key: str
    title: str
    description: str
    is_enabled: bool


@dataclass(frozen=True)
class NavigationMenuSectionViewModel:
    """A grouped section rendered in the application menu."""

    key: str
    title: str
    items: list[NavigationMenuItemViewModel]


@dataclass(frozen=True)
class NavigationMenuStateViewModel:
    """Global navigation menu state for the application shell."""

    sections: list[NavigationMenuSectionViewModel]
    active_route_key: str
    is_open: bool


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
class SettingsOptionViewModel:
    """A selectable option rendered by a settings control."""

    value: str
    label: str


@dataclass(frozen=True)
class SettingsFieldViewModel:
    """A typed settings field descriptor for the settings UI."""

    key: str
    label: str
    help_text: str
    control_type: str
    options: list[SettingsOptionViewModel]


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
    selected_section_title: str
    selected_section_description: str
    selected_section_is_available: bool
    app_settings: AppSettingsViewModel
    theme_mode_field: SettingsFieldViewModel
    ui_language_field: SettingsFieldViewModel
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


def build_navigation_menu_state(
    *,
    active_route_key: str,
    operations_enabled: bool,
    is_open: bool,
) -> NavigationMenuStateViewModel:
    """Return the grouped application navigation menu."""
    return NavigationMenuStateViewModel(
        sections=[
            NavigationMenuSectionViewModel(
                key="workspace",
                title="Workspace",
                items=[
                    NavigationMenuItemViewModel(
                        key="dashboard",
                        title="Dashboard",
                        description="Overview and entry points for the application.",
                        is_enabled=True,
                    ),
                    NavigationMenuItemViewModel(
                        key="projects",
                        title="Projects",
                        description="Open the registry of managed projects and sites.",
                        is_enabled=True,
                    ),
                ],
            ),
            NavigationMenuSectionViewModel(
                key="operations",
                title="Operations",
                items=[
                    NavigationMenuItemViewModel(
                        key="sync",
                        title="Sync",
                        description="Project-scoped synchronization workflow.",
                        is_enabled=operations_enabled,
                    ),
                    NavigationMenuItemViewModel(
                        key="audit",
                        title="Audit",
                        description="Project-scoped audit workflow summary.",
                        is_enabled=operations_enabled,
                    ),
                    NavigationMenuItemViewModel(
                        key="po-processing",
                        title="PO Processing",
                        description="Project-scoped PO workflow summary.",
                        is_enabled=operations_enabled,
                    ),
                ],
            ),
            NavigationMenuSectionViewModel(
                key="system",
                title="System",
                items=[
                    NavigationMenuItemViewModel(
                        key="settings",
                        title="Settings",
                        description="Application, UI and future system configuration.",
                        is_enabled=True,
                    ),
                ],
            ),
        ],
        active_route_key=active_route_key,
        is_open=is_open,
    )


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


def _find_settings_section(section_key: str) -> SettingsSectionViewModel:
    for section in build_settings_sections():
        if section.key == section_key:
            return section
    msg = f"Unknown settings section: {section_key}"
    raise LookupError(msg)


def build_theme_mode_field() -> SettingsFieldViewModel:
    """Return metadata for the theme-mode settings control."""
    return SettingsFieldViewModel(
        key="theme_mode",
        label="Theme Mode",
        help_text="Choose the visual appearance that the Kivy shell should use by default.",
        control_type="choice",
        options=[
            SettingsOptionViewModel(value="system", label="System"),
            SettingsOptionViewModel(value="light", label="Light"),
            SettingsOptionViewModel(value="dark", label="Dark"),
        ],
    )


def build_ui_language_field() -> SettingsFieldViewModel:
    """Return metadata for the UI language settings control."""
    return SettingsFieldViewModel(
        key="ui_language",
        label="UI Language",
        help_text="Prepare the frontend for future localization without wiring translations yet.",
        control_type="choice",
        options=[
            SettingsOptionViewModel(value="en", label="English"),
            SettingsOptionViewModel(value="es", label="Spanish"),
        ],
    )


def build_settings_state(
    *,
    app_settings: AppSettingsViewModel,
    status: str,
    status_message: str | None,
    selected_section_key: str = "app-ui-kivy",
) -> SettingsStateViewModel:
    """Return the settings screen state for the current frontend configuration."""
    selected_section = _find_settings_section(selected_section_key)
    return SettingsStateViewModel(
        sections=build_settings_sections(),
        selected_section_key=selected_section_key,
        selected_section_title=selected_section.title,
        selected_section_description=selected_section.description,
        selected_section_is_available=selected_section.is_available,
        app_settings=app_settings,
        theme_mode_field=build_theme_mode_field(),
        ui_language_field=build_ui_language_field(),
        status=status,
        status_message=status_message,
    )
