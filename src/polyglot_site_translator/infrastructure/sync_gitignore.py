"""Utilities for deriving sync exclusions from .gitignore files."""

from __future__ import annotations

from pathlib import Path

from polyglot_site_translator.domain.sync.scope import (
    ConfiguredSyncRule,
    SyncFilterType,
    SyncRuleBehavior,
)


def load_gitignore_sync_rules(project_path: Path) -> tuple[ConfiguredSyncRule, ...]:
    """Load supported sync exclusions from the project's .gitignore file."""
    gitignore_path = project_path / ".gitignore"
    if not gitignore_path.exists():
        return ()
    raw_lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    configured_rules: list[ConfiguredSyncRule] = []
    for raw_line in raw_lines:
        rule = _parse_gitignore_line(raw_line)
        if rule is not None:
            configured_rules.append(rule)
    return tuple(configured_rules)


def _parse_gitignore_line(raw_line: str) -> ConfiguredSyncRule | None:
    stripped_line = raw_line.strip()
    if stripped_line == "" or stripped_line.startswith("#") or stripped_line.startswith("!"):
        return None
    normalized_line = stripped_line.lstrip("/").rstrip()
    if normalized_line.endswith("/") and "/" not in normalized_line[:-1]:
        relative_path = normalized_line.rstrip("/")
        return ConfiguredSyncRule(
            relative_path=relative_path,
            filter_type=SyncFilterType.GLOB,
            behavior=SyncRuleBehavior.EXCLUDE,
            description=f"Derived from .gitignore: {stripped_line}",
            is_enabled=True,
        )
    if any(character in normalized_line for character in "*?[]"):
        return ConfiguredSyncRule(
            relative_path=normalized_line.rstrip("/"),
            filter_type=SyncFilterType.GLOB,
            behavior=SyncRuleBehavior.EXCLUDE,
            description=f"Derived from .gitignore: {stripped_line}",
            is_enabled=True,
        )
    filter_type = SyncFilterType.FILE
    if normalized_line.endswith("/"):
        filter_type = SyncFilterType.DIRECTORY
    elif "/" not in normalized_line:
        filter_type = SyncFilterType.GLOB
    return ConfiguredSyncRule(
        relative_path=normalized_line.rstrip("/"),
        filter_type=filter_type,
        behavior=SyncRuleBehavior.EXCLUDE,
        description=f"Derived from .gitignore: {stripped_line}",
        is_enabled=True,
    )
