"""Contracts for framework adapters and registry resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.sync.scope import SyncFilterSpec


class FrameworkAdapter(Protocol):
    """Adapter contract for framework-specific detection."""

    @property
    def framework_type(self) -> str:
        """Return the framework type handled by the adapter."""

    @property
    def adapter_name(self) -> str:
        """Return the adapter identifier."""

    @property
    def display_name(self) -> str:
        """Return the adapter label suitable for operator-facing UIs."""

    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        """Inspect a path and return a structured detection result."""

    def get_sync_filters(self, project_path: Path) -> tuple[SyncFilterSpec, ...]:
        """Return adapter-defined sync filters for the given project path."""
