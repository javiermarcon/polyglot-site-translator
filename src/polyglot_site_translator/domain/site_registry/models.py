"""Typed domain models for the site registry subsystem."""

from __future__ import annotations

from dataclasses import dataclass

from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
)


@dataclass(frozen=True)
class SiteRegistrationInput:
    """Validated input payload for create/update site registry workflows.

    Attributes:
        name:
            Documented attribute exposed by this type.
        framework_type:
            Documented attribute exposed by this type.
        local_path:
            Documented attribute exposed by this type.
        default_locale:
            Documented attribute exposed by this type.
        remote_connection:
            Documented attribute exposed by this type.
        is_active:
            Documented attribute exposed by this type.
        compile_mo:
            Documented attribute exposed by this type.
        use_external_translator:
            Documented attribute exposed by this type.
        use_translation_cache:
            Documented attribute exposed by this type.
        only_fuzzy:
            Documented attribute exposed by this type.
        dry_run:
            Documented attribute exposed by this type.
        stats_only:
            Documented attribute exposed by this type.
        report_inconsistencies:
            Documented attribute exposed by this type.
    """

    name: str
    framework_type: str
    local_path: str
    default_locale: str
    remote_connection: RemoteConnectionConfigInput | None
    is_active: bool
    compile_mo: bool = True
    use_external_translator: bool = True
    use_translation_cache: bool = True
    only_fuzzy: bool = False
    dry_run: bool = False
    stats_only: bool = False
    report_inconsistencies: bool = False


@dataclass(frozen=True)
class SiteProject:
    """A site or project persisted in the local site registry.

    Attributes:
        id:
            Documented attribute exposed by this type.
        name:
            Documented attribute exposed by this type.
        framework_type:
            Documented attribute exposed by this type.
        local_path:
            Documented attribute exposed by this type.
        default_locale:
            Documented attribute exposed by this type.
        is_active:
            Documented attribute exposed by this type.
        compile_mo:
            Documented attribute exposed by this type.
        use_external_translator:
            Documented attribute exposed by this type.
        use_translation_cache:
            Documented attribute exposed by this type.
        only_fuzzy:
            Documented attribute exposed by this type.
        dry_run:
            Documented attribute exposed by this type.
        stats_only:
            Documented attribute exposed by this type.
        report_inconsistencies:
            Documented attribute exposed by this type.
    """

    id: str
    name: str
    framework_type: str
    local_path: str
    default_locale: str
    is_active: bool
    compile_mo: bool = True
    use_external_translator: bool = True
    use_translation_cache: bool = True
    only_fuzzy: bool = False
    dry_run: bool = False
    stats_only: bool = False
    report_inconsistencies: bool = False


@dataclass(frozen=True)
class RegisteredSite:
    """Aggregate of a persisted site project and its optional remote config.

    Attributes:
        project:
            Documented attribute exposed by this type.
        remote_connection:
            Documented attribute exposed by this type.
    """

    project: SiteProject
    remote_connection: RemoteConnectionConfig | None

    @property
    def id(self) -> str:
        """Return the persisted project identifier.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.id

    @property
    def name(self) -> str:
        """Return the project name.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.name

    @property
    def framework_type(self) -> str:
        """Return the project framework type.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.framework_type

    @property
    def local_path(self) -> str:
        """Return the local workspace path.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.local_path

    @property
    def default_locale(self) -> str:
        """Return the configured default locale.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.default_locale

    @property
    def compile_mo(self) -> bool:
        """Return whether MO compilation is enabled for this project.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.compile_mo

    @property
    def use_external_translator(self) -> bool:
        """Return whether external translation is enabled for this project.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.use_external_translator

    @property
    def dry_run(self) -> bool:
        """Return whether translation runs in dry-run mode for this project.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.dry_run

    @property
    def use_translation_cache(self) -> bool:
        """Return whether the translation cache is enabled for this project.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.use_translation_cache

    @property
    def only_fuzzy(self) -> bool:
        """Return whether translation should process only fuzzy entries.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.only_fuzzy

    @property
    def stats_only(self) -> bool:
        """Return whether translation runs in stats-only mode for this project.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.stats_only

    @property
    def report_inconsistencies(self) -> bool:
        """Return whether variant inconsistencies are reported for this project.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.report_inconsistencies

    @property
    def is_active(self) -> bool:
        """Return whether the project is active.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.project.is_active
