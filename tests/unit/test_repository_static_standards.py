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
SITE_REGISTRY_STEPS_PATH = (
    REPOSITORY_ROOT / "features" / "steps" / ("site_registry_steps.py")
)
SYNC_STEPS_PATH = REPOSITORY_ROOT / "features" / "steps" / "sync_steps.py"
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


def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef:
    """Find a named class in a parsed module.

    Args:
        module:
            Parsed Python module to inspect.
        class_name:
            Name of the class to find.

    Returns:
        value:
            Matching class definition.

    Raises:
        AssertionError:
            Raised when the expected class is absent from the module.
    """
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    message = f"Class not found: {class_name}"
    raise AssertionError(message)


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


def test_non_pytest_sources_do_not_use_global_statements() -> None:
    """Reject mutable module-level rebinding through ``global`` statements.

    Returns:
        value:
            None. The pytest assertion reports any source location that still
            uses a Python ``global`` statement outside the test suite.
    """
    violations: list[str] = []
    for path in _python_files(NON_PYTEST_ASSERTION_ROOTS):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                relative_path = path.relative_to(REPOSITORY_ROOT)
                violations.append(f"{relative_path}:{node.lineno}")

    assert violations == []


def test_site_registry_steps_do_not_hardcode_tmp_paths() -> None:
    """Ensure site registry BDD steps use tempfile-managed paths.

    Returns:
        value:
            None. The pytest assertion reports hardcoded temporary paths.
    """
    source = SITE_REGISTRY_STEPS_PATH.read_text(encoding="utf-8")

    assert "/tmp" not in source


def test_sync_steps_use_public_progress_popup_api() -> None:
    """Ensure sync BDD steps avoid protected Kivy popup internals.

    Returns:
        value:
            None. The pytest assertion reports direct protected popup access.
    """
    source = SYNC_STEPS_PATH.read_text(encoding="utf-8")

    assert "_sync_progress_popup" not in source
    assert "_command_log_label" not in source
    assert "_status_label" not in source
    assert "_message_label" not in source
    assert "_trust_host_key_button" not in source


def test_kivy_app_instance_attributes_are_introduced_in_init() -> None:
    """Ensure app instance attributes are declared by the constructor.

    Returns:
        value:
            None. The pytest assertion reports attributes first assigned by
            methods other than ``__init__``.
    """
    module = ast.parse(KIVY_APP_PATH.read_text(encoding="utf-8"))
    app_class = _find_class(module, "PolyglotSiteTranslatorApp")
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
