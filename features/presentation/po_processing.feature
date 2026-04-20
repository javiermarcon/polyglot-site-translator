Feature: PO processing workflow
  As an operator working with project locale variants
  I want the PO workflow to reuse and translate missing gettext entries
  So that the processed PO files are actually completed and saved

  Scenario: Synchronize missing entries between locale variants
    Given a site project with PO locale variants in the local workspace
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports synchronized entries

  Scenario: Translate missing entries when no variant already contains them
    Given a site project with untranslated PO locale variants in the local workspace
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports translated entries
    And the processed PO file contains the translated text

  Scenario: Translate several missing entries from the same PO file
    Given a site project with several untranslated entries in one PO file
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports three translated entries
    And the processed PO file contains all translated texts
    And the PO processing progress reports the current file and entry

  Scenario: Keep completed status when no locale variants are found
    Given a site project without PO locale variants in the local workspace
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports zero processed families

  Scenario: Run the PO workflow with selected locales instead of the persisted default
    Given a site project with Portuguese PO locale variants in the local workspace
    When the operator runs the PO processing workflow for that site with selected locale "pt_BR"
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports synchronized entries

  Scenario: Continue processing when one PO entry fails in external translation
    Given a site project with one failing PO entry and one translatable entry
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed with errors status
    And the PO processing result reports translated entries
    And the PO processing result reports failed entries for the source file
