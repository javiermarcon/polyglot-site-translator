# ARCHITECTURE.md

## Project purpose

This repository contains a Kivy-based graphical application for managing translation and localization workflows across multiple frameworks and site/application types.

The application is expected to support:

- registration of sites/projects in SQLite
- FTP-based site download/synchronization
- auditing of source trees
- processing and synchronization of `.po/.mo`
- detection of untranslated or hardcoded strings
- generation of reports
- framework-specific extraction and discovery logic
- future cross-platform packaging considerations

---

## High-level architecture

The codebase should be organized around these layers:

1. **Presentation**
   - Kivy app
   - presentation shell / UI orchestrator
   - typed view models for screens and workflow panels
   - typed settings state and editable draft settings
   - Kivy runtime settings applier for theme and window behavior
   - runtime theme palette tokens for light and dark frontend modes
   - responsive layout rules for compact and desktop settings screens
   - navigation router and selected-project context
   - screens
   - widgets
   - user interaction
   - progress and feedback display

2. **Application services**
   - orchestrate workflows
   - coordinate repositories, scanners, translators, reporters, and adapters
   - expose use cases to the UI
   - validate and orchestrate site registry CRUD through explicit service contracts

3. **Domain logic**
   - shared PO processing
   - finding detection
   - report-ready normalization
   - site/project models
   - adapter contracts
   - typed site registry records and domain errors

4. **Framework adapters / plugins**
   - WordPress-specific discovery and extraction
   - Django-specific discovery and extraction
   - Flask-specific discovery and extraction
   - future target-specific behavior

5. **Infrastructure**
   - SQLite persistence
   - SQLite database-path resolution from frontend settings
   - local reversible encryption for persisted FTP passwords
   - TOML-backed frontend settings persistence
   - FTP access
   - filesystem IO
   - optional translation providers
   - serialization/export

---

## Main domains

### 1. Site registry

Stores user-managed site or project definitions and related metadata in SQLite.

Examples:
- site/project name
- local working directory
- framework type
- FTP host/user/path settings
- preferred locales
- audit/translation options
- active/inactive status
- encrypted FTP password at rest

Current first real implementation:
- `domain/site_registry/` defines typed models, contracts, and explicit errors
- `services/site_registry.py` validates and orchestrates CRUD use cases
- `infrastructure/site_registry_sqlite.py` owns schema creation, row mapping, and SQLite access
- `presentation/site_registry_services.py` adapts the real service into UI-facing catalog/editor workflows

### 2. FTP synchronization

Downloads or synchronizes site content from FTP sources into a local workspace suitable for scanning/auditing.

### 3. Shared PO processing

Responsible for:
- discovering `.po`
- extracting locales
- grouping families
- synchronizing existing translations
- reusing known translations
- optionally translating missing values
- optionally compiling `.mo`

This logic must remain reusable across framework adapters.

### 4. Framework adapters / plugins

Responsible for target-specific behavior such as:
- how to identify project type
- where to scan
- how to infer source roots
- how to extract database configuration
- how to discover framework conventions
- how to enrich findings with target-specific meaning

Examples:
- WordPress may parse `wp-config.php`
- Django may inspect `settings.py`, settings modules, or environment-backed settings
- Flask may rely on config modules, app factories, or environment conventions

### 5. Source auditing

Responsible for scanning source files such as:
- `.php`
- `.py`
- `.js`
- `.json`
- `.twig`
- `.tpl`
- `.html`
- `.jinja`
- other supported formats

for:
- hardcoded strings
- gettext misuse
- localization candidates
- textdomain or equivalent domain issues
- JSON i18n files
- template override or customization candidates where relevant

### 6. Reporting

Responsible for rendering normalized findings and summaries into:
- Markdown
- JSON
- CSV
- optional generated fallback snippets

---

## Architectural boundaries

### Presentation must not own domain logic

Kivy screens/widgets should never directly implement:
- FTP workflows
- SQLite queries
- parsing heuristics
- source scanners
- report formatting
- translation synchronization rules
- framework-specific extraction rules

The presentation layer may contain:
- typed screen state and workflow summaries
- typed settings sections and draft frontend settings
- Kivy-only runtime behavior such as applying theme palette tokens and window size
- a thin router for navigation state
- a presentation shell/controller that coordinates service contracts
- fake or mockable service bundles for local UI development and tests

Frontend settings persistence remains behind the `SettingsService` contract and is now implemented at runtime through a TOML-backed infrastructure service. Kivy screens still edit typed drafts and delegate save/load/reset operations through the presentation shell.

The general settings flow now also owns:
- `database_directory`
- `database_filename`

The final SQLite path is resolved in infrastructure from typed settings. Widgets never compose the database path manually.

### Shared services must remain target-agnostic where feasible

Common services must not hardcode WordPress, Django, or Flask assumptions when those belong in adapters/plugins.

### Adapters must isolate framework behavior

Framework-specific discovery, config parsing, and conventions belong in adapter/plugin modules.

### Infrastructure must not format UI

Repositories, FTP clients, and scanner backends must return structured data rather than UI-ready text.

### Reporting must not discover data

Report modules must render findings produced by scanners/services, not scan files directly.

---

## Typical workflow: audit

1. User selects a site/project from the UI.
2. The presentation shell resolves the selected project context and invokes an application service contract.
3. The service resolves site configuration from SQLite.
4. The service loads the appropriate framework adapter/plugin.
5. The service scans the local working directory or synchronized copy.
6. Domain scanners and the adapter produce normalized findings.
7. Report services aggregate and export findings.
8. UI displays summary and export location.

---

## Typical workflow: PO sync/translation

1. User selects a site/project and locales.
2. The presentation shell invokes a PO processing service contract.
3. The service optionally asks the adapter for relevant scan roots or conventions.
4. The service discovers relevant `.po` files.
5. Files are grouped by family and locale.
6. Existing translations are synchronized across variants.
7. Missing entries are reused or translated through configured providers.
8. `.po` and optionally `.mo` outputs are written.
9. UI presents stats and outputs.

---

## Typical workflow: target-specific extraction

1. User selects a site/project.
2. UI or service resolves the project framework type.
3. The matching adapter/plugin runs extraction logic.
4. Adapter returns normalized data for use by shared services.
5. Shared services continue from normalized contracts rather than raw framework-specific structures.

---

## Future-oriented architectural expectations

The repository should be able to evolve toward:
- multiple translation providers
- multiple storage backends if needed
- background job execution
- richer site/project metadata
- platform-aware packaging workflows
- additional framework adapters/plugins
- additional scanners

Any such change must preserve existing boundaries.

---

## Current frontend base

The current repository baseline includes a first Kivy frontend shell under `src/polyglot_site_translator/`.

Key responsibilities:

- `app.py` and `__main__.py` expose the graphical entrypoint.
- `bootstrap.py` wires the presentation shell with injectable service contracts.
- `presentation/contracts.py` defines UI-facing protocols for project catalog and workflow actions.
- `presentation/view_models.py` defines typed dataclasses for dashboard, projects, project detail, sync, audit, and PO processing states.
- `presentation/frontend_shell.py` centralizes navigation-safe orchestration without embedding infrastructure logic in widgets.
- `presentation/frontend_shell.py` now also owns the grouped application menu state and contextual route enabling.
- `presentation/fakes.py` provides deterministic in-memory services for the initial frontend shell, BDD scenarios, and unit tests.
- `presentation/fakes.py` also exposes a default runtime bundle that keeps fake workflow services but swaps the project catalog/editor flows to the real SQLite-backed site registry.
- `presentation/kivy/` contains thin `ScreenManager` wiring and screen classes that render already-prepared state.
- `presentation/contracts.py` now also defines a settings contract for frontend configuration workflows.
- `presentation/contracts.py` now also defines a project-registry management contract for create/edit flows.
- `presentation/view_models.py` now includes extensible settings sections and typed app/UI/Kivy settings.
- `presentation/view_models.py` now also includes typed project-editor view models and SQLite location settings fields.
- `presentation/kivy/screens/settings.py` exposes the initial configuration screen for frontend behavior using a sectioned layout and typed field metadata.
- `presentation/kivy/screens/project_editor.py` exposes a thin create/edit screen for site registry records.

Current site registry runtime flow:
1. `app.py` builds the default frontend services with TOML settings and a configured SQLite repository.
2. `ConfiguredSqliteSiteRegistryRepository` resolves the database location from persisted general settings.
3. `SqliteSiteRegistryRepository` ensures the schema and persists typed `RegisteredSite` records.
4. `SiteRegistryPresentationCatalogService` and `SiteRegistryPresentationManagementService` adapt CRUD use cases to UI-facing view models.
5. Kivy screens invoke the presentation shell only; they do not import or execute SQL.
