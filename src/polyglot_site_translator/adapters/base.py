"""Base class for discoverable framework adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.sync.scope import SyncFilterSpec


class BaseFrameworkAdapter(ABC):
    """Abstract discoverable framework adapter."""

    framework_type: str
    adapter_name: str
    display_name: str

    @abstractmethod
    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        """Inspect a path and return a structured detection result."""

    def get_sync_filters(self, project_path: Path) -> tuple[SyncFilterSpec, ...]:
        """Return adapter-defined sync filters for the given project path."""
        return ()
