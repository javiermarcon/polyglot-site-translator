Feature: Framework adapter sync filters
  As an operator of the localization desktop application
  I want framework adapters to resolve reusable sync filters
  So that future sync workflows can limit transfers to framework-relevant paths

  Scenario: Resolve WordPress sync filters from the registered framework
    Given a registered "wordpress" project for sync filter resolution
    When the operator resolves the framework sync scope
    Then the resolved sync scope status is "filtered"
    And the resolved sync scope includes the filter "wp-content/languages"
    And the resolved sync scope includes the filter "wp-content/themes"
    And the resolved sync scope includes the filter "wp-content/plugins"

  Scenario: Resolve Django sync filters from the registered framework
    Given a registered "django" project for sync filter resolution
    When the operator resolves the framework sync scope
    Then the resolved sync scope status is "filtered"
    And the resolved sync scope includes the filter "locale"

  Scenario: Resolve Flask sync filters from the registered framework
    Given a registered "flask" project for sync filter resolution
    When the operator resolves the framework sync scope
    Then the resolved sync scope status is "filtered"
    And the resolved sync scope includes the filter "translations"
    And the resolved sync scope includes the filter "babel.cfg"

  Scenario: Return an explicit unresolved scope when no adapter is available
    Given a registered "customapp" project for sync filter resolution
    When the operator resolves the framework sync scope
    Then the resolved sync scope status is "adapter_unavailable"
    And the resolved sync scope reports no sync filters

  Scenario: Return an explicit unresolved scope when the framework is unknown
    Given a registered "unknown" project for sync filter resolution
    When the operator resolves the framework sync scope
    Then the resolved sync scope status is "framework_unresolved"
    And the resolved sync scope reports no sync filters
