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
