"""Typed models for framework detection results."""

from __future__ import annotations

from dataclasses import dataclass

UNKNOWN_FRAMEWORK_TYPE = "unknown"


@dataclass(frozen=True)
class FrameworkDescriptor:
    """Selectable/displayable metadata for a supported framework.

    Attributes:
        framework_type (str): Documented attribute exposed by this type.
        adapter_name (str): Documented attribute exposed by this type.
        display_name (str): Documented attribute exposed by this type.
    """

    framework_type: str
    adapter_name: str
    display_name: str


def unknown_framework_descriptor() -> FrameworkDescriptor:
    """Return the stable descriptor for unresolved framework selection.

    Returns:
        FrameworkDescriptor: Structured value returned by this callable.
    """
    return FrameworkDescriptor(
        framework_type=UNKNOWN_FRAMEWORK_TYPE,
        adapter_name="unresolved",
        display_name="Unknown",
    )


@dataclass(frozen=True)
class FrameworkDetectionResult:
    """Structured framework detection output.

    Attributes:
        framework_type (str): Documented attribute exposed by this type.
        adapter_name (str): Documented attribute exposed by this type.
        matched (bool): Documented attribute exposed by this type.
        confidence (int): Documented attribute exposed by this type.
        evidence (list[str]): Documented attribute exposed by this type.
        relevant_paths (list[str]): Documented attribute exposed by this type.
        config_files (list[str]): Documented attribute exposed by this type.
        warnings (list[str]): Documented attribute exposed by this type.
    """

    framework_type: str
    adapter_name: str
    matched: bool
    confidence: int
    evidence: list[str]
    relevant_paths: list[str]
    config_files: list[str]
    warnings: list[str]

    @classmethod
    def unmatched(
        cls,
        *,
        project_path: str,
        warnings: list[str] | None = None,
    ) -> FrameworkDetectionResult:
        """Build an unmatched detection result with a stable shape.

        Args:
            project_path (str): Value supplied to this callable.
            warnings (list[str] | None): Value supplied to this callable.

        Returns:
            FrameworkDetectionResult: Structured value returned by this callable.
        """
        return cls(
            framework_type=UNKNOWN_FRAMEWORK_TYPE,
            adapter_name="unresolved",
            matched=False,
            confidence=0,
            evidence=[],
            relevant_paths=[project_path],
            config_files=[],
            warnings=list(warnings or []),
        )
