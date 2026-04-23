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
    And the sync progress window shows file download commands while sync is running

  Scenario: Surface a startup sync failure in the progress window
    Given the frontend shell is wired with a real sync workflow
    And the registered project "broken-remote-site" fails while listing the remote files
    When the operator opens the synced detail for project "broken-remote-site"
    And the operator starts the sync workflow from the project detail screen
    Then the sync progress window is open
    And the sync progress window shows a failed status
    And the sync progress window shows the sync error message

  Scenario: Offer explicit host-key trust when an SSH host is unknown
    Given the frontend shell is wired with a real sync workflow
    And the registered project "unknown-ssh-host-site" fails because the SSH host key is unknown
    When the operator opens the synced detail for project "unknown-ssh-host-site"
    And the operator starts the sync workflow from the project detail screen
    Then the sync progress window is open
    And the sync progress window shows a failed status
    And the sync progress window offers the SSH host-key trust action

  Scenario: Keep only the latest sync operations in the progress window regardless of transport
    Given the frontend shell is wired with a real sync workflow
    And the sync command log limit is 2 operations
    And the registered project "marketing-site" has remote files available
    When the operator opens the synced detail for project "marketing-site"
    And the operator starts the sync workflow from the project detail screen
    Then the sync progress window is open
    And the sync progress window keeps only the last 2 operations

  Scenario: Reuse a single remote session for a multi-file sync
    Given the frontend shell is wired with a real sync workflow
    And the registered project "marketing-site" has remote files available
    When the operator opens the synced detail for project "marketing-site"
    And the operator starts the sync workflow from the project detail screen
    Then the sync progress window is open
    And the sync progress window shows a single remote connect command
    And the sync progress window shows a single remote close command

  Scenario: Synchronize local files into the configured remote source
    Given the frontend shell is wired with a real sync workflow
    And the registered project "marketing-site" has local files available for upload
    When the operator opens the synced detail for project "marketing-site"
    And the operator starts the local to remote sync workflow
    Then the sync panel shows a completed status
    And the sync panel reports 2 uploaded files

  Scenario: Reject local to remote sync when the project has no remote connection
    Given the frontend shell is wired with a real sync workflow
    And the registered project "local-only-site" has no remote connection
    When the operator opens the synced detail for project "local-only-site"
    And the operator starts the local to remote sync workflow
    Then the sync panel shows a failed status
    And the sync panel reports the sync error code "missing_remote_connection"

  Scenario: Surface a controlled local to remote error when the remote upload fails
    Given the frontend shell is wired with a real sync workflow
    And the registered project "broken-upload-site" fails while uploading local files
    When the operator opens the synced detail for project "broken-upload-site"
    And the operator starts the local to remote sync workflow
    Then the sync panel shows a failed status
    And the sync panel reports the sync error code "upload_failed"

  Scenario: Complete local to remote sync successfully when the local tree is empty
    Given the frontend shell is wired with a real sync workflow
    And the registered project "empty-local-site" has an empty local source
    When the operator opens the synced detail for project "empty-local-site"
    And the operator starts the local to remote sync workflow
    Then the sync panel shows a completed status
    And the sync panel reports 0 uploaded files

  Scenario: Show the local to remote sync result in the sync screen
    Given the frontend shell is wired with a real sync workflow
    And the registered project "marketing-site" has local files available for upload
    When the operator opens the synced detail for project "marketing-site"
    And the operator starts the local to remote sync workflow
    Then the sync screen shows the uploaded file count

  Scenario: Use adapter sync filters when the persisted project preference enables them
    Given the frontend shell is wired with a real sync workflow
    And the registered project "filtered-sync-site" has mixed remote files and adapter sync filters enabled
    When the operator opens the synced detail for project "filtered-sync-site"
    And the operator starts the sync workflow
    Then the sync panel shows a completed status
    And the sync panel reports 1 downloaded files

  Scenario: Surface a controlled error when adapter sync scope resolution fails
    Given the frontend shell is wired with a real sync workflow and failing adapter sync scope resolution
    And the registered project "scope-broken-site" has mixed remote files and adapter sync filters enabled
    When the operator opens the synced detail for project "scope-broken-site"
    And the operator starts the sync workflow
    Then the sync panel shows a failed status
    And the sync panel reports the sync error code "sync_scope_resolution_failed"

  Scenario: Use full sync when the persisted project preference disables adapter filters
    Given the frontend shell is wired with a real sync workflow
    And the registered project "full-sync-site" has mixed remote files and adapter sync filters disabled
    When the operator opens the synced detail for project "full-sync-site"
    And the operator starts the sync workflow
    Then the sync panel shows a completed status
    And the sync panel reports 2 downloaded files

  Scenario: Apply adapter exclusions during filtered remote to local sync
    Given the frontend shell is wired with a real sync workflow
    And the registered project "django-filtered-site" has django remote files with excluded paths
    When the operator opens the synced detail for project "django-filtered-site"
    And the operator starts the sync workflow
    Then the sync panel shows a completed status
    And the sync panel reports 1 downloaded files

  Scenario: Apply adapter exclusions during filtered local to remote sync
    Given the frontend shell is wired with a real sync workflow
    And the registered project "django-upload-site" has django local files with excluded paths
    When the operator opens the synced detail for project "django-upload-site"
    And the operator starts the local to remote sync workflow
    Then the sync panel shows a completed status
    And the sync panel reports 1 uploaded files
