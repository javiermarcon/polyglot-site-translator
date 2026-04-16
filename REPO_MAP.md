# REPO_MAP.md

## Repository purpose

This repository hosts a Kivy-based application for translation auditing, source scanning, site/project management, optional remote connections, framework-aware extraction, and report generation.

---

## Expected top-level structure

This map describes the intended repository layout.
Update it whenever the structure changes.

### Root

- `src/`
  Main Python package(s) for the application.
  Current package: `polyglot_site_translator/`

- `tests/`
  Automated tests.

- `requirements/`
  Canonical dependency declaration directory.
  Runtime dependencies belong in `requirements/base.txt`.
  Dev/test-only dependencies belong in `requirements/dev.txt`.
  New third-party dependencies must not be introduced outside this strategy.

- `.github/`
  CI, automation, dependabot, repository workflows.

- `.gitignore`
  Ignore rules for Python, Kivy, build artifacts, caches, and local files.

- `pyproject.toml`
  Tooling configuration for linting, formatting, typing, and test integration.

- `LICENSE`
  Repository license.

- `README.md`
  High-level user/developer-facing introduction if present.

- `AGENTS.md`
  Operational rules for agents and contributors, including mandatory documentation alignment and dependency-declaration policy.

- `run_app.py`
  Local launcher for the src-layout application package without requiring editable installation.

---

## Expected `src/` responsibilities

Actual package naming may evolve, but responsibilities should remain clear.

Possible areas under `src/`:

- `app/` or equivalent
  - Kivy application bootstrap
  - screen registration
  - UI entrypoints

- `ui/`
  - Kivy screens
  - widgets
  - presentation glue only

Current frontend base:

- `polyglot_site_translator/app.py`
  Public Kivy app factory.

- `polyglot_site_translator/__main__.py`
  Executable GUI module.

- `polyglot_site_translator/bootstrap.py`
  Presentation-shell wiring and injectable service bundle assembly.

- `polyglot_site_translator/infrastructure/settings.py`
  TOML-backed settings persistence, validation, per-user config-path resolution, and persistence of general app settings such as the SQLite location.

- `polyglot_site_translator/infrastructure/sync_scope_sqlite.py`
  SQLite-backed persistence for shared global/framework sync rules and the `use_gitignore_rules` toggle used by sync scope resolution.

- `polyglot_site_translator/infrastructure/sync_gitignore.py`
  Supported translation of `.gitignore` patterns into sync exclusions.

- `polyglot_site_translator/infrastructure/remote_connections/base.py`
  Shared provider and reusable-session base classes, structured remote-operation errors, controlled connect retry behavior, bounded `list_remote_files()` materialization, and incremental traversal helpers.

- `polyglot_site_translator/infrastructure/database_location.py`
  Resolution and validation of the configured SQLite directory/filename into a final database path.

- `polyglot_site_translator/infrastructure/site_registry_sqlite.py`
  Real SQLite repository for the site registry, including schema setup, legacy FTP migration, related remote-connection persistence, persisted filtered-vs-full sync preference, persisted project sync-rule overrides, and configured runtime wiring from settings.

- `polyglot_site_translator/infrastructure/site_secrets.py`
  Local reversible encryption helper used to store remote passwords encrypted at rest.

- `polyglot_site_translator/domain/remote_connections/`
  Typed remote-connection descriptors, configs, session state, test results, and provider/session contracts.

- `polyglot_site_translator/domain/sync/`
  Typed sync direction, remote/local file descriptors, summaries, results, and explicit sync errors.

- `polyglot_site_translator/domain/sync/scope.py`
  Typed adapter-owned sync include/exclude specs, project-level override models, resolved rule catalogs, filter matching rules, and explicit resolved-scope outcomes.

- `polyglot_site_translator/domain/framework_detection/`
  Typed framework-detection contracts, result models, and explicit ambiguity errors.

- `polyglot_site_translator/domain/site_registry/`
  Typed site registry models, repository contracts, and explicit domain errors.

- `polyglot_site_translator/adapters/`
  Discoverable adapter base class, dynamic adapter registry, and concrete WordPress, Django, and Flask project detectors.

- `polyglot_site_translator/services/framework_detection.py`
  Registry-backed framework detection orchestration with path validation and framework catalog exposure.

- `polyglot_site_translator/services/framework_sync_scope.py`
  Explicit resolution of global sync rules, framework-level settings rules, adapter-defined include/exclude rules, optional `.gitignore` exclusions, and persisted project overrides from the current framework type, without hardcoding framework paths in generic sync services or Kivy UI modules.

- `polyglot_site_translator/services/site_registry.py`
  Site registry CRUD orchestration and validation independent from Kivy or SQLite details, with optional remote-connection integration and optional framework detection integration.

- `polyglot_site_translator/services/remote_connections.py`
  Validation, discoverable catalog exposure, and connection-test orchestration for remote connection providers.

- `polyglot_site_translator/services/project_sync.py`
  Bidirectional sync orchestration over the existing remote provider registry, including one reusable remote session per sync run, optional adapter-resolved sync scopes, typed results, and controlled failures.

- `polyglot_site_translator/domain/po_processing/`
  Typed PO processing models, contracts, and explicit domain/infrastructure errors.

- `polyglot_site_translator/services/po_processing.py`
  Shared PO workflow orchestration for discovery, locale-family grouping, and cross-variant translation synchronization.

- `polyglot_site_translator/infrastructure/po_files.py`
  Real PO repository based on `polib` for reading/writing project PO catalogs.

- `polyglot_site_translator/infrastructure/remote_connections/`
  Discoverable FTP/FTPS/SFTP/SCP provider implementations, reusable transport sessions, and the runtime provider registry.

- `polyglot_site_translator/infrastructure/sync_local.py`
  Local workspace directory creation, local file discovery/reads, and downloaded-file persistence for sync workflows.

- `polyglot_site_translator/presentation/contracts.py`
  UI-facing service protocols, including frontend settings operations and project-registry create/edit flows.

- `polyglot_site_translator/presentation/view_models.py`
  Typed dataclasses for dashboard, project list/detail, sync, audit, PO processing, settings, and project-editor sync rule catalogs.

- `polyglot_site_translator/presentation/frontend_shell.py`
  Navigation menu state, settings editing, project editor orchestration, project-editor preview refreshes, sync background execution state, and route-safe CRUD wiring independent from Kivy rendering.

- `polyglot_site_translator/presentation/fakes.py`
  Default runtime wiring for the real TOML + SQLite-backed frontend services. This module must not keep fake bundles for workflows that already have production implementations.

- `tests/support/frontend_doubles.py`
  Test-only frontend stubs/in-memory doubles for shell navigation, settings, and still-unfinished workflow behavior. Use these from tests and BDD steps instead of shipping fake bundles in `src/`.

- `polyglot_site_translator/presentation/kivy/`
  Thin Kivy `ScreenManager`, screens, and reusable widget area.

- `polyglot_site_translator/presentation/kivy/theme.py`
  Runtime theme palette tokens and active theme selection for the Kivy frontend.

- `polyglot_site_translator/presentation/kivy/settings_layout.py`
  Responsive layout rules for the settings screen so compact windows switch to a usable stacked layout.

- `polyglot_site_translator/presentation/kivy/screens/settings.py`
  Extensible settings screen with editable App / UI / Kivy settings plus general sync-rule administration for global rules, framework rules, and `.gitignore` integration.

- `polyglot_site_translator/presentation/kivy/screens/project_editor.py`
  Thin create/edit screen for site registry records driven entirely by typed presentation state, including the discoverable remote connection selector, the persisted "Use Adapter Sync Filters" switch, the visible sync-scope catalog, per-rule toggles, project-level rule editing, and the "Test Connection" action.

- `polyglot_site_translator/presentation/kivy/widgets/sync_progress_popup.py`
  Dedicated Kivy popup that renders background sync progress and a bounded command-log output without moving remote work into widgets.

- `polyglot_site_translator/presentation/kivy/widgets/path_picker.py`
  Kivy Garden `FileBrowser`-backed modal picker and path-input rows for local filesystem paths (for example project `local_path` and SQLite directory/filename fields). Directory pickers use a filter so listings show folders only, plus disabled filename/filter fields to keep that mode consistent.

- `services/`
  - use-case orchestration
  - audit flows
  - translation flows
  - FTP sync flows
  - site/project management flows

- `domain/`
  - models
  - findings
  - PO grouping/sync concepts
  - classification logic
  - shared contracts

- `adapters/` or `plugins/`
  - WordPress-specific behavior
  - Django-specific behavior
  - Flask-specific behavior
  - future framework-specific modules

- `infrastructure/`
  - SQLite repositories
  - FTP client adapters
  - filesystem access
  - translation provider adapters

- `reporting/`
  - Markdown output
  - JSON output
  - CSV output
  - generated snippets

- `config/`
  - settings
  - constants
  - tool wiring as needed

---

## `tests/` layout

Recommended structure:

- `tests/unit/`
- `tests/integration/`
- `tests/fixtures/`

Current frontend coverage:

- `tests/unit/presentation/`
- `tests/integration/presentation/`
- `tests/unit/infrastructure/test_remote_sync_providers.py`
- `tests/unit/infrastructure/test_site_secrets.py`
- `tests/unit/infrastructure/test_sqlite_site_registry_repository.py`
- `tests/unit/infrastructure/test_sync_local_workspace.py`
- `tests/unit/adapters/test_adapter_common.py`
- `tests/unit/adapters/test_framework_detection_registry.py`
- `tests/unit/adapters/test_wordpress_adapter.py`
- `tests/unit/adapters/test_django_adapter.py`
- `tests/unit/adapters/test_flask_adapter.py`
- `tests/unit/services/test_framework_detection_service.py`
- `tests/unit/services/test_project_sync_service.py`
- `tests/unit/services/test_framework_sync_scope_service.py`
- `tests/unit/presentation/test_site_registry_services.py`
- `tests/unit/presentation/test_sync_workflow_services.py`
- `tests/integration/presentation/test_project_editor_screen_runtime.py`
- `tests/integration/presentation/test_site_registry_flow.py`
- `tests/integration/presentation/test_framework_detection_flow.py`
- `tests/integration/presentation/test_sync_flow.py`
- `tests/unit/infrastructure/test_remote_connection_registry.py`
- `tests/unit/services/test_remote_connection_service.py`
- `tests/integration/presentation/test_remote_connection_editor_flow.py`
- `features/presentation/site_registry.feature`
- `features/presentation/framework_detection.feature`
- `features/presentation/remote_connections.feature`
- `features/presentation/sync.feature`
- `features/presentation/sync_filters.feature`
- `features/presentation/po_processing.feature`
- `features/steps/po_processing_steps.py`
- `tests/unit/services/test_po_processing_service.py`

If UI tests are added, they should remain isolated and clearly labeled.

---

## `requirements/`

Recommended split:

- `requirements/base.txt`
- `requirements/dev.txt`
- `requirements/production.txt` if truly needed later
- `requirements/android.txt` if packaging-specific dependencies become necessary

Treat this directory as the single source of truth for declared third-party dependencies.
Do not add Python standard-library modules here.
Keep this map updated if the strategy changes.

---

## Where to add new code

### New UI screen

Add under the UI/presentation package and wire it from the app entrypoint.
Update:

- `ARCHITECTURE.md`
- `REPO_MAP.md`
- `CODEBASE_ENTRYPOINTS.md`

### New shared service

Add under services/domain as appropriate.
Update:

- `ARCHITECTURE.md`
- `DOMAIN_MAP.md`
- `CODEBASE_ENTRYPOINTS.md`
- tests

### New framework adapter/plugin

Add under `adapters/` or `plugins/`.
Update:

- `ARCHITECTURE.md`
- `DOMAIN_MAP.md`
- `CODEBASE_ENTRYPOINTS.md`
- `ARCHITECTURE_DECISIONS.md` if the extension model changed
- tests

### New persistence/repository module

Add under infrastructure/persistence.
Update:

- `ARCHITECTURE.md`
- `REPO_MAP.md`
- tests

### New report format

Add under reporting.
Update:

- `ARCHITECTURE.md`
- `CODEBASE_ENTRYPOINTS.md`
- tests
- `ARCHITECTURE_GUARDRAILS.md` if new rules are needed

---

## Repository hygiene expectations

Any structural change must keep:

- module responsibilities explicit
- documentation aligned
- tests discoverable
- entrypoints documented

Current BDD frontend coverage lives in:

- `features/presentation/`
- `features/steps/`
