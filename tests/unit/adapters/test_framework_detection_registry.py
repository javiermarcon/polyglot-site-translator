"""Unit tests for framework adapter contracts, models, and registry behavior."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from polyglot_site_translator.adapters.framework_registry import (
    FrameworkAdapterRegistry,
)
from polyglot_site_translator.domain.framework_detection.errors import (
    FrameworkDetectionAmbiguityError,
)
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDescriptor,
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.sync.scope import AdapterSyncScope, SyncFilterSpec


@dataclass(frozen=True)
class FakeAdapter:
    """Test helper for FakeAdapter.

    Attributes:
        framework_type:
            Documented attribute exposed by this type.
        adapter_name:
            Documented attribute exposed by this type.
        display_name:
            Documented attribute exposed by this type.
        result:
            Documented attribute exposed by this type.
    """

    framework_type: str
    adapter_name: str
    display_name: str
    result: FrameworkDetectionResult

    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        """Handle detect.

        Args:
            self:
                Value supplied to this callable.
            project_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return self.result

    @staticmethod
    def get_sync_filters(project_path: Path) -> tuple[SyncFilterSpec, ...]:
        """Handle get sync filters.

        Args:
            project_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return ()

    @staticmethod
    def get_sync_scope(project_path: Path) -> AdapterSyncScope:
        """Handle get sync scope.

        Args:
            project_path:
                Value supplied to this callable.

        Returns:
            value:
                Structured value returned by this callable.
        """
        return AdapterSyncScope()


def test_framework_detection_result_unmatched_factory_preserves_warnings() -> None:
    """Verify framework detection result unmatched factory preserves warnings.

    Returns:
        value:
            Structured value returned by this callable.
    """
    result = FrameworkDetectionResult.unmatched(
        project_path="/workspace/unknown-project",
        warnings=["No supported framework markers were detected."],
    )

    assert result.matched is False
    assert result.framework_type == "unknown"
    assert result.adapter_name == "unresolved"
    assert result.warnings == ["No supported framework markers were detected."]


def test_framework_adapter_registry_iterates_registered_adapters_in_order() -> None:
    """Verify framework adapter registry iterates registered adapters in order.

    Returns:
        value:
            Structured value returned by this callable.
    """
    first = FakeAdapter(
        framework_type="wordpress",
        adapter_name="wordpress_adapter",
        display_name="WordPress",
        result=FrameworkDetectionResult.unmatched(project_path="/workspace/site"),
    )
    second = FakeAdapter(
        framework_type="django",
        adapter_name="django_adapter",
        display_name="Django",
        result=FrameworkDetectionResult.unmatched(project_path="/workspace/site"),
    )
    registry = FrameworkAdapterRegistry(adapters=[first, second])

    assert [adapter.adapter_name for adapter in registry.iter_adapters()] == [
        "wordpress_adapter",
        "django_adapter",
    ]


def test_framewor_adapter_registry_returns_unmatche_re_deae() -> None:
    """Verify framework adapter registry returns unmatched result when no adapter.

    applies.

    Returns:
        value:
            Structured value returned by this callable.
    """
    registry = FrameworkAdapterRegistry(
        adapters=[
            FakeAdapter(
                framework_type="wordpress",
                adapter_name="wordpress_adapter",
                display_name="WordPress",
                result=FrameworkDetectionResult.unmatched(
                    project_path="/workspace/site"
                ),
            )
        ]
    )

    result = registry.resolve(Path("/workspace/site"))

    assert result.matched is False
    assert result.framework_type == "unknown"


def test_framework_adapter_registry_returns_the_highest_confidence_match() -> None:
    """Verify framework adapter registry returns the highest confidence match.

    Returns:
        value:
            Structured value returned by this callable.
    """
    registry = FrameworkAdapterRegistry(
        adapters=[
            FakeAdapter(
                framework_type="flask",
                adapter_name="flask_adapter",
                display_name="Flask",
                result=FrameworkDetectionResult(
                    framework_type="flask",
                    adapter_name="flask_adapter",
                    matched=True,
                    confidence=70,
                    evidence=["app.py contains Flask app markers."],
                    relevant_paths=["/workspace/site/app.py"],
                    config_files=[],
                    warnings=[],
                ),
            ),
            FakeAdapter(
                framework_type="django",
                adapter_name="django_adapter",
                display_name="Django",
                result=FrameworkDetectionResult(
                    framework_type="django",
                    adapter_name="django_adapter",
                    matched=True,
                    confidence=95,
                    evidence=["manage.py and settings.py were found."],
                    relevant_paths=["/workspace/site/manage.py"],
                    config_files=["/workspace/site/project/settings.py"],
                    warnings=[],
                ),
            ),
        ]
    )

    result = registry.resolve(Path("/workspace/site"))

    assert result.framework_type == "django"
    assert result.adapter_name == "django_adapter"


def test_framework_adapter_registry_raises_for_ambiguous_top_matches() -> None:
    """Verify framework adapter registry raises for ambiguous top matches.

    Returns:
        value:
            Structured value returned by this callable.
    """
    registry = FrameworkAdapterRegistry(
        adapters=[
            FakeAdapter(
                framework_type="django",
                adapter_name="django_adapter",
                display_name="Django",
                result=FrameworkDetectionResult(
                    framework_type="django",
                    adapter_name="django_adapter",
                    matched=True,
                    confidence=90,
                    evidence=["manage.py and settings.py were found."],
                    relevant_paths=["/workspace/site/manage.py"],
                    config_files=["/workspace/site/project/settings.py"],
                    warnings=[],
                ),
            ),
            FakeAdapter(
                framework_type="flask",
                adapter_name="flask_adapter",
                display_name="Flask",
                result=FrameworkDetectionResult(
                    framework_type="flask",
                    adapter_name="flask_adapter",
                    matched=True,
                    confidence=90,
                    evidence=["app.py and translations were found."],
                    relevant_paths=["/workspace/site/app.py"],
                    config_files=[],
                    warnings=[],
                ),
            ),
        ]
    )

    with pytest.raises(
        FrameworkDetectionAmbiguityError,
        match=r"Multiple framework adapters matched the project path",
    ):
        registry.resolve(Path("/workspace/site"))


def test_framework_adapter_registry_can_discover_installed_adapters() -> None:
    """Verify framework adapter registry can discover installed adapters.

    Returns:
        value:
            Structured value returned by this callable.
    """
    registry = FrameworkAdapterRegistry.discover_installed()

    assert [adapter.framework_type for adapter in registry.iter_adapters()] == [
        "django",
        "flask",
        "wordpress",
    ]


def test_framework_adapter_registry_exposes_framework_descriptors() -> None:
    """Verify framework adapter registry exposes framework descriptors.

    Returns:
        value:
            Structured value returned by this callable.
    """
    registry = FrameworkAdapterRegistry.discover_installed()

    assert registry.list_framework_descriptors() == [
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
