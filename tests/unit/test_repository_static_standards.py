"""Static regression tests for repository coding standards."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
NON_PYTEST_ASSERTION_ROOTS = (
    REPOSITORY_ROOT / "src",
    REPOSITORY_ROOT / "features",
)
KIVY_APP_PATH = (
    REPOSITORY_ROOT
    / "src"
    / "polyglot_site_translator"
    / "presentation"
    / "kivy"
    / "app.py"
)


def _python_files(paths: Iterable[Path]) -> list[Path]:
    """Collect Python files under the supplied repository paths.

    Args:
        paths:
            Repository paths that should be searched recursively.

    Returns:
        value:
            Sorted Python source files below the supplied paths.
    """
    files: list[Path] = []
    for path in paths:
        files.extend(sorted(path.rglob("*.py")))
    return sorted(files)


def _self_attribute_names(target: ast.expr) -> set[str]:
    """Extract instance attribute names assigned through ``self``.

    Args:
        target:
            Assignment target found in a class method body.

    Returns:
        value:
            Attribute names introduced or updated through ``self``.
    """
    if (
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == "self"
    ):
        return {target.attr}
    if isinstance(target, ast.Tuple | ast.List):
        names: set[str] = set()
        for item in target.elts:
            names.update(_self_attribute_names(item))
        return names
    return set()


def _assigned_self_attributes(function: ast.FunctionDef) -> set[str]:
    """Collect ``self`` attributes assigned inside a method.

    Args:
        function:
            Method AST node to inspect.

    Returns:
        value:
            Attribute names assigned by the method.
    """
    assigned: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                assigned.update(_self_attribute_names(target))
        if isinstance(node, ast.AnnAssign):
            assigned.update(_self_attribute_names(node.target))
        if isinstance(node, ast.AugAssign):
            assigned.update(_self_attribute_names(node.target))
    return assigned


def test_non_pytest_sources_do_not_use_assert_statements() -> None:
    """Reject optimized-away assertions outside pytest test modules.

    Returns:
        value:
            None. The pytest assertion reports any file and line that still
            contains a Python ``assert`` statement outside the test suite.
    """
    violations: list[str] = []
    for path in _python_files(NON_PYTEST_ASSERTION_ROOTS):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                relative_path = path.relative_to(REPOSITORY_ROOT)
                violations.append(f"{relative_path}:{node.lineno}")

    assert violations == []


def test_kivy_app_instance_attributes_are_introduced_in_init() -> None:
    """Ensure app instance attributes are declared by the constructor.

    Returns:
        value:
            None. The pytest assertion reports attributes first assigned by
            methods other than ``__init__``.
    """
    module = ast.parse(KIVY_APP_PATH.read_text(encoding="utf-8"))
    app_class = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "PolyglotSiteTranslatorApp"
    )
    methods = {
        node.name: node for node in app_class.body if isinstance(node, ast.FunctionDef)
    }
    initialized = _assigned_self_attributes(methods["__init__"])
    violations: list[str] = []

    for method_name, method in methods.items():
        if method_name == "__init__":
            continue
        for attribute in sorted(_assigned_self_attributes(method) - initialized):
            violations.append(f"{method_name}: self.{attribute}")

    assert violations == []
