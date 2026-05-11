Feature: Discoverable remote connection workflows
  As an operator of the localization desktop application
  I want optional remote connection settings per project
  So that I can manage projects with or without remote access and test supported transports safely

  Scenario: Register a project without any remote connection
    Given the frontend shell is wired with SQLite-backed remote connection services
    When the operator opens the create project workflow
    Then the remote connection selector includes the "No Remote Connection" option
    When the operator submits a new project without remote connection
    Then the project detail shows that no remote connection is configured

  Scenario: Test a valid remote connection from the project editor
    Given the frontend shell is wired with SQLite-backed remote connection services
    And remote connection tests succeed for "sftp"
    When the operator opens the create project workflow
    And the operator fills a valid "sftp" remote connection draft
    And the operator runs the remote connection test from the editor
    Then the project editor shows a successful remote connection test result

  Scenario: Surface a failed remote connection test from the project editor
    Given the frontend shell is wired with SQLite-backed remote connection services
    And remote connection tests fail for "ftp" with code "authentication_failed"
    When the operator opens the create project workflow
    And the operator fills a valid "ftp" remote connection draft
    And the operator runs the remote connection test from the editor
    Then the project editor shows a failed remote connection test result

  Scenario: Reject a remote connection test without configured remote settings
    Given the frontend shell is wired with SQLite-backed remote connection services
    When the operator opens the create project workflow
    And the operator fills a draft without remote connection
    And the operator runs the remote connection test from the editor
    Then the project editor shows the missing remote connection validation error

  Scenario: Reject a remote connection test with an invalid remote port
    Given the frontend shell is wired with SQLite-backed remote connection services
    When the operator opens the create project workflow
    And the operator fills an invalid "sftp" remote connection draft
    And the operator runs the remote connection test from the editor
    Then the project editor shows the invalid remote port validation error
