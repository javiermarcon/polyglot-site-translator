"""Navigation state for the presentation layer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RouteName(StrEnum):
    """Known routes in the frontend shell.

    Attributes:
        DASHBOARD: Documented attribute exposed by this type.
        PROJECTS: Documented attribute exposed by this type.
        PROJECT_DETAIL: Documented attribute exposed by this type.
        PROJECT_EDITOR: Documented attribute exposed by this type.
        SYNC: Documented attribute exposed by this type.
        AUDIT: Documented attribute exposed by this type.
        PO_PROCESSING: Documented attribute exposed by this type.
        SETTINGS: Documented attribute exposed by this type.
    """

    DASHBOARD = "dashboard"
    PROJECTS = "projects"
    PROJECT_DETAIL = "project-detail"
    PROJECT_EDITOR = "project-editor"
    SYNC = "sync"
    AUDIT = "audit"
    PO_PROCESSING = "po-processing"
    SETTINGS = "settings"


@dataclass(frozen=True)
class Route:
    """Typed route descriptor used by the UI shell.

    Attributes:
        name (RouteName): Documented attribute exposed by this type.
        project_id (str | None): Documented attribute exposed by this type.
    """

    name: RouteName
    project_id: str | None = None


class FrontendRouter:
    """Small router abstraction over the active screen context.

    Attributes:
        None: This type does not declare additional class-level attributes.
    """

    def __init__(self) -> None:
        """Start the frontend on the dashboard route with no selected project.

        Returns:
            None: This callable does not return a value.
        """
        self._current = Route(name=RouteName.DASHBOARD)

    @property
    def current(self) -> Route:
        """Return the active route.

        Returns:
            Route: Structured value returned by this callable.
        """
        return self._current

    def go_to(self, route_name: RouteName, project_id: str | None = None) -> Route:
        """Set the active route and preserve optional project context.

        Args:
            route_name (RouteName): Value supplied to this callable.
            project_id (str | None): Value supplied to this callable.

        Returns:
            Route: Structured value returned by this callable.
        """
        self._current = Route(name=route_name, project_id=project_id)
        return self._current
