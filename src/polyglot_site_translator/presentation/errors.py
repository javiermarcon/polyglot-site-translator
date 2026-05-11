"""Explicit presentation-layer errors."""

from __future__ import annotations


class ControlledServiceError(RuntimeError):
    """Known operational error surfaced to the presentation layer.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """
