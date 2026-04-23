"""Domain errors for PO processing workflows."""

from __future__ import annotations


class POProcessingError(Exception):
    """Base error for PO processing workflows."""


class POProcessingInfrastructureError(POProcessingError):
    """Raised when PO files cannot be loaded or saved from infrastructure."""


class POProcessingTranslationError(POProcessingError):
    """Raised when an external translation provider fails."""


class POTranslationProviderTransportError(POProcessingTranslationError):
    """Raised when an external translation transport/protocol call fails."""


class POTranslationProviderResponseError(POProcessingTranslationError):
    """Raised when an external translation provider returns an invalid response."""


class POTranslationProviderConfigurationError(POProcessingTranslationError):
    """Raised when an external translation provider is not correctly configured."""
