"""Domain errors for PO processing workflows."""

from __future__ import annotations


class POProcessingError(Exception):
    """Base error for PO processing workflows.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """


class POProcessingInfrastructureError(POProcessingError):
    """Raised when PO files cannot be loaded or saved from infrastructure.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """


class POProcessingCompilationError(POProcessingInfrastructureError):
    """Raised when one PO file cannot be compiled into a MO catalog.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """


class POProcessingCacheError(POProcessingInfrastructureError):
    """Raised when the translation cache cannot be loaded or updated.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """


class POProcessingTranslationError(POProcessingError):
    """Raised when an external translation provider fails.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """


class POTranslationProviderTransportError(POProcessingTranslationError):
    """Raised when an external translation transport/protocol call fails.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """


class POTranslationProviderResponseError(POProcessingTranslationError):
    """Raised when an external translation provider returns an invalid response.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """


class POTranslationProviderConfigurationError(POProcessingTranslationError):
    """Raised when an external translation provider is not correctly configured.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """
