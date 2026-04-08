"""Unit tests for the Django framework adapter."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.adapters.django import DjangoFrameworkAdapter


def test_django_adapter_detects_a_typical_project_layout(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text(
        "import os\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')\n",
        encoding="utf-8",
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.py").write_text("INSTALLED_APPS = []\n", encoding="utf-8")
    (config_dir / "wsgi.py").write_text("application = object()\n", encoding="utf-8")
    (tmp_path / "locale").mkdir()

    result = DjangoFrameworkAdapter().detect(tmp_path)

    assert result.matched is True
    assert result.framework_type == "django"
    assert str(config_dir / "settings.py") in result.config_files
    assert any("manage.py" in evidence for evidence in result.evidence)


def test_django_adapter_supports_settings_module_inside_a_package(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text("print('manage')\n", encoding="utf-8")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "settings.py").write_text("DEBUG = True\n", encoding="utf-8")

    result = DjangoFrameworkAdapter().detect(tmp_path)

    assert result.matched is True
    assert result.framework_type == "django"


def test_django_adapter_supports_asgi_without_wsgi(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text("print('manage')\n", encoding="utf-8")
    project_dir = tmp_path / "config"
    project_dir.mkdir()
    (project_dir / "asgi.py").write_text("application = object()\n", encoding="utf-8")

    result = DjangoFrameworkAdapter().detect(tmp_path)

    assert result.matched is True
    assert any("asgi.py" in evidence for evidence in result.evidence)


def test_django_adapter_reports_partial_evidence_without_matching(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text("print('manage')\n", encoding="utf-8")

    result = DjangoFrameworkAdapter().detect(tmp_path)

    assert result.matched is False
    assert any("partial django evidence" in warning.lower() for warning in result.warnings)


def test_django_adapter_returns_unmatched_for_non_django_projects(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")

    result = DjangoFrameworkAdapter().detect(tmp_path)

    assert result.matched is False
    assert result.framework_type == "unknown"
