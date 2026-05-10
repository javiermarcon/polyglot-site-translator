Feature: PO processing workflow
  As an operator working with project locale variants
  I want the PO workflow to reuse and translate missing gettext entries
  So that the processed PO files are actually completed and saved

  Scenario: Synchronize missing entries between locale variants
    Given a site project with PO locale variants in the local workspace
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one found family
    And the PO processing result reports one processed family
    And the PO processing result reports one entry completed from initial sync
    And the PO processing result reports synchronized entries
    And the PO processing result reports compiled mo files
    And the processed locale variants contain compiled mo files

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

  Scenario: Skip MO compilation when the project disables it
    Given a site project with untranslated PO locale variants and MO compilation disabled
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports zero compiled mo files
    And the processed locale variants do not contain compiled mo files

  Scenario: Skip external translation when the project disables it
    Given a site project with untranslated PO locale variants and external translator disabled
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports zero translated entries
    And the PO processing result reports two skipped sync-only entries
    And the processed PO file keeps the untranslated text

  Scenario: Continue processing when one PO entry fails in external translation
    Given a site project with one failing PO entry and one translatable entry
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed with errors status
    And the PO processing result reports translated entries
    And the PO processing result reports failed entries for the source file

  Scenario: Continue processing when one MO file fails during compilation
    Given a site project with one MO compilation failure and one compilable locale variant
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed with errors status
    And the PO processing result reports one processed family
    And the PO processing result reports failed mo files for the source file

  Scenario: Run the PO workflow in dry-run mode without writing files
    Given a site project with untranslated PO locale variants and dry-run enabled
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports translated entries
    And the PO processing result reports zero written PO files
    And the PO processing result reports zero compiled mo files
    And the processed PO file keeps the untranslated text

  Scenario: Run the PO workflow in stats-only mode without writing files
    Given a site project with untranslated PO locale variants and stats-only enabled
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports translated entries
    And the PO processing result reports zero written PO files
    And the PO processing result reports zero compiled mo files
    And the processed PO file keeps the untranslated text

  Scenario: Run the PO workflow in only-fuzzy mode
    Given a site project with fuzzy and non-fuzzy untranslated PO entries
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports translated entries
    And the PO processing result reports one fuzzy entry
    And the PO processing result reports only-fuzzy mode enabled
    And the processed PO file translates only fuzzy entries

  Scenario: Reuse a translation from another variant as a separate metric
    Given a site project with reusable translations across locale families
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports two found families
    And the PO processing result reports two processed families
    And the PO processing result reports one reused translation from another variant

  Scenario: Report translation inconsistencies across locale variants
    Given a site project with inconsistent translated PO locale variants
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports one translation inconsistency
    And the PO processing result reports one variant difference
    And the PO processing result reports the inconsistency detail for "Hello"

  Scenario: Report zero translation inconsistencies when the variants match
    Given a site project with PO locale variants in the local workspace
    When the operator runs the PO processing workflow with inconsistency reporting enabled
    Then the PO processing result reports completed status
    And the PO processing result reports one processed family
    And the PO processing result reports zero translation inconsistencies

  Scenario: Reuse cached translations before calling the external provider
    Given a site project with untranslated PO locale variants and a preseeded translation cache
    When the operator runs the PO processing workflow for that site
    Then the PO processing result reports completed status
    And the PO processing result reports translated entries
    And the PO processing result reports one cached translation
    And the PO processing result reports zero provider translations
    And the processed PO file contains the translated text

  Scenario: Ignore the translation cache when the run disables it
    Given a site project with untranslated PO locale variants and a preseeded translation cache
    When the operator runs the PO processing workflow with translation cache disabled
    Then the PO processing result reports completed status
    And the PO processing result reports translated entries
    And the PO processing result reports zero cached translations
    And the PO processing result reports one provider translation
