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

---

## Persistence entrypoints

SQLite access should be centralized behind repositories or persistence services.

Possible examples:
- site repository
- settings repository
- scan history repository if added later

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

---

## CLI entrypoints

If the repository includes a CLI alongside the GUI, document commands and their owning modules here.
If no CLI exists yet, update this document when one is introduced.

---

## Maintenance rule

If a new screen, service, adapter, command, or major subsystem is introduced, update this file in the same patch.
