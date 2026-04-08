"""Domain errors for framework detection."""

from __future__ import annotations


class FrameworkDetectionError(ValueError):
    """Base error for framework detection workflows."""


class FrameworkDetectionAmbiguityError(FrameworkDetectionError):
    """Raised when multiple adapters match with the same top confidence."""
