# Polyglot Site Translator

Kivy-based graphical application for auditing, translating, and managing
multi-framework site/project localization workflows.

Spanish documentation is maintained in [README_es.md](README_es.md). Any
user-facing or developer-facing change must update both README files in the
same patch.

## Current Status

The repository is in an early but functional stage. It currently includes:

- a Kivy frontend under `src/polyglot_site_translator/`
- screen navigation with `ScreenManager`
- dashboard, projects, project detail, project editor, sync, audit, and PO
  processing screens
- a small Kivy design system with centralized spacing, typography, radius,
  component sizes, surfaces, actions, and reusable form widgets
- gettext-backed UI localization with English as the default language and a
  dynamic language selector based on packaged `.po` and `.mo` catalogs
- UI service contracts and typed presentation view models
- TOML-backed persistence for general application settings
- TOML-backed `Translation Settings` defaults for new projects:
  `default_project_locale`, `default_compile_mo`,
  `default_use_external_translator`, `default_use_translation_cache`,
  `translation_cache_path`, `default_only_fuzzy`, `default_dry_run`,
  `default_stats_only`, and `default_report_inconsistencies`
- SQLite-backed `site_registry` persistence
- SQLite-backed shared sync rules (`global` / `framework`) and
  `use_gitignore_rules`
- configurable SQLite database directory and filename
- reversible local encryption for remote passwords persisted in SQLite
- optional remote connections stored separately from project metadata
- discoverable remote connection types with an explicit `No Remote Connection`
  option
- structured connection tests for `ftp`, `ftps_explicit`, `ftps_implicit`,
  `sftp`, and `scp`
- real bidirectional sync over the project's persisted remote connection
- real `remote -> local` downloads into `local_path`, including automatic local
  directory creation
- real `local -> remote` uploads, including automatic remote directory creation
- adapter/framework sync filters reused by both sync directions
- framework-specific sync includes/excludes, such as `.venv/` and
  `__pycache__/` for Python stacks
- a persisted per-project choice between filtered sync and full sync
- a general UI for shared global/framework sync rules
- optional `.gitignore`-derived sync exclusions
- a visible resolved sync-scope catalog in the project editor
- project-level sync rule overrides
- typed sync results with file counts and stable error codes
- background sync execution from Project Detail with a dedicated progress
  window and bounded operation log
- automatic migration of legacy `ftp_*` columns into related remote connection
  records
- a real framework-detection adapter registry
- effective WordPress, Django, and Flask detection from `local_path`
- dynamic adapter auto-discovery at runtime
- a real PO translation workflow with `.po` discovery, family grouping,
  reuse across files/families, optional persistent translation cache, optional
  external translation, and `.mo` compilation
- a `Translate` action with a pre-run popup for locale and per-run option
  overrides
- progress based on completed gettext entries
- traceable PO progress with current file and current `msgid`
- gettext identity support through `msgctxt`, `msgid`, and `msgid_plural`
- PO processing summaries equivalent to the legacy `ProcessStats` metrics
- explicit skipping of hashtag-like slug tokens before external translation
- typed controlled failures for framework detection, sync scope, persisted
  settings, remote providers, corrupted SQLite secrets, and PO translation
  provider errors
- visible recovery for uncaught main-thread, background-thread, and Kivy
  callback failures when the application can continue safely
- real persisted writes to workspace `.po` files
- real main project flows through persisted `site_registry`
- normalized validation for one or more project default locales
- a Kivy Garden `FileBrowser` path picker for local folders/files
- a packaged Material Icons font for stable UI icons
- BDD scenarios and presentation/orchestration tests
- architecture documentation for future iterations

Not yet fully implemented:

- advanced selective-sync profiles by environment or direction
- the production source-audit scanner
- final report generation

## Goals

The application is intended to provide a graphical shell that can grow without
large rewrites as more production services are added.

The design prioritizes:

- keeping UI separate from domain and infrastructure logic
- supporting shared framework-agnostic services
- isolating framework-specific behavior behind adapters/plugins
- strict typing and testability
- clear extension paths for localization, auditing, sync, and reporting

## Architecture Summary

The expected architecture is layered:

1. Presentation
2. Application services
3. Domain logic
4. Framework adapters / plugins
5. Infrastructure

Current important modules:

- `app.py` and `__main__.py`: graphical application entrypoints
- `bootstrap.py`: frontend shell wiring
- `domain/site_registry/`: typed site-registry models, contracts, and errors
- `domain/remote_connections/`: remote connection models, contracts, and test
  results
- `domain/sync/`: sync directions, file descriptors, summaries, results, and
  explicit errors
- `domain/sync/scope.py`: adapter sync filters, global/framework rules,
  resolved catalogs, project overrides, and reusable scopes
- `domain/framework_detection/`: framework detection contracts, typed results,
  and ambiguity errors
- `domain/po_processing/`: shared PO processing models, contracts, and errors
- `services/site_registry.py`: site registry validation and CRUD orchestration
- `services/remote_connections.py`: remote catalog, validation, and connection
  tests
- `services/project_sync.py`: real bidirectional sync with typed progress and
  controlled errors
- `services/framework_detection.py`: adapter-registry-backed detection
- `services/framework_sync_scope.py`: framework/adapter sync-scope resolution
- `services/po_processing.py`: PO discovery, family grouping, and translation
  synchronization
- `adapters/base.py`: discoverable framework adapter contract
- `adapters/framework_registry.py`: dynamic adapter registry and resolver
- `adapters/wordpress.py`, `adapters/django.py`, `adapters/flask.py`:
  framework-specific detection and structured evidence
- `infrastructure/settings.py`: TOML-backed per-user settings persistence
- `infrastructure/database_location.py`: final SQLite path resolution
- `infrastructure/site_registry_sqlite.py`: real SQLite repository
- `infrastructure/remote_connections/`: discoverable FTP/FTPS/SFTP/SCP
  providers
- `infrastructure/sync_local.py`: local workspace preparation and local file IO
- `infrastructure/po_files.py`: `polib`-backed `.po` read/write and `.mo`
  compilation
- `infrastructure/site_secrets.py`: local encrypted secret handling
- `presentation/contracts.py`: UI-facing service contracts
- `presentation/view_models.py`: typed screen and panel models
- `presentation/ui_localization.py`: gettext catalog discovery, active UI
  language, and dynamic language options
- `presentation/locale/`: packaged `.po` and `.mo` UI catalogs
- `presentation/frontend_shell.py`: navigation and state orchestration
- `presentation/site_registry_services.py`: adapter between real services and
  UI-facing project workflows
- `presentation/kivy/`: app, screens, widgets, design tokens, and theme
  handling

The UI must not talk directly to:

- SQLite
- FTP/SFTP/SCP clients
- scanners
- concrete adapters
- `.po` parsers
- report writers

## Frontend Behavior

The frontend includes:

- Dashboard as the main entry point
- Projects list backed by persisted SQLite records
- Project Detail enriched with framework detection metadata
- Project Editor with `General Settings`, `Translation Settings`,
  `Remote Connection Settings`, and `Sync Settings`
- a `Test Connection` action resolved through services
- bidirectional sync summary screens and progress popup
- audit preview backed by framework detection
- real PO processing summary and pre-run `Translate` popup
- general Settings with TOML persistence and translation defaults
- a dynamic `UI Language` selector backed by packaged gettext catalogs

The selected project context is preserved across navigation. The main
create/list/detail/update, bidirectional sync, and PO-processing flows use real
services; unfinished audit behavior remains behind the same UI-facing
contracts.

## UI Localization

English is the default UI language. Runtime-selectable UI languages are
discovered from compiled gettext catalogs under:

```text
src/polyglot_site_translator/presentation/locale/<language>/LC_MESSAGES/
```

Each language must provide:

```text
polyglot_site_translator.po
polyglot_site_translator.mo
```

Adding a new language means adding both files and packaging them. The selector
shows the language automatically when the compiled `.mo` is present.

Operator-facing UI strings, including presentation summaries and framework
evidence displayed in the UI, must pass through the presentation localization
helpers or reusable localized Kivy widgets. Operational command logs such as
`SFTP GET` and filesystem paths remain raw diagnostic output.

## Repository Structure

```text
src/
  polyglot_site_translator/
    app.py
    __main__.py
    bootstrap.py
    adapters/
    domain/
    infrastructure/
    presentation/
    services/
tests/
features/
requirements/
README.md
README_es.md
```

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements/dev.txt
```

Kivy may require OS-level graphical dependencies depending on your platform.

## Running The App

From the repository root:

```bash
.venv/bin/python run_app.py
```

The graphical entrypoint uses real TOML settings and SQLite-backed
`site_registry` services by default.

General settings are stored in `settings.toml` under the user config directory.
For development or tests, override that directory with:

```bash
POLYGLOT_SITE_TRANSLATOR_CONFIG_DIR=/path/to/config
```

The settings file stores values such as `ui_language`,
`default_project_locale`, translation defaults, `database_directory`,
`database_filename`, and `sync_progress_log_limit`.

## Sync Behavior

The sync workflow uses the project's persisted remote connection to list,
download, upload, and create directories. Work runs in the background from
Project Detail and opens a dedicated progress window.

The command log is bounded by `sync_progress_log_limit`. Remote traversal is
incremental, and a single reusable remote session is used for a full sync run.

SFTP/SCP host-key verification is enabled by default. Unknown host keys fail
with a controlled `unknown_ssh_host_key` error and can be explicitly trusted
through the shared confirmation popup.

## Testing And Validation

Recommended commands:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy src tests features/steps
.venv/bin/python tests/run_docstring_audit.py
.venv/bin/python -m pytest
.venv/bin/python -m behave features/presentation/frontend_shell.feature features/presentation/settings.feature features/presentation/site_registry.feature features/presentation/framework_detection.feature features/presentation/remote_connections.feature features/presentation/sync.feature features/presentation/sync_filters.feature features/presentation/po_processing.feature
```

The repository follows mandatory BDD + TDD for non-trivial work:

1. define the use case
2. define acceptance criteria
3. add or update BDD scenarios
4. add or update unit/integration tests
5. confirm tests fail before implementation
6. implement the minimum change
7. refactor after green
8. update architecture and operational docs

When changing user-visible behavior, update both `README.md` and
`README_es.md` in the same patch.

## Architecture Rules

- keep Kivy screens and widgets thin
- keep SQL, networking, parsing, scanning, translation memory, and reporting
  outside the UI
- keep shared services framework-agnostic
- keep framework-specific rules in adapters
- do not hardcode remote connection catalogs or UI language catalogs in screens
- do not add dependencies outside `requirements/`
- introduce instance attributes only in `__init__`
- keep Python `assert` statements limited to pytest tests under `tests/`
- use temporary-directory fixtures instead of hardcoded `/tmp` paths in tests
- expose public observation APIs instead of accessing protected members across
  class boundaries
- avoid mutable global runtime state
- keep PEP8, PEP257, PEP484, Ruff, mypy, tests, and docstring audit green

## License

See [LICENSE](LICENSE).
