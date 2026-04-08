# TESTING.md

## Testing goals

This project combines:

- Kivy presentation
- shared translation/localization services
- framework-specific adapters
- source scanning
- SQLite persistence
- remote connection integration
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

Unit tests are mandatory for all non-trivial domain, service, adapter, persistence, reporting, and presentation-orchestration logic.

Unit tests must cover, at minimum:

- happy path behavior
- important edge cases
- invalid input
- validation failures
- expected operational failures
- expected exceptions
- regression scenarios for known bugs

They must not only verify “success cases”.
They must also prove that the code behaves correctly under failure and boundary conditions.

Unit tests must cover isolated logic such as:

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
- remote connection input validation

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
- structured evidence, warnings, and relevant paths
- adapter-registry resolution and ambiguity handling
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
- configured database-path resolution from settings
- explicit persistence/configuration error wrapping
- encrypted secret storage behavior if credential fields are persisted

### If changing remote connection code

Test:

- path normalization
- configuration validation
- discoverable provider catalogs
- optional no-connection flows
- structured connection-test results
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

### If changing TOML settings persistence

Test:

- default loading when the config file does not exist yet
- round-trip save/load behavior
- invalid TOML or invalid setting values
- per-user config-path resolution overrides
- remembered safe startup screens and runtime setting application
- database directory/filename validation and normalization
- integration with the configured SQLite site registry location

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

For headless Linux CI or local headless validation of Kivy tests, use a virtual display:

```bash
xvfb-run -a python -m pytest
```

If the project later formalizes dedicated commands, update this file and the repository maps.
If command changes also affect the normal contributor workflow, installation, or validation entrypoints, update `README.md` in the same patch as required by `AGENTS.md`.

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

For non-trivial new or modified logic in this repository, the expected target remains at least 95% coverage for each relevant file unless a narrow documented exception is justified.

Widget rendering internals are a lower priority than domain correctness and orchestration boundaries.

---

## Unit test coverage policy

Unit test coverage is a mandatory quality gate.

### Minimum required coverage

As a rule, unit tests must achieve **at least 95% coverage** for the code they are responsible for validating.

This applies especially to:

- shared services
- domain logic
- adapters
- repositories
- report generation
- CLI behavior
- presentation orchestration / view-model logic

### What “95% coverage” means in practice

Coverage is not just about line execution.
Tests must also exercise meaningful behavioral branches, including:

- success paths
- boundary conditions
- invalid states
- validation failures
- controlled operational failures
- expected exceptions

### Forbidden anti-pattern

It is not acceptable to reach coverage through shallow tests that only touch lines without asserting meaningful behavior.

Coverage must reflect real behavioral verification, not artificial execution.

### Exceptions

If a specific area cannot reasonably reach 95% due to platform/runtime/UI constraints, that exception must be explicitly justified in the task output and should be limited to narrow UI/platform glue, not core logic.

---

## Before merging or concluding a task

Verify:

- tests for changed behavior exist
- regression coverage exists for fixed bugs
- adapter-specific changes have adapter tests
- no new untested report/export path was introduced
- no new persistence or FTP behavior was added without tests
- unit tests cover happy path, edge cases, errors, and expected exceptions
- the affected unit-tested logic meets or exceeds the minimum required coverage target

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

At minimum, tests must cover:

- core happy path
- edge conditions
- validation failures
- expected operational exceptions
- expected domain exceptions
- regression cases for known bugs

For unit-tested logic, the test suite must be sufficiently complete to support the repository’s minimum unit-test coverage target of **95%**.

Do not add implementation first and “backfill” tests afterward except for purely mechanical refactors that do not change behavior
---

## Refactoring rule

Refactoring is allowed only after:

- BDD scenarios exist
- unit/integration tests exist
- tests fail first
- implementation brings the suite back to green

Refactoring must preserve behavior and keep the full suite green.
