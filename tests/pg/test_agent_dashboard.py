"""Task 81 (D-003): the agent command center. Every KPI is checked against a hand-computed dataset.

Dataset, one shop (runs and actions are inserted with known outcomes and ages):
  runs today:        ok, ok, failed                                -> 3 runs today, 1 failed
  run 3 days ago:    ok                                            -> 4 runs in the last 7 days
  run 10 days ago:   failed, ok                                    -> in the last 30 days, and the 7-day "previous" window
  actions (last 7d): executed, executed, failed, rejected          -> 3 approved of 4 decided = 75%
  action pending, action expired                                   -> not decided, left out of the rate
  time saved (7d):   3 ok runs x 2 min + 2 executed x 3 min        -> 12 minutes
  spend: 0.0445 USD this month on a 5.00 cap                       -> 0% (rounded down), shown as 0.04 of 5.00
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from tests.pg.agent_support import scripted_provider as scripted_provider  # noqa: F401  (autouse fixture)
from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg

URL = "/api/v1/agent-runs/dashboard"


async def _run(db: Any, tenant_id: uuid.UUID, outcome: str, days_ago: float, spend: int = 0) -> None:
    await db.execute(
        text(
            "INSERT INTO agent_runs (id, tenant_id, agent, session_id, input_text, output_text, trace_json, action_ids, "
            "outcome, tokens_in, tokens_out, spend_micros, duration_ms, created_at) "
            "VALUES (:id, :t, 'sales', 's', 'in', 'out', '[]', '[]', :o, 0, 0, :sp, 10, now() - make_interval(secs => :s))"
        ),
        {"id": uuid.uuid4(), "t": tenant_id, "o": outcome, "sp": spend, "s": days_ago * 86400},
    )


async def _action(db: Any, tenant_id: uuid.UUID, status: str, days_ago: float = 0.5) -> None:
    await db.execute(
        text(
            "INSERT INTO agent_actions (id, tenant_id, agent, tool, summary, payload_json, payload_hash, status, created_at, updated_at) "
            "VALUES (:id, :t, 'sales', 'post_order', 'x', '{}', 'h', :st, now() - make_interval(secs => :s), now())"
        ),
        {"id": uuid.uuid4(), "t": tenant_id, "st": status, "s": days_ago * 86400},
    )


async def seeded(owner: dict[str, Any]) -> None:
    tid = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tid) as db:
        for outcome in ("ok", "ok", "failed"):
            await _run(db, tid, outcome, 0.001, spend=10_000)
        await _run(db, tid, "ok", 3, spend=14_500)
        await _run(db, tid, "failed", 10)
        await _run(db, tid, "ok", 10)
        for status in ("executed", "executed", "failed", "rejected", "pending", "expired"):
            await _action(db, tid, status)


async def test_every_kpi_matches_the_hand_computed_value(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await seeded(owner)
    body = (await client.get(URL, params={"range": "7d"}, headers=bearer(owner))).json()
    assert body["range"] == "7d" and body["is_empty"] is False and body["enabled"] is True
    assert body["runs_today"] == 3
    assert (body["runs"]["value"], body["runs"]["previous"], body["runs"]["change_percent"]) == (4, 2, 100)
    assert (body["failed_runs"]["value"], body["failed_runs"]["previous"], body["failed_runs"]["change_percent"]) == (1, 1, 0)
    assert body["approval"] == {"approved": 3, "rejected": 1, "rate_percent": 75}
    assert body["time_saved"]["minutes"] == 3 * 2 + 2 * 3
    assert (body["time_saved"]["ok_runs"], body["time_saved"]["executed_actions"]) == (3, 2)
    assert "Estimate" in body["time_saved"]["assumption"]
    assert body["spend"] == {"month_spend_usd": "0.04", "month_cap_usd": "5.00", "percent_used": 0}


async def test_today_and_30_day_ranges_change_the_window(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await seeded(owner)
    today = (await client.get(URL, params={"range": "today"}, headers=bearer(owner))).json()
    assert today["runs"]["value"] == 3 and today["failed_runs"]["value"] == 1
    month = (await client.get(URL, params={"range": "30d"}, headers=bearer(owner))).json()
    assert month["runs"]["value"] == 6 and month["failed_runs"]["value"] == 2
    assert (await client.get(URL, params={"range": "yesterday"}, headers=bearer(owner))).status_code == 422


async def test_a_shop_that_never_ran_an_agent_gets_zeros_and_an_empty_flag(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    res = await client.get(URL, headers=bearer(owner))
    assert res.status_code == 200
    body = res.json()
    assert body["is_empty"] is True and body["runs"]["value"] == 0 and body["runs_today"] == 0
    assert body["approval"] == {"approved": 0, "rejected": 0, "rate_percent": None}
    assert body["time_saved"]["minutes"] == 0 and body["spend"]["percent_used"] == 0


async def test_owner_and_manager_can_open_it_staff_cannot(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    assert (await client.get(URL, headers=bearer(owner))).status_code == 200
    assert (await client.get(URL, headers=bearer(manager))).status_code == 200
    assert (await client.get(URL, headers=bearer(staff))).status_code == 403
    assert (await client.get(URL)).status_code == 401


async def test_a_shop_only_counts_its_own_runs(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await seeded(a)
    other = (await client.get(URL, params={"range": "30d"}, headers=bearer(b))).json()
    assert other["is_empty"] is True and other["runs"]["value"] == 0 and other["approval"]["rate_percent"] is None
