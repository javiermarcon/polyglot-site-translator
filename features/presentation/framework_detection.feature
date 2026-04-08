Feature: Framework adapter detection
  As an operator of the localization desktop application
  I want the system to detect the framework of a local project path
  So that project metadata can be enriched without hardcoding framework rules in the UI

  Scenario: Detect a WordPress project from the project flow
    Given the frontend shell is wired with framework detection and SQLite-backed site registry services
    And a local WordPress project exists
    When the operator registers the local project using the detected path
    Then the project detail shows the detected framework "WordPress"
    And the project detail shows framework detection evidence

  Scenario: Detect a Django project from the project flow
    Given the frontend shell is wired with framework detection and SQLite-backed site registry services
    And a local Django project exists
    When the operator registers the local project using the detected path
    Then the project detail shows the detected framework "Django"
    And the project detail shows framework detection evidence

  Scenario: Detect a Flask project from the project flow
    Given the frontend shell is wired with framework detection and SQLite-backed site registry services
    And a local Flask project exists
    When the operator registers the local project using the detected path
    Then the project detail shows the detected framework "Flask"
    And the project detail shows framework detection evidence

  Scenario: Handle a project path without any supported framework match
    Given the frontend shell is wired with framework detection and SQLite-backed site registry services
    And a local generic project exists
    When the operator registers the local project using the detected path
    Then the project detail shows that no framework was detected
    And the stored project framework keeps the operator-provided value

  Scenario: Handle insufficient partial framework evidence in a controlled way
    Given the frontend shell is wired with framework detection and SQLite-backed site registry services
    And a local project with partial WordPress evidence exists
    When the operator registers the local project using the detected path
    Then the project detail shows that no framework was detected
    And the project detail shows framework detection warnings

  Scenario: Show an audit preview without fake framework findings when nothing was detected
    Given the frontend shell is wired with framework detection and SQLite-backed site registry services
    And a local generic project exists
    When the operator registers the local project using the detected path
    And the operator starts the audit workflow from the detected project
    Then the audit preview shows zero framework findings
    And the audit preview explains that no supported framework was detected

  Scenario: Show the auto-discovered framework options in the project editor
    Given the frontend shell is wired with framework detection and SQLite-backed site registry services
    When the operator opens the create project workflow for framework selection
    Then the framework combo shows the auto-discovered supported options
