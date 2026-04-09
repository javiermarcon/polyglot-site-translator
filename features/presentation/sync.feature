Feature: Remote to local project synchronization
  As an operator of the localization desktop application
  I want to synchronize project files from the configured remote source
  So that the local workspace is prepared for later audit and localization workflows

  Scenario: Synchronize a project from a configured remote source
    Given the frontend shell is wired with a real sync workflow
    And the registered project "marketing-site" has remote files available
    When the operator opens the synced detail for project "marketing-site"
    And the operator starts the sync workflow
    Then the sync panel shows a completed status
    And the sync panel reports 2 downloaded files

  Scenario: Reject sync when the project has no remote connection
    Given the frontend shell is wired with a real sync workflow
    And the registered project "local-only-site" has no remote connection
    When the operator opens the synced detail for project "local-only-site"
    And the operator starts the sync workflow
    Then the sync panel shows a failed status
    And the sync panel reports the sync error code "missing_remote_connection"

  Scenario: Surface a controlled error when the remote connection fails
    Given the frontend shell is wired with a real sync workflow
    And the registered project "broken-remote-site" fails while listing the remote files
    When the operator opens the synced detail for project "broken-remote-site"
    And the operator starts the sync workflow
    Then the sync panel shows a failed status
    And the sync panel reports the sync error code "remote_listing_failed"

  Scenario: Complete sync successfully when the remote source is empty
    Given the frontend shell is wired with a real sync workflow
    And the registered project "empty-remote-site" has an empty remote source
    When the operator opens the synced detail for project "empty-remote-site"
    And the operator starts the sync workflow
    Then the sync panel shows a completed status
    And the sync panel reports 0 downloaded files

  Scenario: Show the sync result in the sync screen
    Given the frontend shell is wired with a real sync workflow
    And the registered project "marketing-site" has remote files available
    When the operator opens the synced detail for project "marketing-site"
    And the operator starts the sync workflow
    Then the sync screen shows the downloaded file count

  Scenario: Open a dedicated sync progress window from the project detail
    Given the frontend shell is wired with a real sync workflow
    And the registered project "marketing-site" has remote files available
    When the operator opens the synced detail for project "marketing-site"
    And the operator starts the sync workflow from the project detail screen
    Then the sync progress window is open
    And the sync progress window lists the remote sync commands
