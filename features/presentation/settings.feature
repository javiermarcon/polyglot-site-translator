Feature: Frontend settings management
  As an operator of the Kivy application
  I want an extensible settings area in the frontend shell
  So that UI behavior can be configured without coupling screens to persistence details

  Scenario: Open the settings screen from the application menu
    Given the frontend shell is wired with seeded fake services
    When the operator opens the application menu
    Then the application menu shows the main navigation groups
    When the operator opens the settings screen from the application menu
    Then the settings route is active
    And the settings screen shows the App / UI / Kivy section

  Scenario: Load the default settings state
    Given the frontend shell is wired with seeded fake services
    When the operator opens the settings screen
    Then the settings draft uses the default window size
    And the settings draft keeps remember last screen disabled
    And the settings screen shows a single theme selector with explanations

  Scenario: Modify settings and save them
    Given the frontend shell is wired with seeded fake services
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
    Given the frontend shell is wired with seeded fake services
    And the operator has opened the settings screen
    When the operator sets the compact window size to 550 by 700
    And the operator applies the settings changes
    Then the saved settings keep the compact window size

  Scenario: Reopen settings and see the saved state
    Given the frontend shell is wired with seeded fake services
    And the operator has saved custom settings
    When the operator opens the settings screen
    Then the settings draft shows the persisted custom values

  Scenario: Reset settings to defaults
    Given the frontend shell is wired with seeded fake services
    And the operator has saved custom settings
    When the operator restores the default settings
    Then the settings draft uses the default window size
    And the settings draft keeps remember last screen disabled

  Scenario: Browse planned settings categories
    Given the frontend shell is wired with seeded fake services
    And the operator has opened the settings screen
    When the operator selects the settings section "translation"
    Then the settings screen shows the selected planned section

  Scenario: Handle a controlled load error
    Given the frontend shell is wired with a failing settings load service
    When the operator opens the settings screen
    Then the settings screen shows a failed status
    And the frontend shell shows the controlled settings error message

  Scenario: Handle a controlled save error
    Given the frontend shell is wired with a failing settings save service
    And the operator has opened the settings screen
    When the operator enables remember last screen
    And the operator applies the settings changes
    Then the settings screen shows a failed status
    And the frontend shell shows the controlled settings error message
