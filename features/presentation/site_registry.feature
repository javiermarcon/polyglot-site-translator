Feature: SQLite-backed site registry management
  As an operator of the localization desktop application
  I want to configure and use a real SQLite-backed site registry
  So that projects remain persisted across sessions without coupling the UI to SQL details

  Scenario: Configure the SQLite database location from general settings
    Given the frontend shell is wired with SQLite-backed site registry services
    And the operator has opened the settings screen
    When the operator sets the database directory to "/tmp/polyglot-db"
    And the operator sets the database filename to "registry.sqlite3"
    And the operator applies the settings changes
    And the operator restarts the SQLite-backed frontend shell
    And the operator opens the settings screen
    Then the settings draft shows the configured database directory
    And the settings draft shows the configured database filename

  Scenario: Use the translation settings defaults when creating a project
    Given the frontend shell is wired with SQLite-backed site registry services
    And the operator has opened the settings screen
    When the operator selects the settings section "translation"
    And the operator sets the default project locale to "es_AR, es_ES"
    And the operator disables default MO compilation
    And the operator applies the settings changes
    And the operator opens the create project workflow
    Then the project editor uses the default locale "es_AR,es_ES"
    And the project editor uses MO compilation disabled

  Scenario: Register the first site in an empty SQLite registry
    Given the frontend shell is wired with SQLite-backed site registry services
    When the operator opens the projects list
    Then the projects list is empty
    When the operator opens the create project workflow
    And the operator submits a new site registry entry
    Then the project detail route is active for the created site
    And the project detail shows the persisted site registry values

  Scenario: Reopen the SQLite registry and list the persisted site
    Given the frontend shell is wired with SQLite-backed site registry services
    And a site has been registered in the SQLite registry
    When the operator restarts the SQLite-backed frontend shell
    And the operator opens the projects list
    Then the projects list shows the persisted SQLite site

  Scenario: Update a persisted SQLite site
    Given the frontend shell is wired with SQLite-backed site registry services
    And a site has been registered in the SQLite registry
    When the operator opens the edit project workflow for the persisted site
    And the operator updates the local path and remote connection data
    Then the project detail shows the updated persisted site registry values
    And reopening the persisted site editor shows the updated remote connection values

  Scenario: Persist the project MO compilation preference
    Given the frontend shell is wired with SQLite-backed site registry services
    When the operator opens the create project workflow
    And the operator submits a new site registry entry with MO compilation disabled
    Then the project detail shows MO compilation disabled
    And reopening the persisted site editor shows MO compilation disabled

  Scenario: Persist the adapter-filter sync preference in the remote configuration
    Given the frontend shell is wired with SQLite-backed site registry services
    When the operator opens the create project workflow
    And the operator submits a new site registry entry with adapter sync filters enabled
    Then the project detail shows the persisted sync mode "filtered"
    And reopening the persisted site editor shows adapter sync filters enabled

  Scenario: Persist project sync-rule overrides from the editor
    Given the frontend shell is wired with SQLite-backed site registry services
    When the operator opens the create project workflow
    And the operator submits a new Django site registry entry with custom sync rule overrides
    Then reopening the persisted site editor shows the custom sync rule "locale_custom"
    And reopening the persisted site editor shows the adapter rule "__pycache__" disabled

  Scenario: Normalize a persisted default locale list
    Given the frontend shell is wired with SQLite-backed site registry services
    When the operator opens the create project workflow
    And the operator submits a new site registry entry with a spaced default locale list
    Then the project detail shows the persisted default locale "es_ES,es_AR"
    And reopening the persisted site editor shows the persisted default locale "es_ES,es_AR"

  Scenario: Reject an invalid default locale value
    Given the frontend shell is wired with SQLite-backed site registry services
    When the operator opens the create project workflow
    And the operator submits a new site registry entry with an invalid default locale
    Then the project editor shows the default locale validation error

  Scenario: Surface an invalid SQLite configuration through the projects flow
    Given the frontend shell is wired with SQLite-backed services and invalid database settings
    When the operator opens the projects list
    Then the projects list is empty
    And the frontend shell shows the controlled site registry error message

  Scenario: Surface a controlled SQLite persistence failure
    Given the frontend shell is wired with a failing SQLite-backed site registry service
    When the operator opens the projects list
    Then the projects list is empty
    And the frontend shell shows the controlled site registry error message
