"""Task 45: the agent activity log (PRD F-022): who asked, what the agent did, what it cost; roles and isolation."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from tests.pg.agent_support import RUNS, propose_sale, say, shop
from tests.pg.agent_support import scripted_provider as scripted_provider  # noqa: F401  (autouse fixture)
from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg


async def test_the_log_lists_every_turn_with_who_what_and_cost(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    staff = await member(client, app_engine, owner, "staff")
    await propose_sale(client, staff)
    listing = (await client.get(RUNS, headers=bearer(owner))).json()
    assert listing["total"] == 2
    run = listing["items"][0]  # newest first: the "yes"
    assert run["agent"] == "sales" and run["outcome"] == "ok" and run["user_name"] and run["input_text"] == "yes"
    assert run["tokens_in"] > 0 and run["tokens_out"] > 0 and float(run["spend_usd"]) > 0 and run["duration_ms"] >= 0
    assert len(run["action_ids"]) == 1
    detail = (await client.get(f"{RUNS}{run['id']}", headers=bearer(owner))).json()
    assert [s["tool"] for s in detail["trace"]] == ["post_order"] and detail["trace"][0]["ok"] is True


async def test_the_log_filters_pages_and_is_read_only(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    for i in range(3):
        await say(client, owner, "sell 1 classic shirt", f"p{i}")
    page = (await client.get(RUNS, params={"limit": 2}, headers=bearer(owner))).json()
    assert page["total"] == 3 and len(page["items"]) == 2 and page["next_cursor"]
    assert (await client.get(RUNS, params={"outcome": "failed"}, headers=bearer(owner))).json()["total"] == 0
    assert (await client.get(RUNS, params={"outcome": "ok", "agent": "sales"}, headers=bearer(owner))).json()["total"] == 3
    assert (await client.get(RUNS, params={"outcome": "bogus"}, headers=bearer(owner))).status_code == 422
    tenant_id = uuid.UUID(owner["tenant_id"])
    from sqlalchemy.exc import DBAPIError

    for statement in ("UPDATE agent_runs SET outcome = 'failed'", "DELETE FROM agent_runs"):
        with pytest.raises(DBAPIError):
            async with tenant_session(tenant_id) as db:
                await db.execute(text(statement))


async def test_only_owners_and_managers_read_the_log_and_shops_are_separate(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await shop(client, a)
    staff = await member(client, app_engine, a, "staff")
    manager = await member(client, app_engine, a, "manager")
    reply = await say(client, staff, "sell 1 classic shirt")
    assert (await client.get(RUNS, headers=bearer(staff))).status_code == 403
    assert (await client.get(f"{RUNS}{reply['run_id']}", headers=bearer(staff))).status_code == 403
    assert (await client.get(f"{RUNS}status", headers=bearer(staff))).status_code == 403
    assert (await client.get(RUNS)).status_code == 401
    assert (await client.get(RUNS, headers=bearer(manager))).json()["total"] == 1
    assert (await client.get(RUNS, headers=bearer(b))).json()["total"] == 0
    assert (await client.get(f"{RUNS}{reply['run_id']}", headers=bearer(b))).status_code == 404
    assert (await client.get(f"{RUNS}{uuid.uuid4()}", headers=bearer(a))).status_code == 404


async def test_the_status_shows_the_switch_and_the_months_allowance(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    before = (await client.get(f"{RUNS}status", headers=bearer(owner))).json()
    assert before["enabled"] is True and before["percent_used"] == 0 and before["runs_this_month"] == 0 and before["month_cap_usd"] == "5.00"
    await say(client, owner, "sell 1 classic shirt")
    after = (await client.get(f"{RUNS}status", headers=bearer(owner))).json()
    assert after["runs_this_month"] == 1 and float(after["month_spend_usd"]) >= 0
