# CODEBASE_ENTRYPOINTS.md

## Purpose

This document identifies the main entrypoints and execution paths of the codebase.
Update it whenever execution paths or module wiring changes.

---

## Main runtime entrypoints

### Graphical application entrypoint

The repository should have one clear Kivy application entrypoint under `src/`.

Its responsibilities should be limited to:

- bootstrapping the app
- wiring screens
- initializing high-level services/configuration
- starting the event loop

It must not contain:

- raw SQL
- FTP logic
- scanning heuristics
- PO synchronization rules
- framework-specific extraction internals
- report formatting internals

Current entrypoints:

- `polyglot_site_translator.app:create_kivy_app`
- `polyglot_site_translator.__main__:main`
- `run_app.py`
- `polyglot_site_translator.presentation.kivy.app.PolyglotSiteTranslatorApp.apply_runtime_settings`
- `polyglot_site_translator.presentation.kivy.app.PolyglotSiteTranslatorApp._install_runtime_error_handlers`

Default runtime wiring:

- `polyglot_site_translator.app:create_kivy_app` must boot the graphical app with the real TOML settings service and SQLite-backed site registry services unless a test/development bundle is injected explicitly.
- `polyglot_site_translator.app:create_kivy_app` must also set the safe Kivy file-log default before importing Kivy-heavy runtime modules.
- `PolyglotSiteTranslatorApp` owns the installation of global exception routing for uncaught main-thread exceptions, worker-thread exceptions, and Kivy callback failures.

---

## Service-level entrypoints

The application should expose use-case-oriented services such as:

- site/project registration and CRUD
- remote connection catalog and test orchestration
- remote synchronization
- PO audit/sync/translation
- source audit
- report generation
- adapter selection/dispatch

These services are the correct integration layer for the UI.

Current frontend-facing service entrypoints:

- `ProjectCatalogService.list_projects`
- `ProjectCatalogService.get_project_detail`
- `ProjectRegistryManagementService.build_create_project_editor`
- `ProjectRegistryManagementService.build_edit_project_editor`
- `ProjectRegistryManagementService.preview_project_editor`
- `ProjectRegistryManagementService.create_project`
- `ProjectRegistryManagementService.update_project`
- `ProjectRegistryManagementService.test_remote_connection`
- `ProjectWorkflowService.start_sync`
- `ProjectWorkflowService.start_sync_to_remote`
- `FrontendShell.start_sync_async`
- `FrontendShell.start_sync_to_remote_async`
- `ProjectWorkflowService.start_audit`
- `ProjectWorkflowService.start_po_processing`
- `polyglot_site_translator.services.po_processing.POProcessingService.process_site`
- `polyglot_site_translator.infrastructure.po_files.PolibPOCatalogRepository.discover_po_files`
- `polyglot_site_translator.infrastructure.po_files.PolibPOCatalogRepository.save_po_files`
- `SettingsService.load_settings`
- `SettingsService.save_settings`
- `SettingsService.reset_settings`
- `polyglot_site_translator.infrastructure.settings.build_default_settings_service`
- `polyglot_site_translator.infrastructure.settings.TomlSettingsService`
- `polyglot_site_translator.services.framework_sync_scope.FrameworkSyncScopeService.resolve_for_site`
- `polyglot_site_translator.services.framework_sync_scope.FrameworkSyncScopeService.resolve_for_framework`
- `polyglot_site_translator.services.framework_sync_scope.SyncScopeResolutionService`
- `polyglot_site_translator.services.framework_detection.FrameworkDetectionService.detect_project`
- `polyglot_site_translator.services.framework_detection.FrameworkDetectionService.list_supported_frameworks`
- `polyglot_site_translator.services.project_sync.ProjectSyncService.sync_remote_to_local`
- `polyglot_site_translator.services.project_sync.ProjectSyncService.sync_local_to_remote`
- `polyglot_site_translator.services.remote_connections.RemoteConnectionService.list_supported_connection_types`
- `polyglot_site_translator.services.remote_connections.RemoteConnectionService.test_connection`
- `polyglot_site_translator.infrastructure.site_secrets.LocalKeySiteSecretCipher.decrypt`
- `polyglot_site_translator.infrastructure.site_registry_sqlite.SqliteSiteRegistryRepository.fetch_encrypted_password`
- `polyglot_site_translator.infrastructure.remote_connections.base.RemoteConnectionOperationError`

---

## Adapter/plugin entrypoints

The codebase should expose a clear registration or discovery mechanism for framework adapters/plugins.

Examples:

- adapter registry
- framework resolver
- plugin loader
- adapter factory

Framework adapters are responsible for target-specific discovery or extraction, not the shared orchestration flow.

Current adapter entrypoints:

- `polyglot_site_translator.adapters.base.BaseFrameworkAdapter`
- `polyglot_site_translator.adapters.base.BaseFrameworkAdapter.get_sync_filters`
- `polyglot_site_translator.adapters.base.BaseFrameworkAdapter.get_sync_scope`
- `polyglot_site_translator.adapters.framework_registry.FrameworkAdapterRegistry`
- `polyglot_site_translator.adapters.framework_registry.FrameworkAdapterRegistry.discover_installed`
- `polyglot_site_translator.adapters.framework_registry.FrameworkAdapterRegistry.list_framework_descriptors`
- `polyglot_site_translator.adapters.wordpress.WordPressFrameworkAdapter`
- `polyglot_site_translator.adapters.django.DjangoFrameworkAdapter`
- `polyglot_site_translator.adapters.flask.FlaskFrameworkAdapter`
- `polyglot_site_translator.services.framework_detection.FrameworkDetectionService.detect_project`
- `polyglot_site_translator.services.framework_detection.FrameworkDetectionService.list_supported_frameworks`

---

## Domain entrypoints

Domain logic should be reachable through well-defined service or module interfaces, not through scattered helpers.

Examples of domain entrypoints:

- PO processing orchestrator
- PO translation provider contract
- source scan orchestrator
- finding classifier
- report summary builder
- framework adapter contract definitions

Current presentation orchestration entrypoint:

- `polyglot_site_translator.bootstrap:create_frontend_shell`

Current navigation entrypoint:

- `polyglot_site_translator.presentation.frontend_shell.FrontendShell`

Current settings orchestration entrypoints:

- `FrontendShell.open_settings`
- `FrontendShell.open_application_menu`
- `FrontendShell.open_route_from_menu`
- `FrontendShell.set_settings_default_project_locale`
- `FrontendShell.set_settings_database_directory`
- `FrontendShell.set_settings_database_filename`
- `FrontendShell.select_settings_section`
- `FrontendShell.update_settings_draft`
- `FrontendShell.save_settings`
- `FrontendShell.restore_default_settings`
- `polyglot_site_translator.presentation.kivy.screens.settings.SettingsScreen`
- `FrontendShell.start_sync_async` resolves the configured sync command-log limit before opening progress state for the popup
- `FrontendShell.start_sync_to_remote_async` resolves the same limit before starting the upload popup state

Current project-registry orchestration entrypoints:

- `FrontendShell.open_project_editor_create`
- `FrontendShell.open_project_editor_edit`
- `FrontendShell.select_project_editor_section`
- `FrontendShell.save_new_project`
- `FrontendShell.save_project_edits`
- `FrontendShell.test_project_connection`
- `FrontendShell.start_sync_async`
- `FrontendShell.start_sync_to_remote_async`
- `polyglot_site_translator.presentation.site_registry_services.SiteRegistryPresentationWorkflowService.start_sync`
- `polyglot_site_translator.presentation.site_registry_services.SiteRegistryPresentationWorkflowService.start_sync_to_remote`
- `polyglot_site_translator.presentation.site_registry_services.SiteRegistryPresentationManagementService._build_service_payload`
- `polyglot_site_translator.presentation.site_registry_services.SiteRegistryPresentationManagementService._build_site_editor`
- `polyglot_site_translator.presentation.kivy.screens.project_editor.ProjectEditorScreen._select_project_editor_section` preserves the current draft before switching tabs so the sectioned editor behaves like one logical form
- `polyglot_site_translator.services.project_sync.ProjectSyncService.sync_remote_to_local`
- `polyglot_site_translator.services.project_sync.ProjectSyncService.sync_local_to_remote`
- `polyglot_site_translator.domain.remote_connections.contracts.RemoteConnectionProvider.open_session`

Current project-detail enrichment entrypoints:

- `polyglot_site_translator.services.site_registry.SiteRegistryService.detect_framework`
- `polyglot_site_translator.services.framework_detection.FrameworkDetectionService.detect_project`
- `polyglot_site_translator.presentation.site_registry_services.SiteRegistryPresentationCatalogService.get_project_detail`
- `polyglot_site_translator.presentation.site_registry_services.SiteRegistryPresentationManagementService.create_project`
- `polyglot_site_translator.presentation.site_registry_services.SiteRegistryPresentationManagementService.update_project`

Current Kivy settings layout entrypoint:

- `polyglot_site_translator.presentation.kivy.settings_layout.build_settings_layout_spec`

Current Kivy sync-progress entrypoint:

- `polyglot_site_translator.presentation.kivy.widgets.sync_progress_popup.SyncProgressPopup`

Current Kivy local path picker entrypoint:

- `polyglot_site_translator.presentation.kivy.widgets.path_picker.show_path_picker_popup`

---

## Persistence entrypoints

SQLite access should be centralized behind repositories or persistence services.

Possible examples:

- site repository
- settings repository
- scan history repository if added later

Current frontend settings persistence entrypoints:

- `polyglot_site_translator.infrastructure.settings.resolve_user_config_dir`
- `polyglot_site_translator.infrastructure.settings.build_default_settings_service`
- `polyglot_site_translator.infrastructure.settings.TomlSettingsService.load_settings`
- `polyglot_site_translator.infrastructure.settings.TomlSettingsService.save_settings`
- `polyglot_site_translator.infrastructure.settings.TomlSettingsService.reset_settings`
- `polyglot_site_translator.infrastructure.sync_gitignore.load_gitignore_sync_rules`

Current shared sync-scope persistence entrypoints:

- `polyglot_site_translator.infrastructure.database_location.resolve_sqlite_database_location`
- `polyglot_site_translator.infrastructure.sync_scope_sqlite.SqliteSyncScopeRepository`
- `polyglot_site_translator.infrastructure.sync_scope_sqlite.ConfiguredSqliteSyncScopeRepository`

Current site-registry persistence entrypoints:

- `polyglot_site_translator.infrastructure.database_location.resolve_sqlite_database_location`
- `polyglot_site_translator.infrastructure.site_registry_sqlite.SqliteSiteRegistryRepository`
- `polyglot_site_translator.infrastructure.site_registry_sqlite.ConfiguredSqliteSiteRegistryRepository`
- `polyglot_site_translator.infrastructure.site_secrets.LocalKeySiteSecretCipher`
- `polyglot_site_translator.infrastructure.remote_connections.registry.RemoteConnectionRegistry`
- `polyglot_site_translator.infrastructure.remote_connections.registry.RemoteConnectionRegistry.discover_installed`
- `polyglot_site_translator.infrastructure.sync_local.LocalSyncWorkspace`
- `polyglot_site_translator.infrastructure.site_registry_sqlite.SqliteSiteRegistryRepository._ensure_remote_table`

---

## Infrastructure entrypoints

Infrastructure adapters should expose narrow interfaces for:

- FTP operations
- translation provider integration
- filesystem operations that need abstraction
- export writing

Current PO-processing entrypoints:

- `polyglot_site_translator.services.po_processing.POProcessingService.process_site`
- `polyglot_site_translator.infrastructure.po_files.PolibPOCatalogRepository.discover_po_files`
- `polyglot_site_translator.infrastructure.po_files.PolibPOCatalogRepository.save_po_files`
- `polyglot_site_translator.infrastructure.po_translator_googletrans.GoogleTransPOTranslationProvider.translate_text`
- `polyglot_site_translator.domain.po_processing.errors.POProcessingTranslationError`

---

## Reporting entrypoints

Report generation should have explicit entrypoints per format or strategy, for example:

- Markdown report writer
- CSV report writer
- JSON report writer
- generated fallback snippet writer

---

## Test entrypoints

Important test-covered entrypoints should include:

- service orchestration
- adapter registration/dispatch
- scanner APIs
- repository APIs
- report writers
- CLI commands if present

Current frontend test-covered entrypoints:

- `FrontendShell.open_dashboard`
- `FrontendShell.open_projects`
- `FrontendShell.select_project`
- `FrontendShell.start_sync`
- `FrontendShell.start_audit`
- `FrontendShell.start_po_processing`
- `SiteRegistryPresentationWorkflowService.start_po_processing`
- `FrontendShell.open_settings`
- `FrontendShell.open_application_menu`
- `FrontendShell.open_route_from_menu`
- `FrontendShell.open_project_editor_create`
- `FrontendShell.open_project_editor_edit`
- `FrontendShell.save_new_project`
- `FrontendShell.save_project_edits`
- `FrontendShell.set_settings_theme_mode`
- `FrontendShell.set_settings_ui_language`
- `FrontendShell.set_settings_database_directory`
- `FrontendShell.set_settings_database_filename`
- `FrontendShell.toggle_remember_last_screen`
- `FrontendShell.toggle_developer_mode`
- `FrontendShell.select_settings_section`
- `FrontendShell.save_settings`
- `FrontendShell.restore_default_settings`
- `FrontendShell.start_sync_async`

---

## CLI entrypoints

If the repository includes a CLI alongside the GUI, document commands and their owning modules here.
If no CLI exists yet, update this document when one is introduced.

---

## Maintenance rule

If a new screen, service, adapter, command, or major subsystem is introduced, update this file in the same patch.
