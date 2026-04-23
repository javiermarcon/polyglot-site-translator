"""Application service for framework detection."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.domain.framework_detection.errors import (
    FrameworkDetectionError,
)
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDescriptor,
    FrameworkDetectionResult,
)


class FrameworkDetectionService:
    """Orchestrate adapter registry resolution for project paths."""

    def __init__(self, *, registry: FrameworkAdapterRegistry) -> None:
        self._registry = registry

    def detect_project(self, project_path: Path | str) -> FrameworkDetectionResult:
        """Return the best framework detection result for a local project path."""
        resolved_path = Path(project_path)
        try:
            if not resolved_path.exists():
                return FrameworkDetectionResult.unmatched(
                    project_path=str(resolved_path),
                    warnings=[f"Project path does not exist: {resolved_path}."],
                )
            if not resolved_path.is_dir():
                return FrameworkDetectionResult.unmatched(
                    project_path=str(resolved_path),
                    warnings=[f"Project path is not a directory: {resolved_path}."],
                )
            return self._registry.resolve(resolved_path)
        except (LookupError, OSError, RuntimeError, ValueError) as error:
            msg = (
                f"Framework detection failed while inspecting project path "
                f"'{resolved_path}'. Cause: {error}"
            )
            raise FrameworkDetectionError(msg) from error

    def list_supported_frameworks(self) -> list[FrameworkDescriptor]:
        """Return framework metadata suitable for selectors and labels."""
        try:
            return self._registry.list_framework_descriptors()
        except (LookupError, OSError, RuntimeError, ValueError) as error:
            msg = f"Framework descriptor discovery failed. Cause: {error}"
            raise FrameworkDetectionError(msg) from error
