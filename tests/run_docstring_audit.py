"""Audit structured docstring coverage for the repository."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

ROOTS = (Path("src"), Path("tests"), Path("features/steps"))
SELF_NAMES = {"self", "cls"}
MAX_REPORTED_ERRORS = 200


@dataclass(frozen=True)
class AuditFailure:
    """Describe one docstring validation failure.

    Attributes:
        path:
            Documented attribute exposed by this type.
        lineno:
            Documented attribute exposed by this type.
        symbol_name:
            Documented attribute exposed by this type.
        message:
            Documented attribute exposed by this type.
    """

    path: str
    lineno: int
    symbol_name: str
    message: str


def main() -> int:
    """Run the repository-wide docstring audit and return an exit code.

    Returns:
        value:
            Structured value returned by this callable.
    """
    failures: list[AuditFailure] = []
    for root in ROOTS:
        failures.extend(_audit_root(root))
    if not failures:
        print("Docstring audit passed.")
        return 0
    for failure in failures[:MAX_REPORTED_ERRORS]:
        print(
            f"{failure.path}:{failure.lineno}: {failure.symbol_name}: "
            f"{failure.message}",
        )
    if len(failures) > MAX_REPORTED_ERRORS:
        remaining = len(failures) - MAX_REPORTED_ERRORS
        print(f"... and {remaining} additional docstring audit failure(s).")
    return 1


def _audit_root(root: Path) -> list[AuditFailure]:
    """Audit every Python file under one configured root.

    Args:
        root:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    failures: list[AuditFailure] = []
    for path in sorted(root.rglob("*.py")):
        failures.extend(_audit_file(path))
    return failures


def _audit_file(path: Path) -> list[AuditFailure]:
    """Audit one Python source file for structured docstring compliance.

    Args:
        path:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    failures: list[AuditFailure] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            failures.extend(_audit_class(path, node))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            failures.extend(_audit_callable(path, node))
    return failures


def _audit_class(path: Path, node: ast.ClassDef) -> list[AuditFailure]:
    """Audit one class definition.

    Args:
        path:
            Value supplied to this callable.
        node:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    failures = _audit_docstring_basics(path, node, symbol_name=node.name)
    docstring = ast.get_docstring(node) or ""
    attributes = _class_attribute_names(node)
    if attributes and "Attributes:" not in docstring:
        failures.append(
            AuditFailure(
                path=path.as_posix(),
                lineno=node.lineno,
                symbol_name=node.name,
                message="class with attributes is missing an 'Attributes:' section",
            ),
        )
    return failures


def _audit_callable(
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[AuditFailure]:
    """Audit one function or method definition.

    Args:
        path:
            Value supplied to this callable.
        node:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    failures = _audit_docstring_basics(path, node, symbol_name=node.name)
    docstring = ast.get_docstring(node) or ""
    parameter_names = _documented_parameter_names(node)
    if parameter_names and "Args:" not in docstring:
        failures.append(
            AuditFailure(
                path=path.as_posix(),
                lineno=node.lineno,
                symbol_name=node.name,
                message="callable with parameters is missing an 'Args:' section",
            ),
        )
    if _requires_returns_section(node) and "Returns:" not in docstring:
        failures.append(
            AuditFailure(
                path=path.as_posix(),
                lineno=node.lineno,
                symbol_name=node.name,
                message="callable is missing a 'Returns:' section",
            ),
        )
    if _raised_exception_names(node) and "Raises:" not in docstring:
        failures.append(
            AuditFailure(
                path=path.as_posix(),
                lineno=node.lineno,
                symbol_name=node.name,
                message="callable that raises errors is missing a 'Raises:' section",
            ),
        )
    return failures


def _audit_docstring_basics(
    path: Path,
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    symbol_name: str,
) -> list[AuditFailure]:
    """Validate docstring presence and multi-line structure for one symbol.

    Args:
        path:
            Value supplied to this callable.
        node:
            Value supplied to this callable.
        symbol_name:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    docstring = ast.get_docstring(node)
    if docstring is None:
        return [
            AuditFailure(
                path=path.as_posix(),
                lineno=node.lineno,
                symbol_name=symbol_name,
                message="missing docstring",
            ),
        ]
    if len([line for line in docstring.strip().splitlines() if line.strip()]) < 2:
        return [
            AuditFailure(
                path=path.as_posix(),
                lineno=node.lineno,
                symbol_name=symbol_name,
                message="docstring must be multi-line and include structured detail",
            ),
        ]
    return []


def _documented_parameter_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    """Return parameter names that must appear under an ``Args:`` section.

    Args:
        node:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    names = [
        argument.arg
        for argument in (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        )
        if argument.arg not in SELF_NAMES
    ]
    if node.args.vararg is not None:
        names.append(node.args.vararg.arg)
    if node.args.kwarg is not None:
        names.append(node.args.kwarg.arg)
    return names


def _requires_returns_section(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether the callable must document a return value.

    Args:
        node:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if node.returns is None:
        return True
    return not (isinstance(node.returns, ast.Name) and node.returns.id == "None")


def _class_attribute_names(node: ast.ClassDef) -> list[str]:
    """Collect documented class attribute names from the class body.

    Args:
        node:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    names: list[str] = []
    for child in node.body:
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            names.append(child.target.id)
        elif isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name):
                    names.append(target.id)
    return names


def _raised_exception_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Collect statically visible exception names raised by one callable.

    Args:
        node:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    names: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Raise) or child.exc is None:
            continue
        exception_name = _exception_name_from_expression(child.exc)
        if exception_name is not None:
            names.add(exception_name)
    return names


def _exception_name_from_expression(expression: ast.expr) -> str | None:
    """Resolve a readable exception name from a raised expression.

    Args:
        expression:
            Value supplied to this callable.

    Returns:
        value:
            Structured value returned by this callable.
    """
    if isinstance(expression, ast.Call):
        return _exception_name_from_expression(expression.func)
    if isinstance(expression, ast.Name):
        return expression.id
    if isinstance(expression, ast.Attribute):
        return expression.attr
    return None


if __name__ == "__main__":
    raise SystemExit(main())
