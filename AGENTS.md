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
- Do not introduce a new external dependency without declaring it in the `requirements/` directory using the repository split defined below.
- Do not leave `README.md` or `README_es.md` outdated when a task changes behavior, installation, usage, testing commands, architecture visible to contributors, or user/developer-facing capabilities.
- Keep `README.md` in English and `README_es.md` in Spanish; update both files in the same patch whenever either one applies.
- Do not keep production fake bundles for workflows that already have a real implementation.
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
- Python source lines must stay within 88 characters unless a narrower, tool-supported exception is
  explicitly justified.
- All modules, classes, functions, and methods introduced or modified by the change, public or
  private, have clear, multi-line docstrings that explain intent, important behavior, inputs,
  outputs, and relevant side effects or failure conditions.
- One-line docstrings are not acceptable for behavioral symbols. Docstrings must be structured and
  must include sections such as `Args:`, `Returns:`, `Raises:`, and `Attributes:` whenever those
  sections are relevant to the symbol being documented.
- The change includes tests for the main behavior introduced or modified.
- Implemented workflows are wired to real services in production entrypoints; test doubles for those workflows live in test support, not in runtime bundles under `src/`.
- The implementation respects DRY, SOLID, SRP, and OCP.
- Shared services remain framework-agnostic where intended.
- Framework-specific extraction or discovery rules are isolated behind dedicated modules.
- New domain logic is not embedded directly in Kivy views/widgets.
- Error handling is explicit and concrete.
- Documentation affected by the change is updated in the same patch.
- Any new external dependency is declared in the correct file under `requirements/`, or explicitly avoided because it belongs to the Python standard library.
- `README.md` and `README_es.md` reflect the real current behavior whenever the task changed installation, setup, commands, workflows, visible features, or other user/developer-facing behavior.
- The repository remains coherent for future Codex/agent iterations.

---

## Required validation before finishing

Before finishing any non-trivial change, verify explicitly:

- Ruff passes.
- mypy passes.
- The changed code still satisfies PEP8, PEP257, and PEP484 explicitly, not only “whatever the
  current tool defaults happen to enforce”.
- The repository docstring audit passes, including private symbols and structured multi-line
  docstring requirements.
- pytest passes for the affected scope.
- Documentation is aligned with the final code.
- New dependencies, if any, are declared in the correct `requirements/` file and nowhere inconsistent.
- `README.md` and `README_es.md` are aligned with the final installation, usage, testing, configuration, and feature set affected by the task.
- No `except Exception` was introduced.
- No domain logic was pushed into presentation-only modules.
- No persistence logic was duplicated across UI and services.
- Shared services still support multiple framework adapters cleanly.
- No runtime fake bundle remains in use for functionality that is already implemented for production use.

---

## Preferred implementation style

- Small, cohesive modules.
- Typed dataclasses or explicit models for structured data.
- Clear docstrings for all modules, classes, functions, and methods, public or private; do not
  leave new or modified behavior undocumented.
- Use structured multi-line docstrings, not one-line placeholders. Include `Args:`, `Returns:`,
  `Raises:`, and `Attributes:` sections whenever they apply to the documented symbol.
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

## Policy for fakes, stubs, and mocks

Production code may contain placeholders only for workflows that are explicitly not implemented yet.

If a workflow already has a real implementation:

- the default runtime entrypoints must use the real implementation
- do not keep or introduce a production fake bundle for that workflow under `src/`
- tests must validate the implemented behavior using mocks, stubs, fixtures, or temporary files
- those mocks/stubs must live in test support code (`tests/`, `features/steps/`, or equivalent test-only locations), not in production runtime wiring
- tests must not depend on external public services such as remote FTP/SFTP servers

If a fake remains temporarily because a workflow is not implemented yet:

- scope it narrowly to the unfinished workflow
- document that limitation in the relevant architecture/runtime docs
- remove it once the real workflow exists

---

## Special rules for Kivy/UI work

- Keep widgets/screens thin.
- Avoid embedding parsing, FTP, SQLite, or translation logic directly in UI classes.
- UI should orchestrate services, not implement them.
- Long-running operations must be designed so they can later be moved to background execution safely.
- Cross-platform assumptions must be documented.
- UI work must improve or preserve the visual design system, not only functional behavior.
- Before editing a Kivy screen, inspect existing theme, reusable widgets, layout helpers, and screen patterns.
- Do not create one-off styling when a reusable themed widget or token should exist.
- Prefer extracting repeated visual patterns into small reusable widgets under
  `presentation/kivy/widgets/`.
- Every new or modified screen must define clear hierarchy, spacing, action placement,
  empty/loading/error states, and responsive behavior.

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

### Dependency declaration policy

External dependencies are mandatory, explicit repository data.
They must never be introduced implicitly.

If a task requires a new third-party library:

- runtime dependencies must be added to `requirements/base.txt`
- development-only or test-only dependencies must be added to `requirements/dev.txt`
- dependencies must not be declared in ad hoc files or inconsistent locations when the existing `requirements/` strategy already covers the use case
- a dependency must not be used in code, tests, scripts, or tooling setup unless it is declared in the appropriate `requirements/` file
- Python standard-library modules such as `ftplib`, `sqlite3`, `pathlib`, `json`, and similar modules must not be added to `requirements/`
- if a new dependency affects CI, automation, or workflows, the relevant CI/workflow files must be updated in the same change
- if a new dependency affects installation, setup, commands, or user/developer expectations, `README.md` and `README_es.md` must be updated in the same change

Do not rely on “it is probably installed already”.
Do not leave undeclared dependencies for future cleanup.

### README alignment policy

`README.md` and `README_es.md` are required operational documents, not optional
project marketing text. `README.md` must be written in English and
`README_es.md` must be written in Spanish. Both must describe the real current
state of the repository.

Update both `README.md` and `README_es.md` in the same patch whenever a task:

- changes observable system behavior
- adds, removes, or materially changes a feature
- changes architecture in a way that affects contributors or the visible system shape
- changes installation, setup, configuration, or environment expectations
- changes testing commands, validation workflow, or canonical development commands
- changes primary usage flows, operator workflows, or visible project capabilities
- adds a dependency or capability whose impact should be visible to users or contributors

Neither README file may remain desynchronized from the codebase or from each
other. If the way to run, test, configure, install, or use the system changed,
both files must reflect it before the task is considered done.

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

### If changing dependencies or developer-visible workflows

Update:

- the correct file under `requirements/`
- `README.md` and `README_es.md` if installation, setup, commands, capabilities, or expectations changed
- CI/workflow files if automation or environment setup changed

---

## Verification commands

Agents should prefer project-standard commands.
Adjust only if the repository evolves and update docs accordingly.

Examples:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python tests/run_docstring_audit.py
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
   - end-to-end behavior for every touched user-visible workflow
4. Add or update unit and integration tests for the same behavior.
5. Run the tests and confirm they fail before implementation.
6. Implement the minimum code required to satisfy the tests and scenarios.
7. Refactor only after the full relevant test suite is green.
8. Update architecture and repository docs if the change affects structure, contracts, or workflows.

Do not implement a feature first and add tests later.

For every meaningful feature:

- acceptance behavior must be specified first
- `.feature` coverage must exist for the externally visible workflow from end to end
- touched user-visible workflows must not rely only on unit or integration tests
- test coverage must precede implementation
- regression tests must be added for bug fixes

When reporting work, explicitly state:

- which use cases were identified
- which BDD scenarios were added or updated
- which unit/integration tests were added first
- which failures were observed before implementation
- what refactors were done after reaching green

---

## Coverage and test completeness rule

For any non-trivial new or modified logic, unit tests must:

- cover happy path behavior
- cover important edge cases
- cover expected errors and exceptions
- include regression tests for bug fixes
- reach at least 99% coverage for the relevant unit-tested logic unless a narrow, explicit exception is justified

For touched production modules, tests are also expected to cover all relevant:

- functions
- methods
- classes with behavior
- meaningful branches

Coverage work must be intentional, not incidental. Tests must explicitly exercise:

- the normal success path
- edge and boundary cases
- invalid or malformed input
- operational failures
- explicit exceptions and typed error paths

The repository target is to keep coverage as close as possible to 99% for touched logic and to avoid leaving meaningful branches, methods, or helper behaviors untested. If any relevant branch, function, method, class behavior, or error path remains uncovered, that gap must be called out explicitly in the final report with a concrete reason.

Do not treat “some tests exist” as sufficient completion.
A task is not done if meaningful branches and failure modes remain untested.

For any non-trivial new or modified user-visible workflow, `.feature` scenarios must also cover all relevant end-to-end:

- happy paths
- important edge cases
- invalid input and validation outcomes visible to the operator
- controlled operational failures
- expected exceptions or surfaced error states

A task is not done if a touched workflow is only covered at unit level but not through the relevant end-to-end feature scenarios.

---

## Explicit style and typing compliance

Every change must explicitly respect:

- PEP8
- PEP257
- PEP484
- Ruff
- mypy

Do not assume those standards are optional just because a specific file already existed in a
weaker state. New and modified code must move the repository toward explicit compliance, not away
from it.
