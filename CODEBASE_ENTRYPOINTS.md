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

---

## Service-level entrypoints

The application should expose use-case-oriented services such as:
- site/project registration and CRUD
- FTP synchronization
- PO audit/sync/translation
- source audit
- report generation
- adapter selection/dispatch

These services are the correct integration layer for the UI.

Current frontend-facing service entrypoints:
- `ProjectCatalogService.list_projects`
- `ProjectCatalogService.get_project_detail`
- `ProjectWorkflowService.start_sync`
- `ProjectWorkflowService.start_audit`
- `ProjectWorkflowService.start_po_processing`
- `SettingsService.load_settings`
- `SettingsService.save_settings`
- `SettingsService.reset_settings`
- `polyglot_site_translator.infrastructure.settings.build_default_settings_service`
- `polyglot_site_translator.infrastructure.settings.TomlSettingsService`

---

## Adapter/plugin entrypoints

The codebase should expose a clear registration or discovery mechanism for framework adapters/plugins.

Examples:
- adapter registry
- framework resolver
- plugin loader
- adapter factory

Framework adapters are responsible for target-specific discovery or extraction, not the shared orchestration flow.

---

## Domain entrypoints

Domain logic should be reachable through well-defined service or module interfaces, not through scattered helpers.

Examples of domain entrypoints:
- PO processing orchestrator
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
- `FrontendShell.select_settings_section`
- `FrontendShell.update_settings_draft`
- `FrontendShell.save_settings`
- `FrontendShell.restore_default_settings`

Current Kivy settings layout entrypoint:
- `polyglot_site_translator.presentation.kivy.settings_layout.build_settings_layout_spec`

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

---

## Infrastructure entrypoints

Infrastructure adapters should expose narrow interfaces for:
- FTP operations
- translation provider integration
- filesystem operations that need abstraction
- export writing

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
- `FrontendShell.open_settings`
- `FrontendShell.open_application_menu`
- `FrontendShell.open_route_from_menu`
- `FrontendShell.set_settings_theme_mode`
- `FrontendShell.set_settings_ui_language`
- `FrontendShell.toggle_remember_last_screen`
- `FrontendShell.toggle_developer_mode`
- `FrontendShell.select_settings_section`
- `FrontendShell.save_settings`
- `FrontendShell.restore_default_settings`

---

## CLI entrypoints

If the repository includes a CLI alongside the GUI, document commands and their owning modules here.
If no CLI exists yet, update this document when one is introduced.

---

## Maintenance rule

If a new screen, service, adapter, command, or major subsystem is introduced, update this file in the same patch.
