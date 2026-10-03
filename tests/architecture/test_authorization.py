"""Architecture test: every route carries an explicit authorization decision (PRD §3.7 constraint 3, §19).

A decision is a dependency with an ``__authz__`` attribute: ``public_route``, ``require_role(...)`` or
``require_platform_admin``. Adding a route without one fails this test, so no endpoint can ship
undecided by accident.
"""

from __future__ import annotations

from typing import Any

from fastapi.routing import APIRoute

from app.main import app


def _walk(dependant: Any) -> list[Any]:
    found: list[Any] = []
    for dep in dependant.dependencies:
        found.append(dep.call)
        found.extend(_walk(dep))
    return found


def _all_routes() -> list[tuple[str, set[str], Any]]:
    routes: list[tuple[str, set[str], Any]] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append((route.path, set(route.methods or []), route.dependant))
        elif hasattr(route, "effective_route_contexts"):
            for ctx in route.effective_route_contexts():
                routes.append((ctx.path, set(ctx.methods), ctx.dependant))
    return routes


def test_router_is_not_empty() -> None:
    assert len(_all_routes()) >= 40


def test_every_route_has_an_authorization_decision() -> None:
    undecided = [
        f"{sorted(methods)} {path}"
        for path, methods, dependant in _all_routes()
        if not any(hasattr(call, "__authz__") for call in _walk(dependant))
    ]
    assert not undecided, "Routes without public_route/require_role/require_platform_admin:\n" + "\n".join(
        sorted(undecided)
    )


def test_only_expected_routes_are_public() -> None:
    public = sorted(
        {
            path
            for path, _methods, dependant in _all_routes()
            if any(getattr(call, "__authz__", None) == "public" for call in _walk(dependant))
        }
    )
    allowed_prefixes = (
        "/health",
        "/api/health",
        "/auth/register",
        "/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/auth/refresh",
        "/auth/logout",
        "/webhook",
        "/vapi/webhook",
    )
    unexpected = [p for p in public if not p.startswith(allowed_prefixes)]
    assert not unexpected, f"Unexpected public routes: {unexpected}"


def test_versioned_routes_are_not_double_prefixed_and_only_real_v1_routers_are_mounted() -> None:
    paths = {path for path, _methods, _dep in _all_routes()}
    assert not [p for p in paths if p.startswith("/api/v1/api")], "legacy routers must not be mounted under /api/v1"
    v1_areas = {p.split("/")[3] for p in paths if p.startswith("/api/v1/")}
    assert v1_areas <= {"auth", "customers", "inventory"}, f"unexpected /api/v1 areas: {v1_areas}"
