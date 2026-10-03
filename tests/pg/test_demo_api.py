"""Task 47: the public live demo (PRD F-027): a temporary shop per visitor, believable data, its own AI allowance."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.cli.purge_demos import purge
from app.core.settings import settings
from app.core.tenancy import tenant_session
from app.core.throttle import reset_signup_throttle
from tests.pg.agent_support import scripted_provider as scripted_provider  # noqa: F401  (autouse fixture)
from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg

START = "/api/v1/demo/start"


@pytest.fixture(autouse=True)
def fresh_throttle(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_signup_throttle()
    monkeypatch.setattr(settings, "DEMO_MAX_PER_HOUR", 0)


async def start(client: AsyncClient) -> dict[str, Any]:
    res = await client.post(START)
    assert res.status_code == 201, res.text
    made: dict[str, Any] = res.json()
    return made


async def test_starting_a_demo_gives_an_owner_session_in_a_full_shop(client: AsyncClient) -> None:
    demo = await start(client)
    assert demo["role"] == "owner" and demo["access_token"] and demo["refresh_token"]
    me = (await client.get("/api/v1/auth/me", headers=bearer(demo))).json()
    assert me["role"] == "owner"
    products = (await client.get("/api/v1/inventory/", params={"limit": 50}, headers=bearer(demo))).json()
    assert products["total"] == 8
    customers = (await client.get("/api/v1/customers/", headers=bearer(demo))).json()
    assert customers["total"] == 3
    summary = (await client.get("/api/v1/dashboard/summary", params={"range": "7d"}, headers=bearer(demo))).json()
    assert summary["orders"]["value"] == 5 and float(summary["sales"]["value"]) > 0
    assert summary["low_stock"] >= 2  # Lawn Suit and Leather Belt are at or under their reorder level
    assert float(summary["unpaid_udhaar"]) == 4500.0  # 2 x Shirt + Cap = 5,500, Rs 1,000 paid now, so Ali owes Rs 4,500
    assert len([d for d in summary["trend"] if d["orders"] > 0]) >= 4


async def test_each_visitor_gets_their_own_shop(client: AsyncClient) -> None:
    a, b = await start(client), await start(client)
    assert a["tenant_id"] != b["tenant_id"]
    sale = (await client.get("/api/v1/orders/", headers=bearer(a))).json()["items"][0]
    assert (await client.get(f"/api/v1/orders/{sale['id']}", headers=bearer(b))).status_code == 404
    # a real shop never sees demo data either
    real = await register(client, "Real Shop")
    assert (await client.get("/api/v1/inventory/", headers=bearer(real))).json()["total"] == 0


async def test_a_demo_shop_has_its_own_tiny_ai_allowance_and_an_expiry(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    demo = await start(client)
    status = (await client.get("/api/v1/agent-runs/status", headers=bearer(demo))).json()
    assert status["month_cap_usd"] == "0.05"
    async with tenant_session(uuid.UUID(demo["tenant_id"])) as db:
        expires = (await db.execute(text("SELECT demo_expires_at FROM tenants"))).scalar_one()
    assert timedelta(hours=23) < expires - datetime.now(timezone.utc) <= timedelta(hours=24)
    # the owner of a real shop still has the platform default
    real = await register(client, "Real Shop")
    assert (await client.get("/api/v1/agent-runs/status", headers=bearer(real))).json()["month_cap_usd"] == "5.00"


async def test_the_demo_agent_works_on_the_demo_data_and_stops_at_its_allowance(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    demo = await start(client)
    reply = (
        await client.post("/api/v1/chat/sales", json={"message": "sell 1 cotton shirt to ali"}, headers=bearer(demo))
    ).json()
    assert "Draft sale" in reply["reply"] and "Cotton Shirt" in reply["reply"]
    from tests.pg.agent_support import PricedReplay  # noqa: F401  (priced turns are covered in test_agent_chat)

    async with tenant_session(uuid.UUID(demo["tenant_id"])) as db:
        await db.execute(text("UPDATE tenants SET agent_cap_usd = 0.00"))
    stopped = (
        await client.post("/api/v1/chat/sales", json={"message": "sell 1 cotton shirt to ali"}, headers=bearer(demo))
    ).json()
    assert stopped["outcome"] == "spend_limit"


async def test_starting_demos_is_rate_limited_per_address(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DEMO_MAX_PER_HOUR", 2)
    headers = {"x-forwarded-for": "203.0.113.7"}
    assert (await client.post(START, headers=headers)).status_code == 201
    assert (await client.post(START, headers=headers)).status_code == 201
    third = await client.post(START, headers=headers)
    assert third.status_code == 429 and third.json()["code"] == "demo_rate_limited"
    assert (await client.post(START, headers={"x-forwarded-for": "203.0.113.8"})).status_code == 201


async def test_the_demo_can_be_switched_off(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DEMO_ENABLED", False)
    res = await client.post(START)
    assert res.status_code == 404 and res.json()["code"] == "demo_disabled"


async def test_purging_removes_only_expired_demo_shops_and_their_owners(
    client: AsyncClient, pg_urls: dict[str, str]
) -> None:
    old, fresh = await start(client), await start(client)
    real = await register(client, "Real Shop")
    engine = create_async_engine(pg_urls["admin"], poolclass=NullPool, connect_args={"statement_cache_size": 0})
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE tenants SET demo_expires_at = now() - interval '1 minute' WHERE id = :id"),
                {"id": old["tenant_id"]},
            )
        assert await purge(engine) == 1
        async with engine.connect() as conn:
            left = {str(r[0]) for r in (await conn.execute(text("SELECT id FROM tenants"))).all()}
            assert old["tenant_id"] not in left and fresh["tenant_id"] in left and real["tenant_id"] in left
            for table in ("products", "orders", "stock_movements", "ledger_entries", "customers", "audit_logs"):
                n = (
                    await conn.execute(
                        text(f"SELECT count(*) FROM {table} WHERE tenant_id = :id"), {"id": old["tenant_id"]}
                    )
                ).scalar_one()
                assert n == 0, table
            demo_users = (
                await conn.execute(text("SELECT count(*) FROM users WHERE email LIKE '%@demo.bazaarflow.invalid'"))
            ).scalar_one()
            live_demos = (await conn.execute(text("SELECT count(*) FROM tenants WHERE demo_expires_at IS NOT NULL"))).scalar_one()
            assert demo_users == live_demos  # no throwaway owner outlives its shop
        assert await purge(engine) == 0
    finally:
        await engine.dispose()
    assert (await client.get("/api/v1/inventory/", headers=bearer(fresh))).status_code == 200
