# ARCHITECTURE_DECISIONS.md

## Purpose

This document records important architectural decisions and their rationale.
Update it when significant design decisions are added, reversed, or refined.

---

## AD-001: Kivy as the primary UI technology

**Decision**
Use Kivy as the graphical UI framework.

**Why**
The project targets a cross-platform graphical workflow and may evolve toward Linux, Windows, macOS, and Android-adjacent packaging paths.

**Implications**

- UI concerns must remain isolated from domain/infrastructure concerns.
- Packaging constraints may influence dependency choices.
- Some tooling must remain platform-aware.

---

## AD-002: Virtualenv-first development workflow

**Decision**
Use `venv` as the primary local development strategy instead of Docker-first development.

**Why**
Kivy, native dependencies, graphical toolchains, and packaging-oriented workflows are easier to manage directly on the host system during development.

**Implications**

- Docker is optional, not the primary development path.
- CI remains important for linting, typing, and testing consistency.
- Host setup documentation matters.

---

## AD-003: SQLite for local site registry

**Decision**
Store site/project metadata locally in SQLite.

**Why**
The application needs a lightweight embedded database for site definitions, paths, FTP settings, framework type, and related metadata without external services.

**Implications**

- Persistence logic must be centralized.
- Schema changes must remain explicit and testable.
- UI must not talk to SQLite directly.

---

## AD-004: FTP support as infrastructure, not UI logic

**Decision**
FTP download/synchronization is treated as infrastructure accessed through services.

**Why**
FTP behavior is operational and testable, but should not be embedded into screens/widgets.

**Implications**

- FTP client behavior should be mockable.
- Services orchestrate FTP workflows.
- UI receives structured results.

---

## AD-005: Preserve PO processing as a shared domain capability

**Decision**
`.po` synchronization/translation capabilities remain a first-class shared subsystem.

**Why**
PO handling is useful across multiple frameworks and should not be tied to a single target type.

**Implications**

- PO logic should be preserved and modularized.
- UI should invoke it through services, not inline code.
- Tests must protect previous useful behavior.
- Framework adapters may guide discovery, but should not reimplement shared PO logic.
- External translators must stay behind provider contracts so the shared workflow does not depend directly on a concrete API client.

---

## AD-006: Use pluggable framework adapters

**Decision**
Framework-specific behavior is implemented through adapters, plugins, or subclasses rather than embedded into shared services.

**Why**
The project is no longer WordPress-only. WordPress, Django, Flask, and future targets have different configuration, source layout, and data-discovery rules.

**Implications**

- Shared services must remain target-agnostic where possible.
- A stable contract is needed between adapters and services.
- Tests must cover both shared behavior and adapter-specific behavior.
- Adapter selection should be centralized in a registry/resolver instead of spread through `if/elif` chains.
- Ambiguous multi-match detection should fail explicitly instead of silently picking an arbitrary framework.
- New adapters should be discoverable by convention from the adapters package instead of requiring manual runtime registration lists.

---

## AD-007: Source auditing expands beyond `.po`

**Decision**
The project must support broader source auditing beyond gettext files.

**Why**
Real-world localization issues also exist in PHP, Python, JS, JSON, templates, framework configuration, builder-managed content, and misused gettext patterns.

**Implications**

- Findings must have typed representations.
- Scanners must be composable and extensible.
- Reporting must work over normalized findings.

---

## AD-008: Reporting is a separate subsystem

**Decision**
Report generation is implemented separately from scanning and persistence.

**Why**
Markdown, CSV, JSON, and future outputs have different concerns and should not leak into scanner code.

**Implications**

- Findings must be normalized before rendering.
- New formats require dedicated tests.
- UI should consume summaries, not formatting internals.

---

## AD-009: Documentation is part of the architecture

**Decision**
Repository governance documents are mandatory and must evolve with the code.

**Why**
This project is intended to be extended iteratively, including by coding agents. Without active architectural documentation, drift becomes likely.

**Implications**

- Structural changes require doc updates in the same patch.
- New modules/services/adapters need repository map updates.
- Agent behavior is constrained by repo docs.

---

## AD-010: Frontend shell depends on contracts and typed presentation models

**Decision**
Introduce a presentation shell between Kivy widgets and application services, using typed view models and explicit UI-facing service protocols.

**Why**
The repository needs a usable Kivy base and must support incremental replacement of fake services with real infrastructure. A presentation shell allows the UI to evolve without coupling widgets to SQLite, TOML persistence, FTP, or future adapter implementations.

**Implications**

- Screens stay thin and render precomputed state.
- Navigation and selected-project context live outside widgets.
- Fake in-memory services can drive BDD and unit tests.
- Future real services can replace fakes through dependency injection without rewriting the frontend structure.

---

## AD-011: Frontend settings use an extensible section-based contract

**Decision**
Model frontend configuration through a dedicated settings contract, typed settings view models, and a section-based settings screen.

**Why**
The current task only needs App / UI / Kivy settings, but the repository will later need settings for translation, adapters, FTP, reporting, and broader system behavior. A section-based contract avoids hardcoding the screen around a single future-incompatible form.

**Implications**

- Settings persistence remains behind a dedicated service contract.
- The Kivy screen edits a typed draft and delegates saving/resetting to the presentation shell.
- Future settings sections can extend the same structure without rewriting navigation or mixing persistence into widgets.

---

## AD-012: SQLite location is configured through general settings and resolved in infrastructure

**Decision**
Store `database_directory` and `database_filename` in the general frontend settings, then resolve the final SQLite path in infrastructure.

**Why**
The application needs a user-configurable SQLite location without teaching widgets how to build paths or where the database lives on disk.

**Implications**

- Kivy screens edit only typed settings fields.
- `TomlSettingsService` persists the configured directory and filename.
- `resolve_sqlite_database_location()` owns normalization and final path composition.
- Runtime site registry wiring can change storage location without rewriting screens or the presentation shell.

---

## AD-013: Remote connections are optional, typed, and discoverable

**Decision**
Store remote connection settings separately from the core site/project record, and resolve concrete connection types through a discoverable provider registry.

**Why**
Not every project needs remote access, and future targets must not assume FTP-only transport or require manual registration when a new provider is added.

**Implications**

- `SiteProject` identity and `RemoteConnectionConfig` persistence remain separate.
- UI selectors must be populated from the discoverable catalog instead of hardcoded lists.
- A "No Remote Connection" option is first-class and valid.
- Connection testing must return structured results and stay behind services/infrastructure boundaries.
- Legacy `ftp_*` persistence needs controlled migration without decrypting stored ciphertext during the move.

---

## AD-014: Sync reuses the existing remote provider registry

**Decision**
Implement real sync as a dedicated service that reuses the existing discoverable remote connection providers instead of creating a second registry or parallel provider system.

**Why**
The repository already has typed optional remote connections and a discoverable provider model. Reusing that base keeps transport resolution centralized, avoids duplicate extension points, and prepares the system for later bidirectional sync without pushing network or filesystem behavior into Kivy.

**Implications**

- Sync direction, summaries, results, remote file descriptors, and errors need explicit typed models.
- Presentation triggers sync through services and renders structured results; widgets do not open sockets or touch the filesystem directly.
- Remote providers now own connection testing plus transport-specific listing/download/upload behavior.
- Multi-file sync must use a reusable remote session opened from the provider instead of reconnecting for each file.
- Local workspace preparation and file writes stay in infrastructure, separate from presentation and domain logic.
- Later stages can add new sync directions and richer controls without replacing the provider registry.

---

## AD-017: Local-to-remote upload extends the existing sync service and session contracts

**Decision**
Implement `local -> remote` as an extension of the existing `ProjectSyncService`, `LocalSyncWorkspace`, and reusable remote-session contracts instead of creating a second upload-only workflow stack.

**Why**
The repository already has typed sync models, reusable provider sessions, bounded progress logs, and presentation wiring for background sync execution. Extending that base keeps both sync directions symmetrical, preserves OCP for transport providers, and avoids duplicating retry, connection lifecycle, or popup orchestration logic.

**Implications**

- `domain/sync` now models both remote and local file descriptors plus bidirectional counters.
- `LocalSyncWorkspace` owns local file discovery and reads for upload workflows.
- Remote sessions must expose explicit directory-creation and upload operations in addition to listing/download.
- The project-detail screen reuses the same popup and shell orchestration for both sync directions.
- Selective/full sync controls in the UI remain future work.

---

## AD-018: Framework adapters own reusable sync include/exclude rules

**Decision**
Define sync include/exclude rules on framework adapters and resolve them through a dedicated service instead of hardcoding framework paths inside `ProjectSyncService` or Kivy screens.

**Why**
WordPress, Django, and Flask care about different localization-relevant paths and different framework-specific artifacts that should be excluded from sync. Keeping those rules in adapter-owned contracts preserves OCP, lets future adapters add includes/excludes without modifying shared sync orchestration, and makes the same resolved scope reusable for both `remote -> local` and `local -> remote`.

**Implications**

- `BaseFrameworkAdapter` and the framework-adapter contract now expose a scope with include and exclude rules.
- `FrameworkSyncScopeService` returns an explicit `ResolvedSyncScope` with statuses such as `filtered`, `no_filters`, `framework_unresolved`, and `adapter_unavailable`.
- `ProjectSyncService` can resolve the effective scope from the persisted remote-config preference and applies it symmetrically to download and upload workflows.
- The project editor persists a per-project `Use Adapter Sync Filters` choice, while scope resolution itself still stays outside the Kivy layer.

---

## AD-019: Project-specific sync rule overrides are persisted and edited through presentation state

**Decision**
Persist project-specific sync rule overrides separately from adapter defaults, and expose them to the UI through typed editor state instead of letting Kivy compute or store scope logic on its own.

**Why**
Adapters need framework-level defaults, but real projects also need local overrides such as custom localization folders or disabled exclusions. Those overrides must survive SQLite round-trips and must not move business logic into widgets.

**Implications**

- `RemoteConnectionFlags` now persists project-level sync rule overrides alongside the filtered-vs-full preference.
- SQLite stores those overrides in a dedicated related table instead of flattening them into widget state or generic settings.
- `FrameworkSyncScopeService` composes adapter rules with persisted project overrides and returns a visible catalog of resolved rules.
- The project editor shows that catalog, toggles rule enablement, and adds/removes project rules by rebuilding typed drafts through presentation services.
- `ProjectSyncService` keeps consuming only the resolved scope; it does not know about Kivy widgets or how the editor is rendered.

---

## AD-020: Compose filtered sync scope from global, framework, project, and optional `.gitignore` layers

**Decision**
Persist shared sync rules in SQLite at two levels, `global` and `framework`, and let `FrameworkSyncScopeService` compose them with adapter defaults, project overrides, and optional `.gitignore`-derived exclusions.

**Why**
Project-local overrides are necessary but insufficient. Real operators also need repository-wide exclusions such as `.git`, reusable framework presets beyond adapter code defaults, and optional alignment with `.gitignore` without pushing parser logic into Kivy or `ProjectSyncService`.

**Implications**

- SQLite now persists global sync rules, framework sync rules, and `use_gitignore_rules` for the sync runtime.
- `settings.toml` continues to persist general app state and the SQLite location, while shared sync scope data is loaded from the configured database.
- the settings screen exposes ABM for those rules, but Kivy still only edits typed drafts.
- `.gitignore` support is explicit and opt-in instead of a silent implicit behavior.

---

## AD-021: Reimplement legacy PO synchronization as a modular shared service

**Decision**
Implement the first real PO-processing slice as typed domain + service + infrastructure modules, and wire it through `ProjectWorkflowService.start_po_processing`.

**Why**
Legacy `traducir.py` mixed discovery, synchronization, translation-provider calls, cache, CLI, and output concerns in one script. The current architecture needs reusable PO behavior without coupling presentation to parsing or file IO.

**Implications**

- PO discovery and persistence are isolated in `infrastructure/po_files.py`.
- Shared synchronization rules live in `services/po_processing.py` and are framework-agnostic.
- The first slice focuses on discovery, family grouping, and synchronization of missing entries (including plurals) between locale variants.
- External translation API calls, persistent cache, and `.mo` compilation remain future stages.

---

## AD-015: Long-running sync runs in background and reports typed progress events

**Decision**
Run project sync from the frontend through a background thread and drive the UI from typed progress events plus a dedicated sync-progress popup.

**Why**
Remote sync can block on FTP/SFTP/SSH I/O. Running that workflow directly in a Kivy callback freezes the UI, which is not acceptable for an operator-facing desktop app.

**Implications**

- Kivy widgets remain presentation-only and do not execute remote I/O directly.
- The presentation shell owns background orchestration state for sync execution.
- Application and infrastructure layers emit typed progress events and command-log entries that the popup can render.
- The Project Detail action opens a progress window instead of blocking the current screen while the workflow runs.

---

## AD-016: Remote sync uses reusable provider sessions

**Decision**
Remote providers expose `open_session()` for sync workflows. A session owns connect, list, download, close, connection state, and controlled retry behavior for connection establishment.

**Why**
Listing once and reconnecting for every downloaded file is fragile, slow, and hard to reason about when FTP/SFTP/SCP transports fail mid-run. A single session-level abstraction makes lifecycle, state, close behavior, progress commands, and retry policy explicit while keeping transport details outside services and widgets.

**Implications**

- `ProjectSyncService` opens one session for a remote-to-local sync run and reuses it for listing and every file download.
- FTP, FTPS, SFTP, and SCP providers implement the same session contract.
- Provider convenience methods remain available for bounded materialization or one-off operations, but they must delegate through sessions.
- Transport errors are normalized into structured remote-operation errors where possible; widgets only render typed progress and final sync results.

---

## AD-017: Kivy Garden FileBrowser for local path picking

**Decision**
Use the `kivy-garden.filebrowser` `FileBrowser` widget (declared in `requirements/base.txt`) for filesystem pickers in the Kivy UI instead of embedding only the stock `FileChooserListView`.

**Why**
The garden widget provides a clearer layout (shortcuts, list/icon tabs, integrated actions) while still delegating to the same `FileChooserController` semantics (`dirselect`, `filters`, `filter_dirs`).

**Implications**

- Directory-only workflows (for example project `local_path` and SQLite directory) combine `dirselect=True`, `filter_dirs=True`, and a callable filter that keeps directory entries in the listing so regular files are not offered as first-class picks.
- File picking for SQLite filename continues to use the same widget in file-selection mode without that listing restriction.
- The dependency must remain explicit under `requirements/` and mypy may ignore missing stubs for `kivy_garden.filebrowser` via `pyproject.toml` overrides.
