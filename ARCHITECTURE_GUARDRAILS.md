# ARCHITECTURE_GUARDRAILS.md

## Purpose

These guardrails define architectural limits that should not be crossed casually.
They protect maintainability, testability, future extensibility, and target-framework modularity.

---

## Core guardrails

### 1. Do not mix UI and domain logic

Kivy screens, widgets, and callbacks must not implement:

- FTP logic
- SQLite queries
- PO parsing
- report rendering
- hardcoded string detection
- gettext analysis
- framework-specific extraction logic

### 2. Do not mix shared services and adapter logic

Shared services detect, orchestrate, normalize, and persist common behaviors.
Framework adapters encapsulate target-specific conventions and discovery rules.
Do not blur that boundary.

### 3. Do not mix scanning and reporting

Scanners detect findings.
Reporters render findings.
They must remain separate.

### 4. Do not duplicate heuristics

String detection, classification, path inference, and framework-specific conventions must be centralized.
Locale selection rules, locale normalization, translation-memory reuse, and translation-provider invocation rules must also stay centralized.

### 5. Do not add output formats without tests

Any new export/report format must come with tests.

### 6. Do not add scanners without classification integration

A new scanner must integrate with the finding model and be reflected in docs and tests.

### 7. Do not spread SQL across the codebase

SQLite access must remain centralized.

### 8. Do not spread FTP behavior across the codebase

FTP connection logic, download logic, and path normalization must remain centralized.

### 8b. Do not hardcode remote connection catalogs in the UI

Connection-type selectors must be loaded from the discoverable remote connection registry through services.
Do not duplicate the supported connection list across widgets, screens, or tests that can consume the typed catalog.

### 8c. Do not hardcode UI language catalogs in screens

UI language selectors must be derived from packaged gettext catalogs through
the presentation localization helper. Kivy screens and widgets must not keep
parallel language lists or inline translation dictionaries.

### 9. Do not change entrypoints silently

If CLI, service entrypoints, UI navigation entrypoints, or adapter registration points change:

- update tests
- update docs
- update `CODEBASE_ENTRYPOINTS.md`

### 10. Do not bypass the presentation shell from Kivy screens

Screens and widgets must use the presentation shell or another explicit presentation boundary for:

- navigation
- selected-project context
- controlled error display
- workflow invocation

Do not call repositories, FTP clients, scanners, PO processors, or adapter internals directly from Kivy widgets.

---

## Documentation guardrails

When any of the following change, update docs in the same patch:

### New module or package

Update:

- `REPO_MAP.md`
- `ARCHITECTURE.md`

### New subsystem/domain boundary

Update:

- `DOMAIN_MAP.md`
- `ARCHITECTURE.md`
- `ARCHITECTURE_DECISIONS.md`

### New adapter/plugin or adapter contract change

Update:

- `ARCHITECTURE.md`
- `DOMAIN_MAP.md`
- `REPO_MAP.md`
- `CODEBASE_ENTRYPOINTS.md`
- `ARCHITECTURE_DECISIONS.md` if the extension model changed

### New workflow or entrypoint

Update:

- `CODEBASE_ENTRYPOINTS.md`
- `AI_CONTEXT.md`

### New rules or development constraints

Update:

- `AGENTS.md`
- `STYLE.md`
- `TESTING.md` if validation-related

### User/developer-facing behavior or workflow documentation

Update both:

- `README.md` in English
- `README_es.md` in Spanish

---

## Code-quality guardrails

- No `except Exception`
- No giant multipurpose classes
- No hidden destructive sync behavior
- No silent fallback that masks operational failures
- No Python `assert` statements outside pytest tests
- No instance attributes introduced outside class constructors
- No hardcoded temporary filesystem paths in tests or BDD steps
- No protected-member access across class boundaries
- No mutable global runtime state for presentation or service behavior
- No unguarded `next()` calls without a fallback or explicit failure path
- No untyped public APIs without justification
- No undocumented APIs or behaviorally significant helpers, public or private, without
  justification
- No one-line placeholder docstrings for classes, functions, or methods; structured multi-line
  docstrings are required for public and private symbols when they carry behavior.
- No bypassing repository/service boundaries from UI code
- No hardcoded WordPress-only assumptions in shared modules

---

## Change review checklist

Before concluding a non-trivial change, verify:

- boundaries are still respected
- logic is not duplicated
- docs are updated
- tests exist for the changed behavior
- code remains type-checkable
- code and docs still satisfy PEP8, PEP257, PEP484, Ruff, and mypy expectations explicitly
- the UI layer did not absorb infrastructure concerns
- framework-specific rules remain isolated behind adapters/plugins

---

## Process guardrails

### Do not implement behavior before acceptance and test coverage exist

Non-trivial features must begin with:

- use case definition
- BDD scenarios
- unit/integration tests

### Do not merge framework-specific behavior without acceptance coverage

Any new adapter or adapter change must include:

- feature scenarios
- adapter tests
- failure-path tests

### Do not refactor behaviorally significant code without regression protection

Before refactoring:

- confirm acceptance coverage exists
- confirm unit/integration coverage exists
- keep the suite green throughout

---

### Do not hide expensive IO behind helpers or properties

Forbidden:

- filesystem traversal inside simple property accessors
- implicit SQLite access during rendering
- remote provider access during UI rendering
- implicit PO parsing inside view-model getters
- hidden network calls during widget refresh
- logging calls that trigger expensive IO, traversal, or serialization

Rules:

- expensive operations must remain explicit
- orchestration layers own expensive workflows
- UI rendering must consume prepared state
- view models should carry prepared values, not trigger workflow execution

---

### Do not introduce hidden runtime state

Forbidden:

- dynamic runtime attribute injection
- mutable hidden singleton state
- module-level mutable orchestration state
- hidden cross-screen state mutation
- import-time operational side effects

Rules:

- runtime state must remain explicit and typed
- state transitions should be observable and testable
- initialization behavior must be predictable

---

### Do not introduce speculative abstractions

Forbidden:

- abstraction layers without active reuse pressure
- plugin systems without multiple concrete use cases
- service indirection that only forwards calls
- adapters that duplicate shared service behavior

Rules:

- prefer small composable helpers
- extend existing contracts before introducing new layers
- optimize for maintainability, not theoretical purity

---

### Static and security safety guardrails

Forbidden:

- unsafe deserialization of untrusted input
- `eval` or `exec`
- `subprocess` command strings built from untrusted input
- broad analyzer suppressions without narrow justification
- hardcoded secrets, credentials, tokens, or test-looking secrets
- mutable defaults in functions or dataclasses

Rules:

- use `default_factory` for mutable dataclass fields
- use safe loaders for structured input
- use `secrets` for security-sensitive token generation
- preserve exception context with `raise ... from exc` when wrapping failures
