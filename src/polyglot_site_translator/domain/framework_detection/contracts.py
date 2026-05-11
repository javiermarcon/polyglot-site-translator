"""Contracts for framework adapters and registry resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.sync.scope import AdapterSyncScope, SyncFilterSpec


class FrameworkAdapter(Protocol):
    """Adapter contract for framework-specific detection.

    Attributes:
        None: This type does not declare class-level attributes.
    """

    @property
    def framework_type(self) -> str:
        """Return the framework type handled by the adapter.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    @property
    def adapter_name(self) -> str:
        """Return the adapter identifier.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    @property
    def display_name(self) -> str:
        """Return the adapter label suitable for operator-facing UIs.

        Args:
            self:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        """Inspect a path and return a structured detection result.

        Args:
            self:
                Value supplied to this callable.
            project_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def get_sync_filters(self, project_path: Path) -> tuple[SyncFilterSpec, ...]:
        """Return adapter-defined sync filters for the given project path.

        Args:
            self:
                Value supplied to this callable.
            project_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """

    def get_sync_scope(self, project_path: Path) -> AdapterSyncScope:
        """Return adapter-defined include/exclude sync rules for the given project path.

        Args:
            self:
                Value supplied to this callable.
            project_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
