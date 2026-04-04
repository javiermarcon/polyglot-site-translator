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

### 5. Do not add output formats without tests

Any new export/report format must come with tests.

### 6. Do not add scanners without classification integration

A new scanner must integrate with the finding model and be reflected in docs and tests.

### 7. Do not spread SQL across the codebase

SQLite access must remain centralized.

### 8. Do not spread FTP behavior across the codebase

FTP connection logic, download logic, and path normalization must remain centralized.

### 9. Do not change entrypoints silently

If CLI, service entrypoints, UI navigation entrypoints, or adapter registration points change:

- update tests
- update docs
- update `CODEBASE_ENTRYPOINTS.md`

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

---

## Code-quality guardrails

- No `except Exception`
- No giant multipurpose classes
- No hidden destructive sync behavior
- No silent fallback that masks operational failures
- No untyped public APIs without justification
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
