# TESTING.md

## Testing goals

This project combines:

- Kivy presentation
- shared translation/localization services
- framework-specific adapters
- source scanning
- SQLite persistence
- FTP integration
- reporting/export

Testing must reflect those responsibilities without making the suite fragile.

---

## Test stack

Use:

- `pytest`
- `pytest` fixtures
- parametrization where it improves coverage and clarity
- mocks/stubs for external services
- temporary directories/files for filesystem-heavy behavior

Avoid tests that depend on:

- public internet
- real FTP servers
- real user-specific environments
- real Android packaging
- GUI timing hacks unless absolutely necessary

---

## Testing layers

### 1. Unit tests

Must cover isolated logic such as:

- PO discovery
- locale/family grouping
- translation synchronization
- plural handling
- cache behavior
- source classification
- gettext detection
- hardcoded string detection
- adapter-specific extraction
- report rendering
- path and configuration normalization
- repository/persistence mapping
- FTP input validation

### 2. Integration tests

Use lightweight integration tests for:

- service orchestration over temporary files
- SQLite repository behavior using temporary databases
- end-to-end scan/report flows over fixture directories
- adapter dispatch and normalization
- CLI invocation with controlled fixtures

### 3. UI tests

Keep Kivy UI tests minimal and focused.
Prefer testing view-model/service orchestration over brittle widget-level behavior.
If UI behavior is tested, scope it narrowly and document assumptions.

---

## Mandatory regression testing

Every bug fix must include at least one regression test when practical.

If a bug is caused by:

- malformed `.po`
- missing domain/context metadata
- bad hardcoded detection
- adapter-specific extraction mismatch
- SQLite persistence mismatch
- FTP path handling
- report rendering edge cases

the fix should include a targeted test.

---

## What to test when touching each area

### If changing shared PO processing

Test:

- discovery
- locale extraction
- family grouping
- synchronization
- plurals
- fuzzy/untranslated handling
- output persistence

### If changing scanners

Test:

- detection behavior
- false-positive control where feasible
- file/line attribution
- classification correctness

### If changing adapters/plugins

Test:

- project/framework detection
- target-specific extraction behavior
- normalization into shared contracts
- failure behavior for invalid configurations

### If changing report generation

Test:

- output format
- escaping/serialization behavior
- stable structure for Markdown/JSON/CSV
- empty result behavior

### If changing SQLite code

Test:

- schema expectations
- inserts/updates/deletes
- idempotency where applicable
- record retrieval and mapping

### If changing FTP code

Test:

- path normalization
- configuration validation
- failure behavior through mocks/stubs
- no accidental destructive behavior

### If changing CLI

Test:

- argument parsing
- command dispatch
- error messaging
- output files where applicable

### If changing Kivy orchestration

Test:

- service invocation boundaries
- state transitions that do not require brittle rendering tests
- error propagation to presentation layer abstractions if present

---

## Fixtures

Prefer small and explicit fixtures for:

- miniature source trees
- `.po` samples
- `.php/.py/.js/.json/.twig/.tpl/.html/.jinja` samples
- SQLite temp DB
- FTP client stubs
- output directories
- sample site/project records

Do not use oversized fixtures when a focused one is enough.

---

## Mocking guidance

Mock external dependencies such as:

- translation provider
- FTP client
- platform-specific integrations
- time-sensitive or OS-specific behavior where needed

Do not over-mock internal domain logic.

---

## Recommended commands

Examples:

```bash
python -m pytest
python -m pytest tests/unit
python -m pytest tests/integration
```

If the project later formalizes dedicated commands, update this file and the repository maps.

---

## Coverage expectations

Coverage should be strong in shared services, adapters, scanning, persistence, and reporting layers.

High-value targets:

- services
- adapter registry and adapters
- scanners
- repositories
- CLI
- report generation

Widget rendering internals are a lower priority than domain correctness and orchestration boundaries.

---

## Before merging or concluding a task

Verify:

- tests for changed behavior exist
- regression coverage exists for fixed bugs
- adapter-specific changes have adapter tests
- no new untested report/export path was introduced
- no new persistence or FTP behavior was added without tests

---

## Mandatory workflow: test-first development

This repository uses both BDD and TDD.

### Required sequence for new functionality

For every non-trivial feature or behavior change:

1. Define the relevant use case.
2. Define acceptance criteria.
3. Write BDD scenarios first.
4. Write unit and integration tests next.
5. Run the test suite and confirm the new tests fail.
6. Implement the minimum code necessary.
7. Run the full relevant suite again.
8. Refactor only after all tests and scenarios pass.

This order is mandatory.

---

## BDD expectations

BDD scenarios must describe externally observable behavior.

Each meaningful feature should include scenarios for:

- happy path
- important edge cases
- invalid input
- operational failures
- expected exceptions or error outcomes

BDD should focus on system behavior and use cases, not brittle visual assertions.

Recommended areas for BDD coverage:

- site/project registration
- adapter detection and resolution
- FTP synchronization flows
- PO processing flows
- audit/report flows
- invalid configuration handling
- failure propagation

---

## TDD expectations

Unit and integration tests must be written before implementation.

At minimum, tests should cover:

- core happy path
- edge conditions
- validation failures
- expected operational exceptions
- regression cases for known bugs

Do not add implementation first and “backfill” tests afterward except for purely mechanical refactors that do not change behavior.

---

## Refactoring rule

Refactoring is allowed only after:

- BDD scenarios exist
- unit/integration tests exist
- tests fail first
- implementation brings the suite back to green

Refactoring must preserve behavior and keep the full suite green.
