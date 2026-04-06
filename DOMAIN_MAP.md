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
- FTP settings
- preferred locales
- site-specific processing options

### Excludes
- UI rendering details
- raw screen state
- report formatting

---

## Domain 2: FTP synchronization

### Responsibility

Download or synchronize site content from remote FTP sources into local workspaces.

### Includes
- connection validation
- remote path handling
- download/sync orchestration
- local target preparation

### Excludes
- UI widget logic
- report generation
- direct persistence concerns not related to FTP operations

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
- source-root conventions
- configuration-file parsing
- database configuration extraction
- framework-aware enrichment of findings

### Examples
- WordPress adapter parsing `wp-config.php`
- Django adapter resolving `settings.py` or related settings modules
- Flask adapter inspecting config modules or factory conventions

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
- FTP connection logic
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
- FTP sessions
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

### Excludes
- UI-driven direct SQL
- scanner logic
- FTP operations

---

## Boundary rules

- Presentation talks to services, not directly to domain internals or infrastructure internals.
- Presentation may use fake/mock service implementations for local shell development and tests, but those fakes must still respect the same contracts.
- Reporting consumes findings; it does not discover them.
- Persistence stores application data; it does not implement UI flows.
- FTP is infrastructure and must stay isolated behind service boundaries.
- Shared translation services and source auditing are related but distinct domains.
- Framework adapters/plugins isolate target-specific behavior from shared services.
