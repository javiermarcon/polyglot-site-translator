# AGENTS.md

## Purpose

This repository contains a cross-platform graphical application built with Kivy for auditing, translating, and managing localization workflows across multiple kinds of websites and applications.

The project is framework-agnostic at the core. Shared translation and audit logic lives in reusable services, while framework-specific behavior is implemented through adapters, plugins, or subclasses for systems such as WordPress, Django, Flask, and future targets.

The application is intended to run on Linux, Windows, macOS, and Android-compatible workflows where feasible, with future packaging support through tools such as Buildozer for supported targets.

Agents working on this repository must preserve architecture, typing, maintainability, platform-awareness, and pluggable framework support.

---

## Mandatory response structure

When proposing or applying changes, always structure the response in this order:

1. `PLAN`
2. `PATCH`
3. `TESTS`
4. `VERIFY`
5. `DOCS`
6. `PENDING / RISKS`

Do not skip sections.
If a section does not apply, explicitly say so.

---

## Hard rules

- Do not use `except Exception`.
- Do not swallow errors silently.
- Do not introduce hidden side effects.
- Do not mix UI logic with domain logic.
- Do not mix persistence, networking, parsing, reporting, and presentation in the same module.
- Do not create large, unstructured files.
- Do not duplicate heuristics, scanning logic, or validation rules.
- Do not hardcode framework-specific rules into shared services when they belong in an adapter or plugin.
- Do not break CLI or service entrypoints if they already exist.
- Do not introduce a new module or subsystem without updating repository documentation.
- Do not change architecture without updating:
  - `ARCHITECTURE.md`
  - `REPO_MAP.md`
  - `ARCHITECTURE_DECISIONS.md`
  - `ARCHITECTURE_GUARDRAILS.md`
  - `AI_CONTEXT.md`
  - `CODEBASE_ENTRYPOINTS.md`
  - `DOMAIN_MAP.md` if domain boundaries changed

---

## Definition of done

A task is not done unless all of the following are true:

- The code is aligned with:
  - PEP8
  - PEP257
  - PEP484
  - Ruff
  - mypy
- The change includes tests for the main behavior introduced or modified.
- The implementation respects DRY, SOLID, SRP, and OCP.
- Shared services remain framework-agnostic where intended.
- Framework-specific extraction or discovery rules are isolated behind dedicated modules.
- New domain logic is not embedded directly in Kivy views/widgets.
- Error handling is explicit and concrete.
- Documentation affected by the change is updated in the same patch.
- The repository remains coherent for future Codex/agent iterations.

---

## Required validation before finishing

Before finishing any non-trivial change, verify explicitly:

- Ruff passes.
- mypy passes.
- pytest passes for the affected scope.
- Documentation is aligned with the final code.
- No `except Exception` was introduced.
- No domain logic was pushed into presentation-only modules.
- No persistence logic was duplicated across UI and services.
- Shared services still support multiple framework adapters cleanly.

---

## Preferred implementation style

- Small, cohesive modules.
- Typed dataclasses or explicit models for structured data.
- Clear separation between:
  - Kivy UI
  - application services
  - domain logic
  - infrastructure
  - persistence
  - reporting
  - framework adapters/plugins
- Dependency injection or clear constructor-based wiring where useful.
- Testable services independent of the GUI runtime.

---

## Special rules for Kivy/UI work

- Keep widgets/screens thin.
- Avoid embedding parsing, FTP, SQLite, or translation logic directly in UI classes.
- UI should orchestrate services, not implement them.
- Long-running operations must be designed so they can later be moved to background execution safely.
- Cross-platform assumptions must be documented.

---

## Special rules for framework support

- Shared logic for `.po`, reports, scanning orchestration, and persistence contracts belongs in common services/modules.
- Framework-specific discovery, configuration parsing, database extraction, and path conventions must live in adapters/plugins.
- Example: a WordPress adapter may parse `wp-config.php`, while a Django adapter may parse settings modules or environment-backed settings.
- Do not leak WordPress assumptions into Django/Flask adapters, and do not leak Django assumptions into shared services.

---

## Special rules for SQLite/FTP work

- Centralize persistence access.
- Centralize FTP client behavior.
- Validate paths, credentials, and remote/local sync assumptions explicitly.
- Avoid implicit destructive operations.
- Dry-run or preview capability is preferred before destructive synchronization.

---

## What to update when adding features

### If adding a new domain service

Update:

- `ARCHITECTURE.md`
- `REPO_MAP.md`
- `DOMAIN_MAP.md`
- `CODEBASE_ENTRYPOINTS.md`

### If adding or changing a framework adapter/plugin

Update:

- `ARCHITECTURE.md`
- `DOMAIN_MAP.md`
- `REPO_MAP.md`
- `ARCHITECTURE_DECISIONS.md` if the extension model changed
- tests for adapter-specific behavior

### If adding a new command, workflow, or screen

Update:

- `ARCHITECTURE.md`
- `REPO_MAP.md`
- `CODEBASE_ENTRYPOINTS.md`
- `AI_CONTEXT.md`

### If adding a new architectural rule

Update:

- `ARCHITECTURE_GUARDRAILS.md`
- `STYLE.md` if coding-related
- `TESTING.md` if validation-related

---

## Verification commands

Agents should prefer project-standard commands.
Adjust only if the repository evolves and update docs accordingly.

Examples:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest
```

If additional commands become canonical, document them in:

- `TESTING.md`
- `CODEBASE_ENTRYPOINTS.md`
- `REPO_MAP.md`

---

## Mandatory development workflow: BDD + TDD

All non-trivial functionality must be developed using this sequence:

1. Define the use case.
2. Identify acceptance criteria.
3. Add or update BDD scenarios covering:
   - happy path
   - edge cases
   - expected failures and exceptions
4. Add or update unit and integration tests for the same behavior.
5. Run the tests and confirm they fail before implementation.
6. Implement the minimum code required to satisfy the tests and scenarios.
7. Refactor only after the full relevant test suite is green.
8. Update architecture and repository docs if the change affects structure, contracts, or workflows.

Do not implement a feature first and add tests later.

For every meaningful feature:

- acceptance behavior must be specified first
- test coverage must precede implementation
- regression tests must be added for bug fixes

When reporting work, explicitly state:

- which use cases were identified
- which BDD scenarios were added or updated
- which unit/integration tests were added first
- which failures were observed before implementation
- what refactors were done after reaching green
