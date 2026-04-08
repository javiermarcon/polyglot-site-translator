"""Registry for framework adapters."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import inspect
from pathlib import Path
import pkgutil

from polyglot_site_translator.adapters import __path__ as adapters_package_path
from polyglot_site_translator.adapters.base import BaseFrameworkAdapter
from polyglot_site_translator.domain.framework_detection.contracts import (
    FrameworkAdapter,
)
from polyglot_site_translator.domain.framework_detection.errors import (
    FrameworkDetectionAmbiguityError,
)
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDescriptor,
    FrameworkDetectionResult,
    unknown_framework_descriptor,
)


@dataclass(frozen=True)
class FrameworkAdapterRegistry:
    """Resolve framework adapters against a project path."""

    adapters: list[FrameworkAdapter]

    @classmethod
    def default_registry(
        cls,
        *,
        adapters: list[FrameworkAdapter],
    ) -> FrameworkAdapterRegistry:
        """Build the default registry with an explicit ordered adapter list."""
        return cls(adapters=list(adapters))

    @classmethod
    def discover_installed(cls) -> FrameworkAdapterRegistry:
        """Discover installed framework adapters dynamically from the adapters package."""
        adapters: list[FrameworkAdapter] = []
        for module_info in pkgutil.iter_modules(adapters_package_path):
            if module_info.name in {"base", "common", "framework_registry"}:
                continue
            module = importlib.import_module(
                f"polyglot_site_translator.adapters.{module_info.name}"
            )
            for _, adapter_class in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(adapter_class, BaseFrameworkAdapter)
                    and adapter_class is not BaseFrameworkAdapter
                    and adapter_class.__module__ == module.__name__
                ):
                    adapters.append(adapter_class())
        adapters.sort(key=lambda adapter: adapter.framework_type)
        return cls(adapters=adapters)

    def iter_adapters(self) -> list[FrameworkAdapter]:
        """Return registered adapters preserving registration order."""
        return list(self.adapters)

    def list_framework_descriptors(self) -> list[FrameworkDescriptor]:
        """Return display metadata for the unknown option and all discovered adapters."""
        descriptors = [
            FrameworkDescriptor(
                framework_type=adapter.framework_type,
                adapter_name=adapter.adapter_name,
                display_name=adapter.display_name,
            )
            for adapter in self.adapters
        ]
        return [unknown_framework_descriptor(), *descriptors]

    def resolve(self, project_path: Path) -> FrameworkDetectionResult:
        """Return the best framework match for the given project path."""
        matched_results: list[FrameworkDetectionResult] = []
        warnings: list[str] = []
        for adapter in self.adapters:
            result = adapter.detect(project_path)
            if result.matched:
                matched_results.append(result)
            else:
                warnings.extend(result.warnings)
        if not matched_results:
            return FrameworkDetectionResult.unmatched(
                project_path=str(project_path),
                warnings=warnings,
            )
        matched_results.sort(key=lambda result: result.confidence, reverse=True)
        top_result = matched_results[0]
        top_matches = [
            result for result in matched_results if result.confidence == top_result.confidence
        ]
        if len(top_matches) > 1:
            adapter_names = ", ".join(result.adapter_name for result in top_matches)
            msg = (
                "Multiple framework adapters matched the project path with the same "
                f"confidence: {adapter_names}."
            )
            raise FrameworkDetectionAmbiguityError(msg)
        return top_result
