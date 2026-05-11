"""Domain errors for framework detection."""

from __future__ import annotations


class FrameworkDetectionError(ValueError):
    """Base error for framework detection workflows.

    Attributes:
        None: This type does not declare class-level attributes.
    """


class FrameworkDetectionAmbiguityError(FrameworkDetectionError):
    """Raised when multiple adapters match with the same top confidence.

    Attributes:
        None: This type does not declare class-level attributes.
    """
