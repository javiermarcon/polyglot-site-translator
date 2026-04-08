# AI_CONTEXT.md

## Repository summary

This repository contains a Kivy-based application for localization workflows across multiple frameworks and site/application types.

It combines:

- site registration
- SQLite persistence
- FTP download/synchronization
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

The frontend baseline now also includes:

- an extensible settings screen
- a dedicated settings contract for frontend configuration
- typed App / UI / Kivy settings state
- TOML-backed frontend settings persistence for runtime configuration
- fake in-memory settings persistence for isolated tests and local doubles
- a grouped application menu that separates workspace, operations, and system navigation
- a Kivy runtime theme module for light/dark palette application
- runtime application of saved window size and theme mode after successful settings saves
- startup loading of persisted theme, window size, and safe remembered screens
- responsive settings layout rules so narrow windows switch to a stacked compact layout
- a first real `site_registry` subsystem backed by SQLite
- explicit domain models, contracts, and errors for site registry CRUD
- SQLite repository resolution from persisted `database_directory` and `database_filename`
- a thin project editor screen for create/edit flows through the presentation shell
- encrypted-at-rest FTP passwords through a local key file stored alongside app config
- a real adapter registry for framework detection with typed results
- dynamic adapter discovery from the `adapters/` package at runtime
- concrete WordPress, Django, and Flask detection adapters
- project-detail enrichment that shows framework detection evidence or warnings without moving heuristics into Kivy

When extending the frontend, keep new behavior behind those boundaries unless the architecture docs are intentionally updated.
