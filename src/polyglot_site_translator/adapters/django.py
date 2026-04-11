"""Django framework adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from polyglot_site_translator.adapters.base import BaseFrameworkAdapter
from polyglot_site_translator.adapters.common import (
    find_first_level_directory,
    find_first_level_file,
)
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.sync.scope import (
    SyncFilterSpec,
    SyncFilterType,
)


@dataclass(frozen=True)
class DjangoFrameworkAdapter(BaseFrameworkAdapter):
    """Detect Django project layouts."""

    framework_type: str = "django"
    adapter_name: str = "django_adapter"
    display_name: str = "Django"

    def get_sync_filters(self, project_path: Path) -> tuple[SyncFilterSpec, ...]:
        """Return the default Django sync scope."""
        return (
            SyncFilterSpec(
                relative_path="locale",
                filter_type=SyncFilterType.DIRECTORY,
                description="Django locale catalogs.",
            ),
        )

    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        """Inspect a local path for Django markers."""
        manage_py = project_path / "manage.py"
        settings_py = find_first_level_file(project_path, "settings.py")
        wsgi_py = find_first_level_file(project_path, "wsgi.py")
        asgi_py = find_first_level_file(project_path, "asgi.py")
        locale_dir = find_first_level_directory(project_path, "locale")

        evidence: list[str] = []
        relevant_paths: list[str] = [str(project_path)]
        config_files: list[str] = []
        warnings: list[str] = []
        confidence = 0

        if manage_py.is_file():
            evidence.append("manage.py is present at the project root.")
            relevant_paths.append(str(manage_py))
            confidence += 45
        if settings_py is not None:
            evidence.append("settings.py was found in the Django configuration package.")
            relevant_paths.append(str(settings_py))
            config_files.append(str(settings_py))
            confidence += 35
        if wsgi_py is not None:
            evidence.append("wsgi.py was found in the Django configuration package.")
            relevant_paths.append(str(wsgi_py))
            config_files.append(str(wsgi_py))
            confidence += 10
        if asgi_py is not None:
            evidence.append("asgi.py was found in the Django configuration package.")
            relevant_paths.append(str(asgi_py))
            config_files.append(str(asgi_py))
            confidence += 10
        if locale_dir is not None:
            evidence.append("locale/ directory is present.")
            relevant_paths.append(str(locale_dir))
            confidence += 5

        if manage_py.is_file() and (
            settings_py is not None or wsgi_py is not None or asgi_py is not None
        ):
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
                "Partial Django evidence was found, but manage.py and a settings entrypoint "
                "were not both available."
            )
        return FrameworkDetectionResult.unmatched(
            project_path=str(project_path),
            warnings=warnings,
        )
