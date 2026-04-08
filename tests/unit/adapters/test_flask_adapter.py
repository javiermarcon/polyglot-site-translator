"""Unit tests for the Flask framework adapter."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.adapters.flask import FlaskFrameworkAdapter


def test_flask_adapter_detects_a_typical_flask_layout(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        "from flask import Flask\napp = Flask(__name__)\n",
        encoding="utf-8",
    )
    (tmp_path / "babel.cfg").write_text("[python: **.py]\n", encoding="utf-8")
    (tmp_path / "translations").mkdir()

    result = FlaskFrameworkAdapter().detect(tmp_path)

    assert result.matched is True
    assert result.framework_type == "flask"
    assert str(tmp_path / "babel.cfg") in result.config_files
    assert any("Flask" in evidence for evidence in result.evidence)


def test_flask_adapter_detects_factory_style_wsgi_projects(tmp_path: Path) -> None:
    (tmp_path / "wsgi.py").write_text(
        "from app import create_app\napplication = create_app()\n",
        encoding="utf-8",
    )
    package_dir = tmp_path / "app"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "from flask import Flask\n\ndef create_app():\n    return Flask(__name__)\n",
        encoding="utf-8",
    )
    (tmp_path / "translations").mkdir()

    result = FlaskFrameworkAdapter().detect(tmp_path)

    assert result.matched is True
    assert result.framework_type == "flask"


def test_flask_adapter_returns_unmatched_when_signals_are_insufficient(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")

    result = FlaskFrameworkAdapter().detect(tmp_path)

    assert result.matched is False
    assert result.warnings != []
