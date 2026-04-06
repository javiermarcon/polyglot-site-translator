Feature: Frontend settings management
  As an operator of the Kivy application
  I want an extensible settings area in the frontend shell
  So that UI behavior can be configured without coupling screens to persistence details

  Scenario: Open the settings screen from the dashboard
    Given the frontend shell is wired with seeded fake services
    When the operator opens the settings screen
    Then the settings route is active
    And the settings screen shows the App / UI / Kivy section

  Scenario: Load the default settings state
    Given the frontend shell is wired with seeded fake services
    When the operator opens the settings screen
    Then the settings draft uses the default window size
    And the settings draft keeps remember last screen disabled

  Scenario: Modify settings and save them
    Given the frontend shell is wired with seeded fake services
    And the operator has opened the settings screen
    When the operator enables remember last screen
    And the operator enables developer mode
    And the operator sets the theme mode to "dark"
    And the operator applies the settings changes
    Then the settings screen shows the changes as saved
    And the saved settings keep remember last screen enabled

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
