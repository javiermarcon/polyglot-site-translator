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

Python source lines must stay within 88 characters so the formatter and linter enforce the same
explicit limit across the repository.

All new and modified code must explicitly satisfy those standards. Do not rely on accidental
compatibility or on whichever subset a tool happens to be checking by default.

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

- All modules, classes, functions, and methods, public or private, must have meaningful
  docstrings.
- Docstrings must be multi-line and structured; one-line placeholder docstrings are not acceptable
  for behavioral symbols.
- Docstrings must explain intent and important behavior, not restate the name.
- Docstrings should describe relevant inputs, outputs, side effects, and failure behavior when
  that context matters to maintainers.
- Functions and methods should use sections such as `Args:`, `Returns:`, and `Raises:` whenever
  they apply.
- Classes should use sections such as `Attributes:` when they expose meaningful state.
- Avoid filler text.
- Keep docstrings aligned with actual behavior.
- Follow PEP257 explicitly; do not treat docstrings as optional commentary.

---

## Error handling

- Never use `except Exception`.
- Catch concrete exceptions only.
- Do not ignore failures silently.
- Use Python `assert` statements only in pytest tests under `tests/`.
- Outside pytest tests, including Behave steps, use explicit exceptions because
  optimized bytecode removes `assert` statements.
- Do not use `next()` without an explicit fallback or deliberate exception
  path. Missing items must fail with clear context instead of implicit
  `StopIteration`.
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
- Introduce instance attributes only in `__init__`; later methods may mutate
  existing state but must not create new attributes on demand.
- Mark methods as `@staticmethod` when they do not use instance or class state.
- Avoid mutable global runtime state. Prefer dependency injection, explicit
  state objects, or context-local state for process-wide presentation settings.
- Do not access protected members of another class. If a workflow or test needs
  to observe state, add a narrow public method or property on the owning class.

---

## Test paths

- Do not hardcode `/tmp`, `/var/tmp`, or platform-specific temporary paths in
  tests or BDD steps.
- Use `tempfile`, `tmp_path`, or repository-provided temporary fixtures for
  temporary files and directories.
- Literal path strings are acceptable only when the path is domain data being
  parsed or validated, not when the test needs a real temporary location.

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

## Kivy visual design rules

Kivy UI changes must follow a consistent visual system.

Screens must use:

- clear visual hierarchy: title, subtitle/help text, primary content, actions
- consistent spacing based on small/medium/large spacing tokens
- reusable card/panel containers for grouped content
- one obvious primary action per screen or workflow area
- secondary/destructive actions visually separated from primary actions
- readable typography sizes for headings, section labels, body text, hints, and errors
- consistent button heights, input heights, margins, and padding
- explicit empty, loading, success, warning, and error states
- responsive layouts that remain usable at narrow desktop widths
- theme tokens from `presentation/kivy/theme.py`, not ad hoc colors
- static operator-facing copy routed through the presentation localization
  helper or reusable widgets backed by gettext catalogs

Avoid:

- raw unstyled `BoxLayout` screens with dense controls
- magic numbers repeated across screens
- hardcoded colors inside individual widgets
- hardcoded UI language lists or inline translation dictionaries in screens
- mixing status messages, forms, and actions without grouping
- screens that only “work” but do not communicate state clearly

When adding or changing a screen, prefer reusable presentation widgets such as:

- card containers
- section headers
- toolbar/action rows
- status banners
- form rows
- primary/secondary/destructive buttons
- empty-state panels
- progress panels

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

## Documentation

- Keep documentation factual and current.
- Keep `README.md` in English and `README_es.md` in Spanish.
- Update both README files in the same patch when a change affects setup,
  commands, workflows, visible behavior, or contributor expectations.

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
