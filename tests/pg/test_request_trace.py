"""Task 57: the access line of an authenticated request names the shop and the person, and the route, not the ids in it."""

from __future__ import annotations

import logging

import pytest
from httpx import AsyncClient

from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg


def access_lines(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "bazaarflow.access"]


async def test_the_access_line_carries_tenant_and_user_ids_and_the_route_template(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    owner = await register(client, "Shop A")
    caplog.set_level(logging.INFO)
    logging.getLogger("bazaarflow.access").disabled = False  # the migration fixture's fileConfig switches it off
    res = await client.get("/api/v1/team/", headers=bearer(owner))
    line = access_lines(caplog)[-1]
    assert line.status == 200 and line.tenant_id == owner["tenant_id"] and line.user_id  # type: ignore[attr-defined]
    assert line.route == "/api/v1/team/"  # type: ignore[attr-defined]
    assert line.request_id == res.headers["x-request-id"]  # type: ignore[attr-defined]
    missing = await client.get(f"/api/v1/orders/{owner['tenant_id']}", headers=bearer(owner))
    assert missing.status_code == 404 and access_lines(caplog)[-1].route == "/api/v1/orders/{order_id}"  # type: ignore[attr-defined]
