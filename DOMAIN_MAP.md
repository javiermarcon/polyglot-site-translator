# DOMAIN_MAP.md

## Purpose

This document maps the main functional domains of the repository and their boundaries.

---

## Domain 1: Site registry

### Responsibility

Manage the local record of sites or projects known to the application.

### Includes
- site/project name
- local workspace path
- framework type
- optional remote connection linkage
- encrypted remote password persistence
- preferred locales
- site-specific processing options
- active/inactive status

### Excludes
- UI rendering details
- raw screen state
- report formatting
- SQLite path composition inside widgets

---

## Domain 2: Remote connections and synchronization

### Responsibility

Configure, validate, test, and later synchronize optional remote sources into local workspaces.

### Includes
- discoverable connection-type catalogs
- optional remote connection configs
- structured connection-test results
- connection validation
- remote path handling
- download/sync orchestration
- local target preparation

### Excludes
- UI widget logic
- report generation
- direct persistence concerns not related to remote operations

---

## Domain 3: Shared translation services

### Responsibility

Handle reusable localization and translation logic.

### Includes
- `.po` discovery
- locale extraction
- family grouping
- translation synchronization
- translation reuse
- optional translation provider use
- optional `.mo` compilation

### Excludes
- framework-specific configuration discovery
- UI concerns
- report rendering

---

## Domain 4: Framework adapters / plugins

### Responsibility

Encapsulate framework-specific conventions and extraction rules.

### Includes
- project type detection
- typed evidence, warnings, and relevant paths for matches or non-matches
- source-root conventions
- configuration-file parsing
- database configuration extraction
- framework-aware enrichment of findings

### Examples
- WordPress adapter parsing `wp-config.php`
- Django adapter resolving `settings.py` or related settings modules
- Flask adapter inspecting config modules or factory conventions

### Current concrete implementation
- ordered adapter registry with explicit ambiguity handling and package auto-discovery
- typed `FrameworkDetectionResult` values
- typed framework descriptors for selectors/catalogs
- WordPress detection via `wp-config.php`, `wp-content/`, `wp-includes/`, and optional `wp-admin/`
- Django detection via `manage.py` plus `settings.py`, `wsgi.py`, or `asgi.py`
- Flask detection via `app.py`, `wsgi.py`, factory markers, `babel.cfg`, and `translations/`

### Excludes
- shared PO logic
- report rendering
- UI behavior

---

## Domain 5: Source auditing

### Responsibility

Inspect source trees for localization-related issues beyond PO files.

### Includes
- PHP/Python/JS/template scanning
- hardcoded string detection
- gettext misuse detection
- JSON i18n detection
- target-specific candidate discovery where relevant

### Excludes
- rendering reports
- remote connection logic
- UI behavior

---

## Domain 6: Reporting

### Responsibility

Export normalized findings and summaries.

### Includes
- Markdown
- JSON
- CSV
- generated snippets
- grouped summaries

### Excludes
- scanning
- persistence
- UI orchestration

---

## Domain 7: Presentation

### Responsibility

Provide the graphical user experience through Kivy.

### Includes
- screens
- widgets
- navigation router
- selected-project UI context
- presentation shell/controller orchestration
- typed screen state and workflow summaries
- typed settings sections and editable draft settings
- user-triggered actions
- display of progress, summaries, errors, and outputs

### Excludes
- domain rules
- raw SQL
- remote sessions
- scanning heuristics
- report generation internals
- adapter extraction internals

---

## Domain 8: Persistence

### Responsibility

Store and retrieve application-owned data locally.

### Includes
- SQLite schema access
- repositories
- mapping between rows and models
- final database-path resolution from typed frontend settings
- local secret-key handling for encrypted persisted credentials

### Excludes
- UI-driven direct SQL
- scanner logic
- remote operations

---

## Boundary rules

- Presentation talks to services, not directly to domain internals or infrastructure internals.
- Presentation may use fake/mock service implementations for local shell development and tests, but those fakes must still respect the same contracts.
- Reporting consumes findings; it does not discover them.
- Persistence stores application data; it does not implement UI flows.
- Remote transport logic is infrastructure and must stay isolated behind service boundaries.
- Shared translation services and source auditing are related but distinct domains.
- Framework adapters/plugins isolate target-specific behavior from shared services.
