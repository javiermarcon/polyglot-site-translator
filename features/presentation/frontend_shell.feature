Feature: Kivy frontend shell for multi-framework localization workflows
  As an operator of the localization desktop application
  I want a navigable frontend shell backed by contracts and fakes
  So that future services can plug in without rewriting the UI layer

  Scenario: Open the app and view the dashboard
    Given the frontend shell is wired with seeded fake services
    When the operator opens the application
    Then the dashboard is the active route
    And the dashboard shows the main workflow sections

  Scenario: Navigate to the projects list and select a project
    Given the frontend shell is wired with seeded fake services
    When the operator opens the projects list
    And the operator selects the project "wp-site"
    Then the project detail route is active for "wp-site"
    And the project detail shows available workflow actions

  Scenario: Trigger a fake sync action from the project detail
    Given the frontend shell is wired with seeded fake services
    And the operator has opened the detail for project "wp-site"
    When the operator starts the sync workflow
    Then the sync panel shows a completed status
    And the sync panel reports the synchronized file count

  Scenario: Trigger a fake audit action from the project detail
    Given the frontend shell is wired with seeded fake services
    And the operator has opened the detail for project "wp-site"
    When the operator starts the audit workflow
    Then the audit panel shows a completed status
    And the audit panel reports the finding summary

  Scenario: Trigger fake PO processing from the project detail
    Given the frontend shell is wired with seeded fake services
    And the operator has opened the detail for project "wp-site"
    When the operator starts the po processing workflow
    Then the po processing panel shows a completed status
    And the po processing panel reports the processed family count

  Scenario: Show an empty projects list
    Given the frontend shell is wired with an empty fake catalog
    When the operator opens the projects list
    Then the projects list is empty
    And the projects screen shows an empty state message

  Scenario: Surface a controlled service error
    Given the frontend shell is wired with a failing sync service
    And the operator has opened the detail for project "wp-site"
    When the operator starts the sync workflow
    Then the sync panel shows a failed status
    And the frontend shell shows the controlled error message
