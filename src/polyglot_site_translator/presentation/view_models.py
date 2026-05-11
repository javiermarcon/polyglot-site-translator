"""Typed presentation models for the Kivy frontend."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDescriptor,
)
from polyglot_site_translator.domain.remote_connections.models import (
    NO_REMOTE_CONNECTION_VALUE,
    RemoteConnectionTypeDescriptor,
)
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScopeSettings,
    build_default_sync_scope_settings,
)


@dataclass(frozen=True)
class NavigationMenuItemViewModel:
    """A navigation target rendered in the application menu.

    Attributes:
        key:
            Documented attribute exposed by this type.
        title:
            Documented attribute exposed by this type.
        description:
            Documented attribute exposed by this type.
        is_enabled:
            Documented attribute exposed by this type.
    """

    key: str
    title: str
    description: str
    is_enabled: bool


@dataclass(frozen=True)
class NavigationMenuSectionViewModel:
    """A grouped section rendered in the application menu.

    Attributes:
        key:
            Documented attribute exposed by this type.
        title:
            Documented attribute exposed by this type.
        items:
            Documented attribute exposed by this type.
    """

    key: str
    title: str
    items: list[NavigationMenuItemViewModel]


@dataclass(frozen=True)
class NavigationMenuStateViewModel:
    """Global navigation menu state for the application shell.

    Attributes:
        sections:
            Documented attribute exposed by this type.
        active_route_key:
            Documented attribute exposed by this type.
        is_open:
            Documented attribute exposed by this type.
    """

    sections: list[NavigationMenuSectionViewModel]
    active_route_key: str
    is_open: bool


@dataclass(frozen=True)
class DashboardSectionViewModel:
    """A top-level workflow entry rendered in the dashboard.

    Attributes:
        key:
            Documented attribute exposed by this type.
        title:
            Documented attribute exposed by this type.
        description:
            Documented attribute exposed by this type.
    """

    key: str
    title: str
    description: str


@dataclass(frozen=True)
class SettingsSectionViewModel:
    """A settings category rendered in the settings screen.

    Attributes:
        key:
            Documented attribute exposed by this type.
        title:
            Documented attribute exposed by this type.
        description:
            Documented attribute exposed by this type.
        is_available:
            Documented attribute exposed by this type.
    """

    key: str
    title: str
    description: str
    is_available: bool


@dataclass(frozen=True)
class ProjectEditorSectionViewModel:
    """A project-editor section rendered in the create/edit workflow.

    Attributes:
        key:
            Documented attribute exposed by this type.
        title:
            Documented attribute exposed by this type.
        description:
            Documented attribute exposed by this type.
    """

    key: str
    title: str
    description: str


@dataclass(frozen=True)
class SettingsOptionViewModel:
    """A selectable option rendered by a settings control.

    Attributes:
        value:
            Documented attribute exposed by this type.
        label:
            Documented attribute exposed by this type.
    """

    value: str
    label: str


@dataclass(frozen=True)
class SettingsFieldViewModel:
    """A typed settings field descriptor for the settings UI.

    Attributes:
        key:
            Documented attribute exposed by this type.
        label:
            Documented attribute exposed by this type.
        help_text:
            Documented attribute exposed by this type.
        control_type:
            Documented attribute exposed by this type.
        options:
            Documented attribute exposed by this type.
    """

    key: str
    label: str
    help_text: str
    control_type: str
    options: list[SettingsOptionViewModel]


@dataclass(frozen=True)
class AppSettingsViewModel:
    """Editable frontend settings related to Kivy and UI behavior.

    Attributes:
        theme_mode:
            Documented attribute exposed by this type.
        window_width:
            Documented attribute exposed by this type.
        window_height:
            Documented attribute exposed by this type.
        remember_last_screen:
            Documented attribute exposed by this type.
        last_opened_screen:
            Documented attribute exposed by this type.
        developer_mode:
            Documented attribute exposed by this type.
        ui_language:
            Documented attribute exposed by this type.
        default_project_locale:
            Documented attribute exposed by this type.
        default_compile_mo:
            Documented attribute exposed by this type.
        default_use_external_translator:
            Documented attribute exposed by this type.
        default_use_translation_cache:
            Documented attribute exposed by this type.
        default_only_fuzzy:
            Documented attribute exposed by this type.
        translation_cache_path:
            Documented attribute exposed by this type.
        default_dry_run:
            Documented attribute exposed by this type.
        default_stats_only:
            Documented attribute exposed by this type.
        default_report_inconsistencies:
            Documented attribute exposed by this type.
        database_directory:
            Documented attribute exposed by this type.
        database_filename:
            Documented attribute exposed by this type.
        sync_progress_log_limit:
            Documented attribute exposed by this type.
        sync_scope_settings:
            Documented attribute exposed by this type.
    """

    theme_mode: str = "system"
    window_width: int = 1280
    window_height: int = 720
    remember_last_screen: bool = False
    last_opened_screen: str = "dashboard"
    developer_mode: bool = False
    ui_language: str = "en"
    default_project_locale: str = "en_US"
    default_compile_mo: bool = True
    default_use_external_translator: bool = True
    default_use_translation_cache: bool = True
    default_only_fuzzy: bool = False
    translation_cache_path: str = ""
    default_dry_run: bool = False
    default_stats_only: bool = False
    default_report_inconsistencies: bool = False
    database_directory: str = ""
    database_filename: str = "site_registry.sqlite3"
    sync_progress_log_limit: int = 200
    sync_scope_settings: AdapterSyncScopeSettings = field(
        default_factory=build_default_sync_scope_settings
    )


@dataclass(frozen=True)
class TranslationOptionsViewModel:
    """Translation workflow toggles shared by settings, projects and run popups.

    Attributes:
        compile_mo:
            Documented attribute exposed by this type.
        use_external_translator:
            Documented attribute exposed by this type.
        use_translation_cache:
            Documented attribute exposed by this type.
        only_fuzzy:
            Documented attribute exposed by this type.
        dry_run:
            Documented attribute exposed by this type.
        stats_only:
            Documented attribute exposed by this type.
        report_inconsistencies:
            Documented attribute exposed by this type.
    """

    compile_mo: bool = True
    use_external_translator: bool = True
    use_translation_cache: bool = True
    only_fuzzy: bool = False
    dry_run: bool = False
    stats_only: bool = False
    report_inconsistencies: bool = False


@dataclass(frozen=True)
class TranslationWorkflowRequestViewModel:
    """Per-run translation request selected from the popup.

    Attributes:
        locales:
            Documented attribute exposed by this type.
        options:
            Documented attribute exposed by this type.
    """

    locales: str
    options: TranslationOptionsViewModel


@dataclass(frozen=True)
class ProjectSummaryViewModel:
    """Summary row rendered in the projects list.

    Attributes:
        id:
            Documented attribute exposed by this type.
        name:
            Documented attribute exposed by this type.
        framework:
            Documented attribute exposed by this type.
        local_path:
            Documented attribute exposed by this type.
        status:
            Documented attribute exposed by this type.
    """

    id: str
    name: str
    framework: str
    local_path: str
    status: str


@dataclass(frozen=True)
class ProjectActionViewModel:
    """Action available from the project detail view.

    Attributes:
        key:
            Documented attribute exposed by this type.
        label:
            Documented attribute exposed by this type.
        description:
            Documented attribute exposed by this type.
    """

    key: str
    label: str
    description: str


@dataclass(frozen=True)
class ProjectDetailViewModel:
    """Detailed project information rendered by the UI.

    Attributes:
        project:
            Documented attribute exposed by this type.
        default_locale:
            Documented attribute exposed by this type.
        configuration_summary:
            Documented attribute exposed by this type.
        metadata_summary:
            Documented attribute exposed by this type.
        actions:
            Documented attribute exposed by this type.
        compile_mo:
            Documented attribute exposed by this type.
        use_external_translator:
            Documented attribute exposed by this type.
        use_translation_cache:
            Documented attribute exposed by this type.
        only_fuzzy:
            Documented attribute exposed by this type.
        dry_run:
            Documented attribute exposed by this type.
        stats_only:
            Documented attribute exposed by this type.
        report_inconsistencies:
            Documented attribute exposed by this type.
    """

    project: ProjectSummaryViewModel
    default_locale: str
    configuration_summary: str
    metadata_summary: str
    actions: list[ProjectActionViewModel]
    compile_mo: bool = True
    use_external_translator: bool = True
    use_translation_cache: bool = True
    only_fuzzy: bool = False
    dry_run: bool = False
    stats_only: bool = False
    report_inconsistencies: bool = False

    @property
    def translation_options(self) -> TranslationOptionsViewModel:
        """Return translation toggles associated with this project detail.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_translation_options(
            compile_mo=self.compile_mo,
            use_external_translator=self.use_external_translator,
            use_translation_cache=self.use_translation_cache,
            only_fuzzy=self.only_fuzzy,
            dry_run=self.dry_run,
            stats_only=self.stats_only,
            report_inconsistencies=self.report_inconsistencies,
        )


@dataclass(frozen=True)
class DashboardStateViewModel:
    """Dashboard state consumed by the dashboard screen.

    Attributes:
        sections:
            Documented attribute exposed by this type.
    """

    sections: list[DashboardSectionViewModel]


@dataclass(frozen=True)
class SettingsStateViewModel:
    """Settings state consumed by the settings screen.

    Attributes:
        sections:
            Documented attribute exposed by this type.
        selected_section_key:
            Documented attribute exposed by this type.
        selected_section_title:
            Documented attribute exposed by this type.
        selected_section_description:
            Documented attribute exposed by this type.
        selected_section_is_available:
            Documented attribute exposed by this type.
        app_settings:
            Documented attribute exposed by this type.
        theme_mode_field:
            Documented attribute exposed by this type.
        ui_language_field:
            Documented attribute exposed by this type.
        status:
            Documented attribute exposed by this type.
        status_message:
            Documented attribute exposed by this type.
    """

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
    """Projects list state consumed by the projects screen.

    Attributes:
        projects:
            Documented attribute exposed by this type.
        empty_message:
            Documented attribute exposed by this type.
    """

    projects: list[ProjectSummaryViewModel]
    empty_message: str | None


@dataclass(frozen=True)
class ProjectDetailStateViewModel:
    """Project detail state consumed by the detail screen.

    Attributes:
        project:
            Documented attribute exposed by this type.
        default_locale:
            Documented attribute exposed by this type.
        configuration_summary:
            Documented attribute exposed by this type.
        metadata_summary:
            Documented attribute exposed by this type.
        actions:
            Documented attribute exposed by this type.
        compile_mo:
            Documented attribute exposed by this type.
        use_external_translator:
            Documented attribute exposed by this type.
        use_translation_cache:
            Documented attribute exposed by this type.
        only_fuzzy:
            Documented attribute exposed by this type.
        dry_run:
            Documented attribute exposed by this type.
        stats_only:
            Documented attribute exposed by this type.
        report_inconsistencies:
            Documented attribute exposed by this type.
    """

    project: ProjectSummaryViewModel
    default_locale: str
    configuration_summary: str
    metadata_summary: str
    actions: list[ProjectActionViewModel]
    compile_mo: bool = True
    use_external_translator: bool = True
    use_translation_cache: bool = True
    only_fuzzy: bool = False
    dry_run: bool = False
    stats_only: bool = False
    report_inconsistencies: bool = False

    @property
    def translation_options(self) -> TranslationOptionsViewModel:
        """Return translation toggles associated with this project detail state.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_translation_options(
            compile_mo=self.compile_mo,
            use_external_translator=self.use_external_translator,
            use_translation_cache=self.use_translation_cache,
            only_fuzzy=self.only_fuzzy,
            dry_run=self.dry_run,
            stats_only=self.stats_only,
            report_inconsistencies=self.report_inconsistencies,
        )


@dataclass(frozen=True)
class SiteEditorViewModel:
    """Editable site registry form values consumed by the project editor screen.

    Attributes:
        site_id:
            Documented attribute exposed by this type.
        name:
            Documented attribute exposed by this type.
        framework_type:
            Documented attribute exposed by this type.
        local_path:
            Documented attribute exposed by this type.
        default_locale:
            Documented attribute exposed by this type.
        connection_type:
            Documented attribute exposed by this type.
        remote_host:
            Documented attribute exposed by this type.
        remote_port:
            Documented attribute exposed by this type.
        remote_username:
            Documented attribute exposed by this type.
        remote_password:
            Documented attribute exposed by this type.
        remote_path:
            Documented attribute exposed by this type.
        is_active:
            Documented attribute exposed by this type.
        compile_mo:
            Documented attribute exposed by this type.
        use_external_translator:
            Documented attribute exposed by this type.
        use_translation_cache:
            Documented attribute exposed by this type.
        only_fuzzy:
            Documented attribute exposed by this type.
        dry_run:
            Documented attribute exposed by this type.
        stats_only:
            Documented attribute exposed by this type.
        report_inconsistencies:
            Documented attribute exposed by this type.
        remote_verify_host:
            Documented attribute exposed by this type.
        use_adapter_sync_filters:
            Documented attribute exposed by this type.
        sync_rule_items:
            Documented attribute exposed by this type.
    """

    site_id: str | None
    name: str
    framework_type: str
    local_path: str
    default_locale: str
    connection_type: str
    remote_host: str
    remote_port: str
    remote_username: str
    remote_password: str
    remote_path: str
    is_active: bool
    compile_mo: bool = True
    use_external_translator: bool = True
    use_translation_cache: bool = True
    only_fuzzy: bool = False
    dry_run: bool = False
    stats_only: bool = False
    report_inconsistencies: bool = False
    remote_verify_host: bool = True
    use_adapter_sync_filters: bool = False
    sync_rule_items: tuple[SyncRuleEditorItemViewModel, ...] = ()

    @property
    def translation_options(self) -> TranslationOptionsViewModel:
        """Return translation toggles associated with this editor draft.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return build_translation_options(
            compile_mo=self.compile_mo,
            use_external_translator=self.use_external_translator,
            use_translation_cache=self.use_translation_cache,
            only_fuzzy=self.only_fuzzy,
            dry_run=self.dry_run,
            stats_only=self.stats_only,
            report_inconsistencies=self.report_inconsistencies,
        )


@dataclass(frozen=True)
class RemoteConnectionTestResultViewModel:
    """Connection-test result rendered by the project editor.

    Attributes:
        success:
            Documented attribute exposed by this type.
        message:
            Documented attribute exposed by this type.
        error_code:
            Documented attribute exposed by this type.
    """

    success: bool
    message: str
    error_code: str | None


@dataclass(frozen=True)
class ProjectEditorStateViewModel:
    """Project editor state consumed by the project editor screen.

    Attributes:
        mode:
            Documented attribute exposed by this type.
        title:
            Documented attribute exposed by this type.
        submit_label:
            Documented attribute exposed by this type.
        sections:
            Documented attribute exposed by this type.
        selected_section_key:
            Documented attribute exposed by this type.
        selected_section_title:
            Documented attribute exposed by this type.
        selected_section_description:
            Documented attribute exposed by this type.
        editor:
            Documented attribute exposed by this type.
        framework_options:
            Documented attribute exposed by this type.
        connection_type_options:
            Documented attribute exposed by this type.
        sync_rule_filter_type_options:
            Documented attribute exposed by this type.
        sync_rule_behavior_options:
            Documented attribute exposed by this type.
        connection_test_enabled:
            Documented attribute exposed by this type.
        connection_test_result:
            Documented attribute exposed by this type.
        sync_scope_status:
            Documented attribute exposed by this type.
        sync_scope_message:
            Documented attribute exposed by this type.
        status:
            Documented attribute exposed by this type.
        status_message:
            Documented attribute exposed by this type.
    """

    mode: str
    title: str
    submit_label: str
    sections: list[ProjectEditorSectionViewModel]
    selected_section_key: str
    selected_section_title: str
    selected_section_description: str
    editor: SiteEditorViewModel
    framework_options: list[SettingsOptionViewModel]
    connection_type_options: list[SettingsOptionViewModel]
    sync_rule_filter_type_options: list[SettingsOptionViewModel]
    sync_rule_behavior_options: list[SettingsOptionViewModel]
    connection_test_enabled: bool
    connection_test_result: RemoteConnectionTestResultViewModel | None
    sync_scope_status: str
    sync_scope_message: str
    status: str
    status_message: str | None


@dataclass(frozen=True)
class SyncRuleEditorItemViewModel:
    """A single sync rule rendered and edited in the project editor.

    Attributes:
        rule_key:
            Documented attribute exposed by this type.
        target_rule_key:
            Documented attribute exposed by this type.
        relative_path:
            Documented attribute exposed by this type.
        filter_type:
            Documented attribute exposed by this type.
        behavior:
            Documented attribute exposed by this type.
        description:
            Documented attribute exposed by this type.
        source:
            Documented attribute exposed by this type.
        is_enabled:
            Documented attribute exposed by this type.
        is_removable:
            Documented attribute exposed by this type.
    """

    rule_key: str
    target_rule_key: str | None
    relative_path: str
    filter_type: str
    behavior: str
    description: str
    source: str
    is_enabled: bool
    is_removable: bool


@dataclass(frozen=True)
class SyncStatusViewModel:
    """Sync panel state.

    Attributes:
        status:
            Documented attribute exposed by this type.
        files_synced:
            Documented attribute exposed by this type.
        summary:
            Documented attribute exposed by this type.
        error_code:
            Documented attribute exposed by this type.
    """

    status: str
    files_synced: int
    summary: str
    error_code: str | None = None


@dataclass(frozen=True)
class SyncCommandLogEntryViewModel:
    """A single sync command rendered in the progress window.

    Attributes:
        command_text:
            Documented attribute exposed by this type.
        message:
            Documented attribute exposed by this type.
    """

    command_text: str
    message: str


@dataclass(frozen=True)
class SyncProgressStateViewModel:
    """Progress state rendered while a sync runs in background.

    Attributes:
        project_id:
            Documented attribute exposed by this type.
        project_name:
            Documented attribute exposed by this type.
        status:
            Documented attribute exposed by this type.
        message:
            Documented attribute exposed by this type.
        progress_current:
            Documented attribute exposed by this type.
        progress_total:
            Documented attribute exposed by this type.
        progress_is_indeterminate:
            Documented attribute exposed by this type.
        command_log_limit:
            Documented attribute exposed by this type.
        command_log:
            Documented attribute exposed by this type.
    """

    project_id: str
    project_name: str
    status: str
    message: str
    progress_current: int
    progress_total: int
    progress_is_indeterminate: bool
    command_log_limit: int
    command_log: list[SyncCommandLogEntryViewModel]


@dataclass(frozen=True)
class AuditSummaryViewModel:
    """Audit panel state.

    Attributes:
        status:
            Documented attribute exposed by this type.
        findings_count:
            Documented attribute exposed by this type.
        findings_summary:
            Documented attribute exposed by this type.
    """

    status: str
    findings_count: int
    findings_summary: str


@dataclass(frozen=True)
class POProcessingSummaryViewModel:
    """PO processing panel state.

    Attributes:
        status:
            Documented attribute exposed by this type.
        processed_families:
            Documented attribute exposed by this type.
        summary:
            Documented attribute exposed by this type.
        progress_current:
            Documented attribute exposed by this type.
        progress_total:
            Documented attribute exposed by this type.
        progress_is_indeterminate:
            Documented attribute exposed by this type.
        current_file:
            Documented attribute exposed by this type.
        current_entry:
            Documented attribute exposed by this type.
    """

    status: str
    processed_families: int
    summary: str
    progress_current: int = 0
    progress_total: int = 0
    progress_is_indeterminate: bool = True
    current_file: str | None = None
    current_entry: str | None = None


def build_settings_sections() -> list[SettingsSectionViewModel]:
    """Return the initial extensible settings sections.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
            description="Locale defaults and translation workflow behavior.",
            is_available=True,
        ),
        SettingsSectionViewModel(
            key="frameworks",
            title="Framework / Adapter Settings",
            description=(
                "Shared sync filters, framework rules and gitignore integration."
            ),
            is_available=True,
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
    """Return the grouped application navigation menu.

    Args:
        active_route_key:
            Value supplied to this callable.
        operations_enabled:
            Value supplied to this callable.
        is_open:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
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
                        title="Translation",
                        description="Project-scoped translation workflow summary.",
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


def build_default_app_settings(
    *,
    database_directory: str = "",
    database_filename: str = "site_registry.sqlite3",
) -> AppSettingsViewModel:
    """Return the default frontend settings.

    Args:
        database_directory:
            Value supplied to this callable.
        database_filename:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    translation_cache_path = (
        str(Path(database_directory) / ".po_translation_cache")
        if database_directory != ""
        else ".po_translation_cache"
    )
    return AppSettingsViewModel(
        theme_mode="system",
        window_width=1280,
        window_height=720,
        remember_last_screen=False,
        last_opened_screen="dashboard",
        developer_mode=False,
        ui_language="en",
        default_project_locale="en_US",
        default_compile_mo=True,
        default_use_external_translator=True,
        default_use_translation_cache=True,
        default_only_fuzzy=False,
        translation_cache_path=translation_cache_path,
        default_dry_run=False,
        default_stats_only=False,
        default_report_inconsistencies=False,
        database_directory=database_directory,
        database_filename=database_filename,
        sync_progress_log_limit=200,
        sync_scope_settings=build_default_sync_scope_settings(),
    )


def build_translation_options(  # noqa: PLR0913
    *,
    compile_mo: bool = True,
    use_external_translator: bool = True,
    use_translation_cache: bool = True,
    only_fuzzy: bool = False,
    dry_run: bool = False,
    stats_only: bool = False,
    report_inconsistencies: bool = False,
) -> TranslationOptionsViewModel:
    """Return translation workflow toggles for settings, projects and popups.

    Args:
        compile_mo:
            Value supplied to this callable.
        use_external_translator:
            Value supplied to this callable.
        use_translation_cache:
            Value supplied to this callable.
        only_fuzzy:
            Value supplied to this callable.
        dry_run:
            Value supplied to this callable.
        stats_only:
            Value supplied to this callable.
        report_inconsistencies:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return TranslationOptionsViewModel(
        compile_mo=compile_mo,
        use_external_translator=use_external_translator,
        use_translation_cache=use_translation_cache,
        only_fuzzy=only_fuzzy,
        dry_run=dry_run,
        stats_only=stats_only,
        report_inconsistencies=report_inconsistencies,
    )


def build_default_site_editor(
    *,
    default_locale: str = "en_US",
    translation_options: TranslationOptionsViewModel | None = None,
) -> SiteEditorViewModel:
    """Return the default site registry editor draft.

    Args:
        default_locale:
            Value supplied to this callable.
        translation_options:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    options = (
        build_translation_options()
        if translation_options is None
        else translation_options
    )
    return SiteEditorViewModel(
        site_id=None,
        name="",
        framework_type="unknown",
        local_path="",
        default_locale=default_locale,
        compile_mo=options.compile_mo,
        use_external_translator=options.use_external_translator,
        use_translation_cache=options.use_translation_cache,
        only_fuzzy=options.only_fuzzy,
        dry_run=options.dry_run,
        stats_only=options.stats_only,
        report_inconsistencies=options.report_inconsistencies,
        connection_type=NO_REMOTE_CONNECTION_VALUE,
        remote_host="",
        remote_port="",
        remote_username="",
        remote_password="",
        remote_path="",
        is_active=True,
        remote_verify_host=True,
        use_adapter_sync_filters=False,
        sync_rule_items=(),
    )


def build_project_editor_state(  # noqa: PLR0913
    *,
    mode: str,
    editor: SiteEditorViewModel,
    framework_options: list[SettingsOptionViewModel],
    connection_type_options: list[SettingsOptionViewModel],
    sync_rule_filter_type_options: list[SettingsOptionViewModel],
    sync_rule_behavior_options: list[SettingsOptionViewModel],
    connection_test_enabled: bool,
    connection_test_result: RemoteConnectionTestResultViewModel | None,
    sync_scope_status: str,
    sync_scope_message: str,
    status: str,
    status_message: str | None,
    selected_section_key: str = "general",
) -> ProjectEditorStateViewModel:
    """Return the project editor state for create/edit flows.

    Args:
        mode:
            Value supplied to this callable.
        editor:
            Value supplied to this callable.
        framework_options:
            Value supplied to this callable.
        connection_type_options:
            Value supplied to this callable.
        sync_rule_filter_type_options:
            Value supplied to this callable.
        sync_rule_behavior_options:
            Value supplied to this callable.
        connection_test_enabled:
            Value supplied to this callable.
        connection_test_result:
            Value supplied to this callable.
        sync_scope_status:
            Value supplied to this callable.
        sync_scope_message:
            Value supplied to this callable.
        status:
            Value supplied to this callable.
        status_message:
            Value supplied to this callable.
        selected_section_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    selected_section = _find_project_editor_section(selected_section_key)
    if mode == "edit":
        return ProjectEditorStateViewModel(
            mode=mode,
            title="Edit Project",
            submit_label="Save Project",
            sections=build_project_editor_sections(),
            selected_section_key=selected_section.key,
            selected_section_title=selected_section.title,
            selected_section_description=selected_section.description,
            editor=editor,
            framework_options=framework_options,
            connection_type_options=connection_type_options,
            sync_rule_filter_type_options=sync_rule_filter_type_options,
            sync_rule_behavior_options=sync_rule_behavior_options,
            connection_test_enabled=connection_test_enabled,
            connection_test_result=connection_test_result,
            sync_scope_status=sync_scope_status,
            sync_scope_message=sync_scope_message,
            status=status,
            status_message=status_message,
        )
    return ProjectEditorStateViewModel(
        mode=mode,
        title="Register Project",
        submit_label="Create Project",
        sections=build_project_editor_sections(),
        selected_section_key=selected_section.key,
        selected_section_title=selected_section.title,
        selected_section_description=selected_section.description,
        editor=editor,
        framework_options=framework_options,
        connection_type_options=connection_type_options,
        sync_rule_filter_type_options=sync_rule_filter_type_options,
        sync_rule_behavior_options=sync_rule_behavior_options,
        connection_test_enabled=connection_test_enabled,
        connection_test_result=connection_test_result,
        sync_scope_status=sync_scope_status,
        sync_scope_message=sync_scope_message,
        status=status,
        status_message=status_message,
    )


def build_framework_type_options_from_descriptors(
    descriptors: Iterable[FrameworkDescriptor],
) -> list[SettingsOptionViewModel]:
    """Return selectable framework types for the project editor.

    Args:
        descriptors:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return [
        SettingsOptionViewModel(
            value=descriptor.framework_type,
            label=descriptor.display_name,
        )
        for descriptor in descriptors
    ]


def build_connection_type_options(
    *,
    descriptors: Iterable[RemoteConnectionTypeDescriptor],
) -> list[SettingsOptionViewModel]:
    """Return selectable remote connection types for the project editor.

    Args:
        descriptors:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return [
        SettingsOptionViewModel(
            value=descriptor.connection_type,
            label=descriptor.display_name,
        )
        for descriptor in descriptors
    ]


def build_sync_rule_filter_type_options() -> list[SettingsOptionViewModel]:
    """Return selectable filter types for sync-rule editing.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return [
        SettingsOptionViewModel(value="directory", label="Directory"),
        SettingsOptionViewModel(value="file", label="File"),
    ]


def build_sync_rule_behavior_options() -> list[SettingsOptionViewModel]:
    """Return selectable include/exclude behaviors for sync-rule editing.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return [
        SettingsOptionViewModel(value="include", label="Include"),
        SettingsOptionViewModel(value="exclude", label="Exclude"),
    ]


def build_project_editor_sections() -> list[ProjectEditorSectionViewModel]:
    """Return the logical sections rendered in the project editor.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return [
        ProjectEditorSectionViewModel(
            key="general",
            title="General Settings",
            description="Core project identity, framework and active state.",
        ),
        ProjectEditorSectionViewModel(
            key="translation",
            title="Translation Settings",
            description="Locale defaults inherited from application settings.",
        ),
        ProjectEditorSectionViewModel(
            key="remote",
            title="Remote Connection Settings",
            description="Connection credentials and remote project path.",
        ),
        ProjectEditorSectionViewModel(
            key="sync",
            title="Sync Settings",
            description="Adapter filters and project-specific sync overrides.",
        ),
    ]


def _find_settings_section(section_key: str) -> SettingsSectionViewModel:
    """Find settings section.

    Args:
        section_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        LookupError:
            Raised when this callable hits the corresponding error path.
    """
    for section in build_settings_sections():
        if section.key == section_key:
            return section
    msg = f"Unknown settings section: {section_key}"
    raise LookupError(msg)


def _find_project_editor_section(section_key: str) -> ProjectEditorSectionViewModel:
    """Find project editor section.

    Args:
        section_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        LookupError:
            Raised when this callable hits the corresponding error path.
    """
    for section in build_project_editor_sections():
        if section.key == section_key:
            return section
    msg = f"Unknown project editor section: {section_key}"
    raise LookupError(msg)


def build_theme_mode_field() -> SettingsFieldViewModel:
    """Return metadata for the theme-mode settings control.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return SettingsFieldViewModel(
        key="theme_mode",
        label="Theme Mode",
        help_text=(
            "Choose the visual appearance that the Kivy shell should use by default."
        ),
        control_type="choice",
        options=[
            SettingsOptionViewModel(value="system", label="System"),
            SettingsOptionViewModel(value="light", label="Light"),
            SettingsOptionViewModel(value="dark", label="Dark"),
        ],
    )


def build_ui_language_field() -> SettingsFieldViewModel:
    """Return metadata for the UI language settings control.

    Returns:
        value:
            Structured value returned by this callable.
    """
    return SettingsFieldViewModel(
        key="ui_language",
        label="UI Language",
        help_text=(
            "Prepare the frontend for future localization without wiring "
            "translations yet."
        ),
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
    """Return the settings screen state for the current frontend configuration.

    Args:
        app_settings:
            Value supplied to this callable.
        status:
            Value supplied to this callable.
        status_message:
            Value supplied to this callable.
        selected_section_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
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


def select_project_editor_section(
    state: ProjectEditorStateViewModel,
    *,
    section_key: str,
) -> ProjectEditorStateViewModel:
    """Return the editor state with a different selected section.

    Args:
        state:
            Value supplied to this callable.
        section_key:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    selected_section = _find_project_editor_section(section_key)
    return ProjectEditorStateViewModel(
        mode=state.mode,
        title=state.title,
        submit_label=state.submit_label,
        sections=state.sections,
        selected_section_key=selected_section.key,
        selected_section_title=selected_section.title,
        selected_section_description=selected_section.description,
        editor=state.editor,
        framework_options=state.framework_options,
        connection_type_options=state.connection_type_options,
        sync_rule_filter_type_options=state.sync_rule_filter_type_options,
        sync_rule_behavior_options=state.sync_rule_behavior_options,
        connection_test_enabled=state.connection_test_enabled,
        connection_test_result=state.connection_test_result,
        sync_scope_status=state.sync_scope_status,
        sync_scope_message=state.sync_scope_message,
        status=state.status,
        status_message=state.status_message,
    )
