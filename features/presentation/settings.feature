Feature: Frontend settings management
  As an operator of the Kivy application
  I want an extensible settings area in the frontend shell
  So that UI behavior can be configured without coupling screens to persistence details

  Scenario: Open the settings screen from the application menu
    Given the frontend shell is wired with seeded frontend test doubles
    When the operator opens the application menu
    Then the application menu shows the main navigation groups
    When the operator opens the settings screen from the application menu
    Then the settings route is active
    And the settings screen shows the App / UI / Kivy section

  Scenario: Load the default settings state
    Given the frontend shell is wired with seeded frontend test doubles
    When the operator opens the settings screen
    Then the settings draft uses the default window size
    And the settings draft keeps remember last screen disabled
    And the settings screen shows a single theme selector with explanations

  Scenario: Modify settings and save them
    Given the frontend shell is wired with seeded frontend test doubles
    And the operator has opened the settings screen
    When the operator enables remember last screen
    And the operator enables developer mode
    And the operator sets the theme mode to "dark"
    And the operator sets the window size to 1440 by 900
    And the operator applies the settings changes
    Then the settings screen shows the changes as saved
    And the settings save exposes a saved confirmation message
    And the saved settings keep remember last screen enabled
    And the saved settings keep the selected window size

  Scenario: Save a compact window size profile
    Given the frontend shell is wired with seeded frontend test doubles
    And the operator has opened the settings screen
    When the operator sets the compact window size to 550 by 700
    And the operator applies the settings changes
    Then the saved settings keep the compact window size

  Scenario: Reopen settings and see the saved state
    Given the frontend shell is wired with seeded frontend test doubles
    And the operator has saved custom settings
    When the operator opens the settings screen
    Then the settings draft shows the persisted custom values

  Scenario: Reopen settings from a new shell and keep the TOML-backed state
    Given the frontend shell is wired with TOML-backed settings persistence
    And the operator has saved custom settings
    When the operator restarts the frontend shell
    And the operator opens the settings screen
    Then the settings draft shows the persisted custom values

  Scenario: Reset settings to defaults
    Given the frontend shell is wired with seeded frontend test doubles
    And the operator has saved custom settings
    When the operator restores the default settings
    Then the settings draft uses the default window size
    And the settings draft keeps remember last screen disabled

  Scenario: Browse translation settings and persist translation defaults
    Given the frontend shell is wired with seeded frontend test doubles
    And the operator has opened the settings screen
    When the operator selects the settings section "translation"
    And the operator sets the default project locale to "es_ES, es_AR"
    And the operator enables default MO compilation
    And the operator applies the settings changes
    Then the settings screen shows the translation settings section
    And the saved settings keep the default project locale "es_ES,es_AR"
    And the saved settings keep default MO compilation enabled

  Scenario: Configure global sync rules and persist them
    Given the frontend shell is wired with TOML-backed settings persistence
    And the operator has opened the settings screen
    When the operator selects the settings section "frameworks"
    And the operator enables gitignore-based sync exclusions
    And the operator adds the global sync rule ".git" as "exclude" "directory"
    And the operator applies the settings changes
    Then the settings screen shows the changes as saved
    And the saved settings enable gitignore-based sync exclusions
    And the saved settings contain the global sync rule ".git"

  Scenario: Configure framework sync rules and reopen them from TOML
    Given the frontend shell is wired with TOML-backed settings persistence
    And the operator has opened the settings screen
    When the operator selects the settings section "frameworks"
    And the operator adds the framework sync rule ".venv" for "django" as "exclude" "directory"
    And the operator applies the settings changes
    And the operator restarts the frontend shell
    And the operator opens the settings screen
    And the operator selects the settings section "frameworks"
    Then the saved settings contain the framework sync rule ".venv" for "django"

  Scenario: Handle a controlled load error
    Given the frontend shell is wired with a failing settings-load test double
    When the operator opens the settings screen
    Then the settings screen shows a failed status
    And the frontend shell shows the controlled settings error message

  Scenario: Handle a controlled save error
    Given the frontend shell is wired with a failing settings-save test double
    And the operator has opened the settings screen
    When the operator enables remember last screen
    And the operator applies the settings changes
    Then the settings screen shows a failed status
    And the frontend shell shows the controlled settings error message
