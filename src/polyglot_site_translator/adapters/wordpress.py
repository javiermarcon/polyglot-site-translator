"""WordPress framework adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from polyglot_site_translator.adapters.base import BaseFrameworkAdapter
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScope,
    SyncFilterSpec,
    SyncFilterType,
)


@dataclass(frozen=True)
class WordPressFrameworkAdapter(BaseFrameworkAdapter):
    """Detect WordPress project layouts."""

    framework_type: str = "wordpress"
    adapter_name: str = "wordpress_adapter"
    display_name: str = "WordPress"

    def get_sync_scope(self, project_path: Path) -> AdapterSyncScope:
        """Return the default WordPress sync scope."""
        return AdapterSyncScope(
            filters=(
                SyncFilterSpec(
                    relative_path="wp-content/languages",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="WordPress translation catalogs.",
                ),
                SyncFilterSpec(
                    relative_path="wp-content/themes",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="WordPress theme sources and language assets.",
                ),
                SyncFilterSpec(
                    relative_path="wp-content/plugins",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="WordPress plugin sources and language assets.",
                ),
            ),
        )

    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        """Inspect a local path for WordPress markers."""
        wp_config = project_path / "wp-config.php"
        wp_content = project_path / "wp-content"
        wp_includes = project_path / "wp-includes"
        wp_admin = project_path / "wp-admin"

        evidence: list[str] = []
        relevant_paths: list[str] = [str(project_path)]
        config_files: list[str] = []
        warnings: list[str] = []
        confidence = 0

        if wp_config.is_file():
            evidence.append("wp-config.php is present at the project root.")
            relevant_paths.append(str(wp_config))
            config_files.append(str(wp_config))
            confidence += 50
        if wp_content.is_dir():
            evidence.append("wp-content/ is present.")
            relevant_paths.append(str(wp_content))
            confidence += 25
        if wp_includes.is_dir():
            evidence.append("wp-includes/ is present.")
            relevant_paths.append(str(wp_includes))
            confidence += 25
        if wp_admin.is_dir():
            evidence.append("wp-admin/ is present.")
            relevant_paths.append(str(wp_admin))
            confidence += 10

        if wp_config.is_file() or (wp_content.is_dir() and wp_includes.is_dir()):
            return FrameworkDetectionResult(
                framework_type=self.framework_type,
                adapter_name=self.adapter_name,
                matched=True,
                confidence=min(confidence, 100),
                evidence=evidence,
                relevant_paths=relevant_paths,
                config_files=config_files,
                warnings=[],
            )

        if evidence:
            warnings.append(
                "Partial WordPress evidence was found, but the layout is insufficient "
                "to confirm the framework."
            )
        return FrameworkDetectionResult.unmatched(
            project_path=str(project_path),
            warnings=warnings,
        )
