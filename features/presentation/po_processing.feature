Feature: PO processing workflow
  As an operator working with project locale variants
  I want the PO workflow to synchronize reusable translations between variants
  So that missing entries are completed without duplicating translation work

  Scenario: Synchronize missing entries between locale variants
    Given a site project with PO locale variants in the local workspace
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports synchronized entries

  Scenario: Keep completed status when no locale variants are found
    Given a site project without PO locale variants in the local workspace
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports zero processed families
