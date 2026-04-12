"""BDD steps for framework-driven sync filter resolution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, cast

import behave as behave_module  # type: ignore[import-untyped]

from polyglot_site_translator.adapters.framework_registry import FrameworkAdapterRegistry
from polyglot_site_translator.domain.site_registry.models import RegisteredSite, SiteProject
from polyglot_site_translator.domain.sync.scope import ResolvedSyncScope
from polyglot_site_translator.services.framework_sync_scope import (
    FrameworkSyncScopeService,
)

StepFunction = TypeVar("StepFunction", bound=Callable[..., object])

given = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.given)
when = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.when)
then = cast(Callable[[str], Callable[[StepFunction], StepFunction]], behave_module.then)


@dataclass
class SyncFilterScenarioState:
    """Scenario state for framework sync filter resolution."""

    site: RegisteredSite | None = None
    resolved_scope: ResolvedSyncScope | None = None


def _state(context: object) -> SyncFilterScenarioState:
    state = getattr(context, "sync_filter_state", None)
    if isinstance(state, SyncFilterScenarioState):
        return state
    state = SyncFilterScenarioState()
    context.sync_filter_state = state  # type: ignore[attr-defined]
    return state


@given('a registered "{framework_type}" project for sync filter resolution')
def step_given_registered_project(context: object, framework_type: str) -> None:
    tmp_dir = Path.cwd() / ".behave-sync-filters" / framework_type
    tmp_dir.mkdir(parents=True, exist_ok=True)
    state = _state(context)
    state.site = RegisteredSite(
        project=SiteProject(
            id=f"{framework_type}-project",
            name=f"{framework_type}-project",
            framework_type=framework_type,
            local_path=str(tmp_dir),
            default_locale="en",
            is_active=True,
        ),
        remote_connection=None,
    )


@when("the operator resolves the framework sync scope")
def step_when_resolve_scope(context: object) -> None:
    state = _state(context)
    if state.site is None:
        msg = "A registered site must be configured before resolving scope."
        raise AssertionError(msg)
    service = FrameworkSyncScopeService(registry=FrameworkAdapterRegistry.discover_installed())
    state.resolved_scope = service.resolve_for_site(state.site)


@then('the resolved sync scope status is "{status}"')
def step_then_scope_status(context: object, status: str) -> None:
    state = _state(context)
    resolved_scope = state.resolved_scope
    if resolved_scope is None:
        msg = "The sync scope must be resolved before asserting its status."
        raise AssertionError(msg)
    assert resolved_scope.status == status


@then('the resolved sync scope includes the filter "{relative_path}"')
def step_then_scope_contains_filter(context: object, relative_path: str) -> None:
    state = _state(context)
    resolved_scope = state.resolved_scope
    if resolved_scope is None:
        msg = "The sync scope must be resolved before asserting its filters."
        raise AssertionError(msg)
    filters = resolved_scope.filters
    assert relative_path in [sync_filter.relative_path for sync_filter in filters]


@then('the resolved sync scope excludes the filter "{relative_path}"')
def step_then_scope_contains_exclusion(context: object, relative_path: str) -> None:
    state = _state(context)
    resolved_scope = state.resolved_scope
    if resolved_scope is None:
        msg = "The sync scope must be resolved before asserting its exclusions."
        raise AssertionError(msg)
    assert relative_path in [sync_filter.relative_path for sync_filter in resolved_scope.excludes]


@then('the resolved sync scope does not exclude the filter "{relative_path}"')
def step_then_scope_lacks_exclusion(context: object, relative_path: str) -> None:
    state = _state(context)
    resolved_scope = state.resolved_scope
    if resolved_scope is None:
        msg = "The sync scope must be resolved before asserting its exclusions."
        raise AssertionError(msg)
    assert relative_path not in [
        sync_filter.relative_path for sync_filter in resolved_scope.excludes
    ]


@then("the resolved sync scope reports no sync filters")
def step_then_scope_has_no_filters(context: object) -> None:
    state = _state(context)
    resolved_scope = state.resolved_scope
    if resolved_scope is None:
        msg = "The sync scope must be resolved before asserting its filters."
        raise AssertionError(msg)
    assert resolved_scope.filters == ()
