"""Unit tests for framework adapter contracts, models, and registry behavior."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
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
    """Small fake adapter for registry tests."""

    framework_type: str
    adapter_name: str
    display_name: str
    result: FrameworkDetectionResult

    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        return self.result

    def get_sync_filters(self, project_path: Path) -> tuple[SyncFilterSpec, ...]:
        return ()

    def get_sync_scope(self, project_path: Path) -> AdapterSyncScope:
        return AdapterSyncScope()


def test_framework_detection_result_unmatched_factory_preserves_warnings() -> None:
    result = FrameworkDetectionResult.unmatched(
        project_path="/workspace/unknown-project",
        warnings=["No supported framework markers were detected."],
    )

    assert result.matched is False
    assert result.framework_type == "unknown"
    assert result.adapter_name == "unresolved"
    assert result.warnings == ["No supported framework markers were detected."]


def test_framework_adapter_registry_iterates_registered_adapters_in_order() -> None:
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


def test_framework_adapter_registry_returns_unmatched_result_when_no_adapter_applies() -> None:
    registry = FrameworkAdapterRegistry(
        adapters=[
            FakeAdapter(
                framework_type="wordpress",
                adapter_name="wordpress_adapter",
                display_name="WordPress",
                result=FrameworkDetectionResult.unmatched(project_path="/workspace/site"),
            )
        ]
    )

    result = registry.resolve(Path("/workspace/site"))

    assert result.matched is False
    assert result.framework_type == "unknown"


def test_framework_adapter_registry_returns_the_highest_confidence_match() -> None:
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
    registry = FrameworkAdapterRegistry.discover_installed()

    assert [adapter.framework_type for adapter in registry.iter_adapters()] == [
        "django",
        "flask",
        "wordpress",
    ]


def test_framework_adapter_registry_exposes_framework_descriptors() -> None:
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
