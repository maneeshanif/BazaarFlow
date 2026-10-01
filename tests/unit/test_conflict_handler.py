"""An optimistic-locking conflict is reported as 409, never a bare 500 (review finding on task 03)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm.exc import StaleDataError

from app.core.auth import public_route
from app.main import app


def test_stale_data_error_becomes_a_409() -> None:
    from fastapi import Depends

    @app.get("/_test/stale", dependencies=[Depends(public_route)])
    async def _stale() -> None:
        raise StaleDataError("row was updated by another transaction")

    try:
        res = TestClient(app, raise_server_exceptions=False).get("/_test/stale")
    finally:
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/_test/stale"]
    assert res.status_code == 409
    assert "Reload" in res.json()["detail"]
