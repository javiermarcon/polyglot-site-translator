"""Navigation state for the presentation layer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RouteName(StrEnum):
    """Known routes in the frontend shell."""

    DASHBOARD = "dashboard"
    PROJECTS = "projects"
    PROJECT_DETAIL = "project-detail"
    SYNC = "sync"
    AUDIT = "audit"
    PO_PROCESSING = "po-processing"
    SETTINGS = "settings"


@dataclass(frozen=True)
class Route:
    """Typed route descriptor used by the UI shell."""

    name: RouteName
    project_id: str | None = None


class FrontendRouter:
    """Small router abstraction over the active screen context."""

    def __init__(self) -> None:
        self._current = Route(name=RouteName.DASHBOARD)

    @property
    def current(self) -> Route:
        """Return the active route."""
        return self._current

    def go_to(self, route_name: RouteName, project_id: str | None = None) -> Route:
        """Set the active route and preserve optional project context."""
        self._current = Route(name=route_name, project_id=project_id)
        return self._current
