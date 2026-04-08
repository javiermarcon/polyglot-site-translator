# REPO_MAP.md

## Repository purpose

This repository hosts a Kivy-based application for translation auditing, source scanning, site/project management, FTP synchronization, framework-aware extraction, and report generation.

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
  Dependency files split by environment or purpose.

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
  TOML-backed settings persistence, validation, and per-user config-path resolution.

- `polyglot_site_translator/infrastructure/database_location.py`
  Resolution and validation of the configured SQLite directory/filename into a final database path.

- `polyglot_site_translator/infrastructure/site_registry_sqlite.py`
  Real SQLite repository for the site registry, including schema setup and configured runtime wiring from settings.

- `polyglot_site_translator/infrastructure/site_secrets.py`
  Local reversible encryption helper used to store FTP passwords encrypted at rest.

- `polyglot_site_translator/domain/site_registry/`
  Typed site registry models, repository contracts, and explicit domain errors.

- `polyglot_site_translator/services/site_registry.py`
  Site registry CRUD orchestration and validation independent from Kivy or SQLite details.

- `polyglot_site_translator/presentation/contracts.py`
  UI-facing service protocols, including frontend settings operations and project-registry create/edit flows.

- `polyglot_site_translator/presentation/view_models.py`
  Typed dataclasses for dashboard, project list/detail, sync, audit, PO processing, and settings.

- `polyglot_site_translator/presentation/frontend_shell.py`
  Navigation menu state, settings editing, project editor orchestration, and route-safe CRUD wiring independent from Kivy rendering.

- `polyglot_site_translator/presentation/fakes.py`
  In-memory fake services used by the frontend shell and tests, plus seeded fake catalog/workflow wiring with injectable settings persistence.

- `polyglot_site_translator/presentation/kivy/`
  Thin Kivy `ScreenManager`, screens, and reusable widget area.

- `polyglot_site_translator/presentation/kivy/theme.py`
  Runtime theme palette tokens and active theme selection for the Kivy frontend.

- `polyglot_site_translator/presentation/kivy/settings_layout.py`
  Responsive layout rules for the settings screen so compact windows switch to a usable stacked layout.

- `polyglot_site_translator/presentation/kivy/screens/settings.py`
  Extensible settings screen with the initial App / UI / Kivy section, including editable SQLite directory/filename fields.

- `polyglot_site_translator/presentation/kivy/screens/project_editor.py`
  Thin create/edit screen for site registry records driven entirely by typed presentation state.

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
- `tests/unit/infrastructure/test_site_secrets.py`
- `tests/unit/infrastructure/test_sqlite_site_registry_repository.py`
- `tests/unit/presentation/test_site_registry_services.py`
- `tests/integration/presentation/test_project_editor_screen_runtime.py`
- `tests/integration/presentation/test_site_registry_flow.py`
- `features/presentation/site_registry.feature`

If UI tests are added, they should remain isolated and clearly labeled.

---

## `requirements/`

Recommended split:

- `requirements/base.txt`
- `requirements/dev.txt`
- `requirements/production.txt` if truly needed later
- `requirements/android.txt` if packaging-specific dependencies become necessary

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
