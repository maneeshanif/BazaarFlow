"""Tasks 79 and 82 (F-025, D-004): the operator's view across shops, tenant suspension, and the platform overview.

Overview dataset (every figure hand-computed):
  shops: Operator Co, Shop A (created 30 days ago), Shop B, and one visitor demo shop     -> 3 real shops, 1 demo
  3 real shops now; 1 existed before the last 7 days (Shop A)                             -> change 200%
  Shop A has an order today, Shop B has an agent run today, the demo shop has an order    -> 2 active real shops
  messages: 3 today and 4 five days ago (all in Shop A)                                   -> 3 today, 7 in 7 days = 1 per day
  agent runs (7 days): A ok 0.03 USD, A ok 0.02 USD, B failed 0                          -> 3 runs, 1 failed = 33%, spend 0.05
"""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text

from app.core.tenancy import platform_session, tenant_session
from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg

OVERVIEW = "/api/v1/platform/overview"
TENANTS = "/api/v1/platform/tenants"


@pytest_asyncio.fixture(autouse=True)
async def clean_slate(admin_conn: asyncpg.Connection) -> None:
    """The platform figures are global, so each test starts from an empty database (the container is shared)."""
    await admin_conn.execute("TRUNCATE tenants, users, audit_logs, login_attempts, refresh_tokens RESTART IDENTITY CASCADE")


async def operator(client: AsyncClient, admin: asyncpg.Connection, shop: str = "Operator Co") -> dict[str, Any]:
    """A shop owner who is also a BazaarFlow operator (the flag is set by hand, as in production)."""
    acct = await register(client, shop)
    await admin.execute("UPDATE users SET is_platform_admin = true WHERE email = $1", acct["email"])
    res = await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})
    assert res.status_code == 200, res.text
    user_id = await admin.fetchval("SELECT id FROM users WHERE email = $1", acct["email"])
    return {**acct, **res.json(), "user_id": user_id}


async def _order(owner: dict[str, Any]) -> None:
    tid = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tid) as db:
        await db.execute(
            text(
                "INSERT INTO orders (id, tenant_id, status, subtotal, discount, total, channel, version, created_at, updated_at) "
                "VALUES (:id, :t, 'posted', 100, 0, 100, 'pos', 1, now(), now())"
            ),
            {"id": uuid.uuid4(), "t": tid},
        )


async def _run(owner: dict[str, Any], outcome: str, spend: int) -> None:
    tid = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tid) as db:
        await db.execute(
            text(
                "INSERT INTO agent_runs (id, tenant_id, agent, session_id, input_text, output_text, trace_json, action_ids, "
                "outcome, tokens_in, tokens_out, spend_micros, duration_ms, created_at) "
                "VALUES (:id, :t, 'sales', 's', 'in', 'out', '[]', '[]', :o, 0, 0, :sp, 10, now())"
            ),
            {"id": uuid.uuid4(), "t": tid, "o": outcome, "sp": spend},
        )


async def _messages(admin: asyncpg.Connection, owner: dict[str, Any], count: int, days_ago: int) -> None:
    for _ in range(count):
        await admin.execute(
            "INSERT INTO messages (id, tenant_id, phone, direction, text, status, created_at, updated_at) "
            "VALUES (gen_random_uuid(), $1, '+923001110001', 'inbound', 'hi', 'delivered', "
            "now() - make_interval(days => $2), now())",
            uuid.UUID(owner["tenant_id"]),
            days_ago,
        )


async def test_every_overview_figure_matches_the_hand_computed_value(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    op = await operator(client, admin_conn)
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    demo = await register(client, "Visitor Demo")
    await admin_conn.execute("UPDATE tenants SET created_at = now() - interval '30 days' WHERE id = $1", uuid.UUID(a["tenant_id"]))
    await admin_conn.execute("UPDATE tenants SET demo_expires_at = now() + interval '1 day' WHERE id = $1", uuid.UUID(demo["tenant_id"]))
    await _order(a)
    await _order(demo)
    await _run(b, "failed", 0)
    await _run(a, "ok", 30_000)
    await _run(a, "ok", 20_000)
    await _messages(admin_conn, a, 3, 0)
    await _messages(admin_conn, a, 4, 5)

    body = (await client.get(OVERVIEW, headers=bearer(op))).json()
    assert (body["tenants"]["value"], body["tenants"]["previous"], body["tenants"]["change_percent"]) == (3, 1, 200)
    assert body["demo_tenants"] == 1 and body["active_tenants_7d"] == 2
    assert (body["messages_today"], body["messages_per_day_7d"]) == (3, 1)
    assert (body["agent_runs_7d"], body["error_rate_percent"], body["ai_spend_month_usd"]) == (3, 33, "0.05")
    assert body["is_empty"] is False


async def test_the_overview_of_a_platform_with_no_activity_has_zero_rates_not_errors(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    op = await operator(client, admin_conn)
    res = await client.get(OVERVIEW, headers=bearer(op))
    assert res.status_code == 200
    body = res.json()
    assert body["agent_runs_7d"] == 0 and body["error_rate_percent"] is None
    assert (body["messages_today"], body["messages_per_day_7d"], body["ai_spend_month_usd"]) == (0, 0, "0.00")


async def test_only_operators_can_open_platform_endpoints(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    for url in (OVERVIEW, TENANTS, f"{TENANTS}/{owner['tenant_id']}"):
        assert (await client.get(url, headers=bearer(owner))).status_code == 403
        assert (await client.get(url)).status_code == 401
    suspend = await client.post(f"{TENANTS}/{owner['tenant_id']}/suspend", json={"reason": "test"}, headers=bearer(owner))
    assert suspend.status_code == 403


async def test_the_tenant_list_shows_every_real_shop_with_size_and_last_activity(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    op = await operator(client, admin_conn)
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    demo = await register(client, "Visitor Demo")
    await admin_conn.execute("UPDATE tenants SET demo_expires_at = now() + interval '1 day' WHERE id = $1", uuid.UUID(demo["tenant_id"]))
    await _order(a)
    page = (await client.get(TENANTS, headers=bearer(op))).json()
    names = {t["name"] for t in page["items"]}
    assert names == {"Operator Co", "Shop A", "Shop B"} and page["total"] == 3
    row_a = next(t for t in page["items"] if t["name"] == "Shop A")
    assert row_a["users"] == 1 and row_a["status"] == "active" and row_a["is_demo"] is False
    assert row_a["last_activity_at"] is not None
    assert next(t for t in page["items"] if t["name"] == "Shop B")["last_activity_at"] is None
    assert "owner_phone" not in row_a and "credentials" not in row_a
    with_demo = (await client.get(TENANTS, params={"include_demo": True}, headers=bearer(op))).json()
    assert with_demo["total"] == 4 and any(t["is_demo"] for t in with_demo["items"])
    found = (await client.get(TENANTS, params={"q": "shop b"}, headers=bearer(op))).json()
    assert [t["name"] for t in found["items"]] == ["Shop B"]
    assert b["tenant_id"] == found["items"][0]["id"]
    assert (await client.get(TENANTS, params={"status": "deleted"}, headers=bearer(op))).status_code == 422
    one = await client.get(f"{TENANTS}/{a['tenant_id']}", headers=bearer(op))
    assert one.status_code == 200 and one.json()["name"] == "Shop A"
    assert (await client.get(f"{TENANTS}/{uuid.uuid4()}", headers=bearer(op))).status_code == 404


async def test_suspending_a_shop_locks_its_users_out_at_once_and_reactivating_lets_them_back(
    client: AsyncClient, admin_conn: asyncpg.Connection
) -> None:
    op = await operator(client, admin_conn)
    a = await register(client, "Shop A")
    assert (await client.get("/api/v1/customers/", headers=bearer(a))).status_code == 200

    res = await client.post(f"{TENANTS}/{a['tenant_id']}/suspend", json={"reason": "Unpaid invoice"}, headers=bearer(op))
    assert res.status_code == 200 and res.json()["status"] == "suspended"
    locked = await client.get("/api/v1/customers/", headers=bearer(a))
    assert locked.status_code == 403 and "suspended" in locked.json()["detail"]
    login = await client.post("/api/v1/auth/login", json={"email": a["email"], "password": a["password"]})
    assert login.status_code == 403 and "suspended" in login.json()["detail"]
    assert [t["name"] for t in (await client.get(TENANTS, params={"status": "suspended"}, headers=bearer(op))).json()["items"]] == ["Shop A"]

    back = await client.post(f"{TENANTS}/{a['tenant_id']}/reactivate", headers=bearer(op))
    assert back.status_code == 200 and back.json()["status"] == "active"
    assert (await client.get("/api/v1/customers/", headers=bearer(a))).status_code == 200
    assert (await client.post("/api/v1/auth/login", json={"email": a["email"], "password": a["password"]})).status_code == 200


async def test_suspension_is_audited_without_a_tenant_and_needs_a_reason(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    op = await operator(client, admin_conn)
    a = await register(client, "Shop A")
    assert (await client.post(f"{TENANTS}/{a['tenant_id']}/suspend", json={"reason": "x"}, headers=bearer(op))).status_code == 422
    assert (await client.post(f"{TENANTS}/{a['tenant_id']}/suspend", json={}, headers=bearer(op))).status_code == 422
    await client.post(f"{TENANTS}/{a['tenant_id']}/suspend", json={"reason": "Unpaid invoice"}, headers=bearer(op))
    row = await admin_conn.fetchrow("SELECT tenant_id, actor_id, after_json FROM audit_logs WHERE action = 'platform.tenant_suspended'")
    assert row is not None and row["tenant_id"] is None and row["actor_id"] == str(op["user_id"])
    assert "Unpaid invoice" in str(row["after_json"])
    access = await admin_conn.fetchval("SELECT count(*) FROM audit_logs WHERE action = 'platform.access'")
    assert access >= 1  # every platform request leaves a trace


async def test_an_operator_cannot_suspend_the_shop_they_are_signed_in_to(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    op = await operator(client, admin_conn)
    res = await client.post(f"{TENANTS}/{op['tenant_id']}/suspend", json={"reason": "by mistake"}, headers=bearer(op))
    assert res.status_code == 409 and res.json()["code"] == "cannot_suspend_own_shop"


async def test_the_platform_session_opens_only_the_listed_tables(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    op = await operator(client, admin_conn)
    a = await register(client, "Shop A")
    await client.post("/api/v1/customers/", json={"phone": "+923001110001", "name": "Private"}, headers=bearer(a))
    async with platform_session(op["user_id"]) as db:
        assert (await db.execute(text("SELECT count(*) FROM tenants"))).scalar_one() >= 2
        for table in ("customers", "products", "ledger_entries", "payments", "agent_actions", "vendors", "audit_logs"):
            assert (await db.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one() == 0, f"{table} must stay closed"


async def test_a_normal_tenant_session_still_sees_only_its_own_shop(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    await register(client, "Shop B")
    async with tenant_session(uuid.UUID(a["tenant_id"])) as db:
        assert (await db.execute(text("SELECT count(*) FROM tenants"))).scalar_one() == 1
