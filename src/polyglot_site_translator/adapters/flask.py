"""Flask framework adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from polyglot_site_translator.adapters.base import BaseFrameworkAdapter
from polyglot_site_translator.adapters.common import read_text_if_present
from polyglot_site_translator.domain.framework_detection.models import (
    FrameworkDetectionResult,
)
from polyglot_site_translator.domain.sync.scope import (
    AdapterSyncScope,
    SyncFilterSpec,
    SyncFilterType,
)

FLASK_MATCH_THRESHOLD = 55


def _contains_flask_markers(content: str) -> bool:
    return "Flask(" in content or "from flask import Flask" in content or "create_app(" in content


@dataclass(frozen=True)
class FlaskFrameworkAdapter(BaseFrameworkAdapter):
    """Detect Flask project layouts."""

    framework_type: str = "flask"
    adapter_name: str = "flask_adapter"
    display_name: str = "Flask"

    def get_sync_scope(self, project_path: Path) -> AdapterSyncScope:
        """Return the default Flask sync scope."""
        return AdapterSyncScope(
            filters=(
                SyncFilterSpec(
                    relative_path="translations",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="Flask-Babel translation catalogs.",
                ),
                SyncFilterSpec(
                    relative_path="babel.cfg",
                    filter_type=SyncFilterType.FILE,
                    description="Flask-Babel extraction configuration.",
                ),
            ),
            excludes=(
                SyncFilterSpec(
                    relative_path=".venv",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="Project virtual environment.",
                ),
                SyncFilterSpec(
                    relative_path="venv",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="Project virtual environment.",
                ),
                SyncFilterSpec(
                    relative_path="__pycache__",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="Python bytecode cache.",
                ),
                SyncFilterSpec(
                    relative_path=".mypy_cache",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="mypy cache.",
                ),
                SyncFilterSpec(
                    relative_path=".pytest_cache",
                    filter_type=SyncFilterType.DIRECTORY,
                    description="pytest cache.",
                ),
            ),
        )

    def detect(self, project_path: Path) -> FrameworkDetectionResult:
        """Inspect a local path for Flask markers."""
        app_py = project_path / "app.py"
        wsgi_py = project_path / "wsgi.py"
        babel_cfg = project_path / "babel.cfg"
        translations_dir = project_path / "translations"
        app_package_init = project_path / "app" / "__init__.py"

        evidence: list[str] = []
        relevant_paths: list[str] = [str(project_path)]
        config_files: list[str] = []
        warnings: list[str] = []
        confidence = 0

        app_py_content = read_text_if_present(app_py)
        if _contains_flask_markers(app_py_content):
            evidence.append("app.py contains Flask application markers.")
            relevant_paths.append(str(app_py))
            confidence += 45

        wsgi_content = read_text_if_present(wsgi_py)
        if _contains_flask_markers(wsgi_content) or "create_app()" in wsgi_content:
            evidence.append("wsgi.py contains Flask application markers.")
            relevant_paths.append(str(wsgi_py))
            confidence += 20

        package_init_content = read_text_if_present(app_package_init)
        if _contains_flask_markers(package_init_content):
            evidence.append("app/__init__.py contains Flask factory markers.")
            relevant_paths.append(str(app_package_init))
            confidence += 35

        if babel_cfg.is_file():
            evidence.append("babel.cfg is present.")
            relevant_paths.append(str(babel_cfg))
            config_files.append(str(babel_cfg))
            confidence += 10
        if translations_dir.is_dir():
            evidence.append("translations/ directory is present.")
            relevant_paths.append(str(translations_dir))
            confidence += 10

        if confidence >= FLASK_MATCH_THRESHOLD:
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

        if evidence or app_py.is_file() or wsgi_py.is_file():
            warnings.append(
                "Partial Flask evidence was found, but the project layout is insufficient "
                "to confirm the framework."
            )
        return FrameworkDetectionResult.unmatched(
            project_path=str(project_path),
            warnings=warnings,
        )
