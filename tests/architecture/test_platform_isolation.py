"""The cross-tenant session is reachable only through ``get_platform_db`` (behind ``require_platform_admin``).

``platform_session`` sets ``app.platform_admin``, which opens the narrow ``platform_select`` policies. If any other
module opened it, a tenant route could read other shops' rows, so the set of modules allowed to name it is fixed here.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.routing import APIRoute

from app.core.auth import get_platform_db, require_platform_admin
from app.main import app

APP = Path(__file__).resolve().parents[2] / "app"
ALLOWED = {"app/core/tenancy.py", "app/core/auth.py"}


def test_only_the_platform_dependency_opens_a_platform_session() -> None:
    users = {
        path.relative_to(APP.parent).as_posix()
        for path in APP.rglob("*.py")
        if "platform_session" in path.read_text(encoding="utf-8")
    }
    assert users <= ALLOWED, f"platform_session used outside the allowed modules: {sorted(users - ALLOWED)}"


def _walk(dependant: object) -> list[object]:
    found: list[object] = []
    for dep in dependant.dependencies:  # type: ignore[attr-defined]
        found.append(dep)
        found.extend(_walk(dep))
    return found


def _routes() -> list[tuple[str, object]]:
    out: list[tuple[str, object]] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            out.append((route.path, route.dependant))
        elif hasattr(route, "effective_route_contexts"):
            out.extend((ctx.path, ctx.dependant) for ctx in route.effective_route_contexts())
    return out


def test_every_platform_route_requires_an_operator_and_closes_its_session_before_responding() -> None:
    platform_routes = [(path, dep) for path, dep in _routes() if "/platform/" in path]
    assert platform_routes, "no /platform routes found"
    for path, dependant in platform_routes:
        deps = _walk(dependant)
        assert any(getattr(d, "call", None) is require_platform_admin for d in deps), path
        db = [d for d in deps if getattr(d, "call", None) is get_platform_db]
        assert db and all(d.scope == "function" for d in db), f"{path} must use get_platform_db(scope='function')"  # type: ignore[attr-defined]


SYSTEM_ALLOWED = {"app/core/tenancy.py", "app/services/marketing_publisher.py", "app/services/automation_service.py"}


def test_only_the_scheduler_opens_a_system_session() -> None:
    """``system_session`` opens a read-only look at which shops have posts or schedules; nothing else may use it."""
    users = {
        path.relative_to(APP.parent).as_posix()
        for path in APP.rglob("*.py")
        if "system_session" in path.read_text(encoding="utf-8")
    }
    assert users <= SYSTEM_ALLOWED, f"system_session used outside the scheduler: {sorted(users - SYSTEM_ALLOWED)}"
