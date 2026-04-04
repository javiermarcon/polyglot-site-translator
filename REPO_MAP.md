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
