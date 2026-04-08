"""Shared filesystem helpers for framework adapters."""

from __future__ import annotations

from pathlib import Path


def find_first_level_file(project_path: Path, filename: str) -> Path | None:
    """Return the first matching file found at the project root or one level below."""
    root_candidate = project_path / filename
    if root_candidate.is_file():
        return root_candidate
    for child in project_path.iterdir():
        candidate = child / filename
        if child.is_dir() and candidate.is_file():
            return candidate
    return None


def find_first_level_directory(project_path: Path, dirname: str) -> Path | None:
    """Return the first matching directory found at the project root or one level below."""
    root_candidate = project_path / dirname
    if root_candidate.is_dir():
        return root_candidate
    for child in project_path.iterdir():
        candidate = child / dirname
        if child.is_dir() and candidate.is_dir():
            return candidate
    return None


def read_text_if_present(path: Path) -> str:
    """Read a text file if possible and return an empty string otherwise."""
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
    except UnicodeDecodeError:
        return ""
