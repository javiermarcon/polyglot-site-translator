# AI_CONTEXT.md

## Repository summary

This repository contains a Kivy-based application for localization workflows across multiple frameworks and site/application types.

It combines:

- site registration
- SQLite persistence
- optional remote connection management and testing
- FTP/FTPS/SFTP/SCP download/synchronization
- shared translation services
- source auditing
- framework-specific adapters
- report generation

The project is intended to remain cross-platform friendly and maintainable over time.

---

## What matters most

When changing this codebase, prioritize:

1. separation of concerns
2. explicit typing
3. testability
4. framework-agnostic shared services
5. isolated framework-specific adapters
6. Kivy UI thinness
7. explicit error handling
8. documentation consistency

---

## Conceptual domains

- **Site registry**: local records for managed sites
- **Remote connections**: optional typed remote configs and connection tests
- **FTP sync**: remote site download/update workflows
- **Common translation services**: PO discovery, sync, translation, compilation, reporting-ready outputs
- **Framework adapters**: WordPress, Django, Flask, and future target-specific discovery/parsing rules
- **Source auditing**: scan code/templates/assets for localization issues
- **Reporting**: turn normalized findings into usable outputs
- **Presentation**: Kivy screens and user interactions

---

## Practical rules for future changes

- Keep the Kivy layer thin.
- Push business/domain logic into services and dedicated modules.
- Push IO/integration concerns into infrastructure modules.
- Keep translation providers behind explicit contracts and infrastructure adapters.
- Model findings and important records explicitly.
- Keep shared services framework-agnostic when feasible.
- Put target-specific rules into adapters/plugins.
- Add tests with every meaningful feature or bugfix.
- Update architectural docs whenever structure or flows change.

---

## Expected implementation style

- small modules
- typed models
- explicit services
- clean repository boundaries
- separate reporting layer
- pluggable adapter architecture
- repository documentation kept current

---

## Common mistakes to avoid

- embedding FTP logic in screens
- hardcoding remote connection types in widgets
- embedding SQL in views/widgets
- generating reports inside scanners
- hardcoding WordPress assumptions in shared modules
- adding new target frameworks without adapter boundaries
- adding new formats without tests
- changing architecture without updating docs

---

## Entry points to inspect first

Before making changes, inspect at least:

- the main application entrypoint
- the presentation shell / router
- service orchestration modules
- framework adapter interfaces/registries
- domain models/findings
- persistence layer
- existing tests
- `ARCHITECTURE.md`
- `REPO_MAP.md`
- `CODEBASE_ENTRYPOINTS.md`

---

## Development workflow summary

This repository follows a strict BDD + TDD workflow:

1. define the use case
2. define acceptance criteria
3. write BDD scenarios
4. write unit/integration tests
5. confirm tests fail
6. implement the minimum code
7. refactor after reaching green
8. update docs if architecture or contracts changed

Agents must not skip directly to implementation for non-trivial functionality.

---

## Current frontend baseline

The current Kivy frontend base is organized around:

- `polyglot_site_translator/app.py` as the public GUI factory
- `polyglot_site_translator/bootstrap.py` for shell wiring
- `polyglot_site_translator/presentation/frontend_shell.py` for stateful UI orchestration
- `polyglot_site_translator/presentation/contracts.py` for UI-facing protocols
- `polyglot_site_translator/presentation/view_models.py` for typed screen state
- `polyglot_site_translator/presentation/fakes.py` for deterministic in-memory services
- `polyglot_site_translator/presentation/kivy/` for thin screen rendering
- `polyglot_site_translator/presentation/kivy/widgets/path_picker.py` for Kivy Garden `FileBrowser` path entry (directory listings can be folder-only; still no domain or SQL in that module)

The frontend baseline now also includes:

- an extensible settings screen
- a dedicated settings contract for frontend configuration
- typed App / UI / Kivy settings state
- typed translation defaults inside the settings flow, including the default locale, default `.mo`-compilation preference, and default external-translator preference inherited by new project drafts
- runtime-level exception routing so uncaught thread/callback failures become visible shell state when recovery is possible
- typed wrapping of framework-detection, sync-scope, provider-transport, and persisted-secret decoding failures before they reach Kivy callbacks
- workflow-by-workflow hardening should prefer typed adapter/infrastructure failures over leaked raw transport, decoding, sqlite, or registry exceptions
- the PO workflow persists `.po` changes first and then compiles sibling `.mo` catalogs, collecting file-level compilation failures into typed workflow results instead of aborting the entire run
- TOML-backed frontend settings persistence for runtime configuration
- persisted global sync rules and framework sync rules in general settings
- explicit `.gitignore` integration for filtered sync resolution
- fake in-memory settings persistence for isolated tests and local doubles
- a grouped application menu that separates workspace, operations, and system navigation
- a Kivy runtime theme module for light/dark palette application
- runtime application of saved window size and theme mode after successful settings saves
- startup loading of persisted theme, window size, and safe remembered screens
- responsive settings layout rules so narrow windows switch to a stacked compact layout
- a first real `site_registry` subsystem backed by SQLite
- a real optional `remote_connections` subsystem with a discoverable provider registry
- explicit domain models, contracts, and errors for site registry CRUD
- explicit typed descriptors and structured connection-test results for remote connections
- SQLite repository resolution from persisted `database_directory` and `database_filename`
- persisted `sync_progress_log_limit` for the sync progress popup
- a thin project editor screen for create/edit flows through the presentation shell
- a sectioned project editor workflow so project configuration is grouped like the general settings screen
- the `General` project-editor section now owns only general metadata not covered by the translation, remote, or sync tabs, and switching tabs must preserve the in-progress draft
- a discoverable remote connection combo with a "No Remote Connection" option
- an editor-level "Test Connection" action delegated through presentation/application services
- an explicit SSH host-key trust popup during sync for unknown SFTP/SCP hosts, with strict verification on by default and TOFU auto-add only after user confirmation
- encrypted-at-rest remote passwords through a local key file stored alongside app config
- migration of legacy `ftp_*` columns into a related remote-connection table without decrypting stored ciphertext during migration
- a real bidirectional sync service that reuses the discoverable remote provider registry
- reusable remote provider sessions with explicit state for connect/list/download/upload/close across a full sync run
- remote connection tests and sync failures report operation/project/protocol/host/port/path-specific errors instead of raw generic transport messages
- FTP/FTPS/SFTP/SCP providers should keep operational failures under typed `RemoteConnectionOperationError` subtypes before project sync consumes them
- typed sync direction, remote file descriptors, summaries, results, and controlled sync errors
- typed sync progress events used to drive a background execution popup in the frontend
- local workspace preparation, local file discovery/reads, and file writes isolated in infrastructure for sync workflows
- a dedicated sync progress window opened from Project Detail so download/upload transfers do not block the Kivy UI thread
- a bounded sync command log that keeps only the latest configured operations in memory
- incremental remote sync downloads so large FTP/SFTP trees can begin writing local files before remote discovery fully completes
- incremental local-to-remote uploads with automatic remote directory preparation and one reusable remote session per sync run
- adapter-owned sync include/exclude specs plus an explicit scope-resolution service reused by both sync directions
- current adapters expose framework-specific includes and exclusions for WordPress, Django, and Flask without hardcoding those rules in generic sync services or Kivy widgets
- `FrameworkSyncScopeService` now composes global settings rules, framework settings rules, adapter defaults, project overrides, and optional `.gitignore` exclusions
- the remote project configuration now persists whether sync should use adapter filters or full sync
- the project editor only captures that preference; `ProjectSyncService` and `FrameworkSyncScopeService` resolve the effective behavior outside the Kivy layer
- sync-scope resolution failures are surfaced as structured workflow/editor failures instead of falling through as raw adapter/gitignore/settings exceptions
- framework-detection service entrypoints likewise wrap adapter-registry runtime failures before catalog/detail workflows consume them
- the project editor now also renders the resolved sync-rule catalog and captures project-level include/exclude overrides, but rule composition and persistence still stay in services/infrastructure
- a real adapter registry for framework detection with typed results
- dynamic adapter discovery from the `adapters/` package at runtime
- concrete WordPress, Django, and Flask detection adapters
- project-detail enrichment that shows framework detection evidence or warnings without moving heuristics into Kivy
- a first real shared translation workflow for discovery, locale-family grouping, cross-variant synchronization of missing entries, optional external translation, and optional `.mo` compilation
- the project detail screen exposes that workflow as a generic `Translate` action, and the pre-run popup can override locales, `.mo` compilation, and external-translator usage for the current execution
- typed PO-processing results surfaced through the presentation workflow service
- external PO translation providers should distinguish configuration, transport/protocol, and response-shape failures with typed PO translation errors
- `polib`-backed PO repository wiring in runtime frontend services (instead of fixed preview placeholders)

When extending the frontend, keep new behavior behind those boundaries unless the architecture docs are intentionally updated.
