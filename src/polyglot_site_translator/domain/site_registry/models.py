"""Typed domain models for the site registry subsystem."""

from __future__ import annotations

from dataclasses import dataclass

from polyglot_site_translator.domain.remote_connections.models import (
    RemoteConnectionConfig,
    RemoteConnectionConfigInput,
)


@dataclass(frozen=True)
class SiteRegistrationInput:
    """Validated input payload for create/update site registry workflows."""

    name: str
    framework_type: str
    local_path: str
    default_locale: str
    remote_connection: RemoteConnectionConfigInput | None
    is_active: bool


@dataclass(frozen=True)
class SiteProject:
    """A site or project persisted in the local site registry."""

    id: str
    name: str
    framework_type: str
    local_path: str
    default_locale: str
    is_active: bool


@dataclass(frozen=True)
class RegisteredSite:
    """Aggregate of a persisted site project and its optional remote config."""

    project: SiteProject
    remote_connection: RemoteConnectionConfig | None

    @property
    def id(self) -> str:
        """Return the persisted project identifier."""
        return self.project.id

    @property
    def name(self) -> str:
        """Return the project name."""
        return self.project.name

    @property
    def framework_type(self) -> str:
        """Return the project framework type."""
        return self.project.framework_type

    @property
    def local_path(self) -> str:
        """Return the local workspace path."""
        return self.project.local_path

    @property
    def default_locale(self) -> str:
        """Return the configured default locale."""
        return self.project.default_locale

    @property
    def is_active(self) -> bool:
        """Return whether the project is active."""
        return self.project.is_active
