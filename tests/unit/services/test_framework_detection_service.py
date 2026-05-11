"""Unit tests for the framework detection application service."""

from __future__ import annotations

from pathlib import Path

import pytest

from polyglot_site_translator.adapters.django import DjangoFrameworkAdapter
from polyglot_site_translator.adapters.flask import FlaskFrameworkAdapter
from polyglot_site_translator.adapters.framework_registry import (
    FrameworkAdapterRegistry,
)
from polyglot_site_translator.adapters.wordpress import WordPressFrameworkAdapter
from polyglot_site_translator.domain.framework_detection.errors import (
    FrameworkDetectionError,
)
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDescriptor,
)
from polyglot_site_translator.services.framework_detection import (
    FrameworkDetectionService,
)


def test_framework_detection_service_detects_supported_frameworks(
    tmp_path: Path,
) -> None:
    """Verify framework detection service detects supported frameworks.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    wordpress_path = tmp_path / "wordpress-site"
    wordpress_path.mkdir()
    (wordpress_path / "wp-config.php").write_text("<?php\n", encoding="utf-8")
    (wordpress_path / "wp-content").mkdir()
    (wordpress_path / "wp-includes").mkdir()

    service = FrameworkDetectionService(
        registry=FrameworkAdapterRegistry.default_registry(
            adapters=[
                WordPressFrameworkAdapter(),
                DjangoFrameworkAdapter(),
                FlaskFrameworkAdapter(),
            ]
        )
    )

    result = service.detect_project(wordpress_path)

    assert result.framework_type == "wordpress"
    assert result.matched is True


def test_framework_detection_service_returns_unmatched_for_missing_paths(
    tmp_path: Path,
) -> None:
    """Verify framework detection service returns unmatched for missing paths.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = FrameworkDetectionService(
        registry=FrameworkAdapterRegistry.default_registry(
            adapters=[
                WordPressFrameworkAdapter(),
                DjangoFrameworkAdapter(),
                FlaskFrameworkAdapter(),
            ]
        )
    )

    result = service.detect_project(tmp_path / "missing-project")

    assert result.matched is False
    assert any("does not exist" in warning for warning in result.warnings)


def test_framework_detection_service_returns_unmatched_for_non_directory_paths(
    tmp_path: Path,
) -> None:
    """Verify framework detection service returns unmatched for non directory paths.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    project_file = tmp_path / "project.txt"
    project_file.write_text("hello\n", encoding="utf-8")
    service = FrameworkDetectionService(
        registry=FrameworkAdapterRegistry.default_registry(
            adapters=[
                WordPressFrameworkAdapter(),
                DjangoFrameworkAdapter(),
                FlaskFrameworkAdapter(),
            ]
        )
    )

    result = service.detect_project(project_file)

    assert result.matched is False
    assert any("not a directory" in warning for warning in result.warnings)


def test_framework_detection_service_lists_supported_frameworks() -> None:
    """Verify framework detection service lists supported frameworks.

    Returns:
        value:
            Structured value returned by this callable.
    """
    service = FrameworkDetectionService(
        registry=FrameworkAdapterRegistry.discover_installed()
    )

    assert service.list_supported_frameworks() == [
        FrameworkDescriptor(
            framework_type="unknown",
            adapter_name="unresolved",
            display_name="Unknown",
        ),
        FrameworkDescriptor(
            framework_type="django",
            adapter_name="django_adapter",
            display_name="Django",
        ),
        FrameworkDescriptor(
            framework_type="flask",
            adapter_name="flask_adapter",
            display_name="Flask",
        ),
        FrameworkDescriptor(
            framework_type="wordpress",
            adapter_name="wordpress_adapter",
            display_name="WordPress",
        ),
    ]


def test_framework_detection_service_wraps_registry_runtime_failures(
    tmp_path: Path,
) -> None:
    """Verify framework detection service wraps registry runtime failures.

    Args:
        tmp_path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.

    Raises:
        OSError:
            Raised when this callable hits the corresponding error path.
        RuntimeError:
            Raised when this callable hits the corresponding error path.
    """

    class _FailingRegistry:
        """Test helper for FailingRegistry.

        Attributes:
            None: This type does not declare class-level attributes.
        """

        @staticmethod
        def resolve(_project_path: Path) -> object:
            """Handle resolve.

            Args:
                _project_path:
                    Value supplied to this callable.

            Returns:
                value:
                    Structured value returned by this callable.

            Raises:
                OSError:
                    Raised when this callable hits the corresponding error path.
            """
            msg = "broken adapter registry"
            raise OSError(msg)

        @staticmethod
        def list_framework_descriptors() -> list[FrameworkDescriptor]:
            """Handle list framework descriptors.

            Returns:
                value:
                    Structured value returned by this callable.

            Raises:
                RuntimeError:
                    Raised when this callable hits the corresponding error path.
            """
            msg = "broken adapter registry"
            raise RuntimeError(msg)

    service = FrameworkDetectionService(registry=_FailingRegistry())  # type: ignore[arg-type]

    with pytest.raises(
        FrameworkDetectionError,
        match=r"Framework detection failed while inspecting project path",
    ):
        service.detect_project(tmp_path)

    with pytest.raises(
        FrameworkDetectionError,
        match=r"Framework descriptor discovery failed",
    ):
        service.list_supported_frameworks()
