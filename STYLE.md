# STYLE.md

## Coding standards

This project must follow:
- PEP8
- PEP257
- PEP484

The repository should also remain compatible with:
- Ruff for linting and formatting
- mypy for static type checking
- pytest for tests

---

## Core design principles

All code must follow these principles:
- DRY
- SOLID
- SRP
- OCP

Interpretation for this repository:
- **DRY**: scanning rules, classification rules, persistence helpers, locale-validation rules, translation-memory logic, adapter registration, and reporting logic must not be duplicated.
- **SRP**: each module should have one reason to change.
- **OCP**: new scanners, reports, or framework adapters should be added through extension, not through widespread rewrites.
- **SOLID** should guide service boundaries and abstractions, especially between UI, services, adapters, storage, and infrastructure.

---

## Typing

- Use explicit type hints in public functions, methods, and module-level helpers.
- Prefer typed dataclasses or explicit structured models for:
  - site/project records
  - scan findings
  - configuration
  - FTP connection info
  - adapter contracts
  - report summaries
- Avoid untyped dictionaries when a stable structure exists.
- Avoid `Any` unless there is a clear and justified boundary.

---

## Docstrings

- Public modules, classes, and non-trivial functions should have meaningful docstrings.
- Docstrings must explain intent and important behavior, not restate the name.
- Avoid filler text.
- Keep docstrings aligned with actual behavior.

---

## Error handling

- Never use `except Exception`.
- Catch concrete exceptions only.
- Do not ignore failures silently.
- Error messages must be actionable.
- Prefer explicit validation over late failure.
- If logging an unexpected failure, prefer `logger.exception(...)`.
- Avoid broad fallback logic that masks the real error.

---

## Logging

- Use logging for operationally relevant events.
- Do not use random `print()` calls inside domain or infrastructure code.
- CLI or explicit debug tooling may print user-facing information where appropriate.
- GUI notifications should not replace logging for meaningful failures.

---

## Function and class design

- Keep functions small and cohesive.
- Avoid deeply nested conditionals where refactoring improves clarity.
- Avoid giant service classes with unrelated responsibilities.
- Prefer composable helpers/services instead of monoliths.
- Keep Kivy screens/widgets focused on presentation and orchestration.

---

## Shared services vs adapters

- Shared services must remain framework-agnostic where feasible.
- Framework-specific logic belongs in adapters/plugins.
- Do not parse `wp-config.php`, `settings.py`, or framework-specific conventions from generic modules unless that generic module is explicitly an adapter boundary.

---

## UI rules

Kivy views must not absorb domain responsibilities.

Avoid placing these directly inside widget/screen classes:
- FTP session logic
- SQLite queries
- PO parsing
- source scanning heuristics
- report generation
- translation memory logic
- framework-specific extraction rules

Views may:
- receive input
- trigger services
- display results
- render progress and errors

---

## Persistence rules

- SQLite access must be centralized.
- Schema assumptions must be explicit.
- Do not spread SQL strings across unrelated modules.
- Prefer repositories or dedicated persistence services.

---

## FTP rules

- Centralize FTP operations.
- Validate credentials, remote roots, and sync targets.
- Avoid implicit overwrite behavior.
- Make destructive behavior explicit and testable.

---

## Reporting rules

- Markdown, JSON, CSV, and future report formats must be implemented in separate modules or clearly separated strategies.
- Formatting must not be mixed with scanning logic.
- Findings must be normalized before rendering/export.

---

## Naming

- Use descriptive names.
- Prefer domain terminology consistently:
  - site
  - project
  - scan
  - finding
  - report
  - sync
  - locale
  - family
  - adapter
  - plugin
  - framework
- Avoid vague names like:
  - `data`
  - `manager`
  - `helper`
  - `misc`
  - `stuff`

unless the role is genuinely generic and justified.

---

## Imports

- Keep imports clean and minimal.
- Remove unused imports.
- Avoid circular dependencies.
- Prefer explicit imports over wildcard imports.

---

## Configuration

- Centralize configuration.
- Avoid scattering path constants, environment assumptions, or default values without clear ownership.
- Platform-specific behavior must be isolated and documented.

---

## Forbidden shortcuts

The following are forbidden unless explicitly justified and documented:
- `except Exception`
- giant god classes
- hidden mutation through shared global state
- duplicating SQL logic
- duplicating scanner heuristics
- duplicating framework-specific rules across adapters
- embedding business logic directly in Kivy callbacks
- architecture changes without doc updates
