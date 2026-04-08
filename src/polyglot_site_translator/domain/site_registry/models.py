"""Typed domain models for the site registry subsystem."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SiteRegistrationInput:
    """Validated input payload for create/update site registry workflows."""

    name: str
    framework_type: str
    local_path: str
    default_locale: str
    ftp_host: str
    ftp_port: int
    ftp_username: str
    ftp_password: str
    ftp_remote_path: str
    is_active: bool


@dataclass(frozen=True)
class RegisteredSite:
    """A site or project persisted in the local site registry."""

    id: str
    name: str
    framework_type: str
    local_path: str
    default_locale: str
    ftp_host: str
    ftp_port: int
    ftp_username: str
    ftp_password: str
    ftp_remote_path: str
    is_active: bool
