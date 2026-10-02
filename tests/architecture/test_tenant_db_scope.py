"""Every route that uses ``get_tenant_db`` must close the session BEFORE the response is sent.

FastAPI (>= 0.118) runs the exit code of a yield dependency after the response by default, which would let a
client see a 201 before the transaction commits (or never learn that the commit failed). ``scope="function"``
runs the exit code right after the endpoint returns.
"""

from __future__ import annotations

from typing import Any

from fastapi.routing import APIRoute

from app.core.auth import get_tenant_db
from app.main import app


def _walk(dependant: Any) -> list[Any]:
    found = []
    for dep in dependant.dependencies:
        found.append(dep)
        found.extend(_walk(dep))
    return found


def _dependants() -> list[Any]:
    out = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            out.append(route.dependant)
        elif hasattr(route, "effective_route_contexts"):
            out.extend(ctx.dependant for ctx in route.effective_route_contexts())
    return out


def test_there_are_routes_using_the_tenant_session() -> None:
    assert any(dep.call is get_tenant_db for d in _dependants() for dep in _walk(d))


def test_tenant_session_is_closed_before_the_response_is_sent() -> None:
    bad = [dep.path for d in _dependants() for dep in _walk(d) if dep.call is get_tenant_db and dep.scope != "function"]
    assert not bad, f"get_tenant_db must be used with scope='function' on: {sorted(set(bad))}"
