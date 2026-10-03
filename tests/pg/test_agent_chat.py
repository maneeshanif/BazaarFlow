"""Tasks 37, 63, 64, 65 (and 29's runtime gate): the sales agent on the shop's own data, with approvals.

The scripted model drives the REAL tools, the REAL approval flow and the REAL database, so these tests prove the path a
shopkeeper takes: chat, draft, "yes", approval, stock and ledger, trace. What they cannot show is whether a live model
would choose the same tools; that needs a recorded run against the provider.
"""

from __future__ import annotations

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.settings import settings
from app.core.tenancy import tenant_session
from app.evals.replay import ToolCall, Turn
from tests.pg.agent_support import (
    APPROVALS,
    RUNS,
    FailingAfter,
    PricedReplay,
    propose_sale,
    say,
    shop,
    stock,
    use_model,
)
from tests.pg.agent_support import scripted_provider as scripted_provider  # noqa: F401  (autouse fixture)
from tests.pg.conftest import bearer, member, register
from tests.pg.test_sales_api import customer, product

pytestmark = pytest.mark.pg


async def test_a_chat_sale_waits_for_approval_then_posts_when_a_manager_approves(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")

    draft = await say(client, staff, "sell 2 classic shirt to ali")
    assert draft["outcome"] == "ok" and not draft["actions"]
    assert "Draft sale for Ali Raza" in draft["reply"] and "Rs 5,000.00" in draft["reply"] and "Post it?" in draft["reply"]

    sent = await say(client, staff, "yes")
    assert [a["status"] for a in sent["actions"]] == ["pending"] and sent["actions"][0]["tool"] == "post_order"
    assert "Sent for approval" in sent["reply"]
    assert await stock(client, owner, items["shirt"]) == 10, "nothing changes until it is approved"
    assert (await client.get("/api/v1/orders/", headers=bearer(owner))).json()["total"] == 0

    waiting = (await client.get(APPROVALS, params={"status": "pending"}, headers=bearer(manager))).json()
    assert waiting["total"] == 1
    card = waiting["items"][0]
    assert card["tool"] == "post_order" and card["requested_by_name"] and card["payload"]["items"][0]["qty"] == 2

    done = await client.post(f"{APPROVALS}{card['id']}/approve", headers=bearer(manager))
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "executed" and done.json()["executed_at"]
    assert await stock(client, owner, items["shirt"]) == 8
    orders = (await client.get("/api/v1/orders/", headers=bearer(owner))).json()
    assert orders["total"] == 1 and orders["items"][0]["channel"] == "chat" and orders["items"][0]["total"] == "5000.00"
    detail = (await client.get(f"/api/v1/orders/{orders['items'][0]['id']}", headers=bearer(owner))).json()
    assert detail["created_by"] is not None and detail["payments"][0]["amount"] == "5000.00"

    runs = (await client.get(RUNS, headers=bearer(manager))).json()
    assert runs["total"] == 2 and {r["outcome"] for r in runs["items"]} == {"ok"}


async def test_a_rejected_sale_never_happens(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    sent = await propose_sale(client, owner)
    rejected = await client.post(f"{APPROVALS}{sent['actions'][0]['id']}/reject", json={"reason": "Wrong customer"}, headers=bearer(owner))
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected" and rejected.json()["decision_note"] == "Wrong customer"
    assert await stock(client, owner, items["shirt"]) == 10
    assert (await client.get("/api/v1/orders/", headers=bearer(owner))).json()["total"] == 0
    assert (await client.post(f"{APPROVALS}{sent['actions'][0]['id']}/approve", headers=bearer(owner))).status_code == 409


async def test_roman_urdu_commands_are_understood_by_the_wiring(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    plain = await say(client, owner, "2 classic shirt bech do ali ko", "u1")
    assert "2" in plain["reply"] and "Rs 5,000.00" in plain["reply"] and "Ali Raza" in plain["reply"]
    credit = await say(client, owner, "1 classic shirt ali ko udhaar pe", "u2")
    assert "on credit Rs 2,500.00" in credit["reply"] and "Paid now Rs 0.00" in credit["reply"]


async def test_a_sale_cannot_be_posted_before_its_draft_was_shown(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    args = {"items": [{"product_id": items["shirt"]["id"], "qty": 1, "unit_price": None}], "customer_id": None, "payment_method": "cash", "amount_paid": None, "discount": None}
    use_model(monkeypatch, PricedReplay([Turn(tool_calls=[ToolCall("post_order", args)]), Turn(text="Done")]))
    reply = await say(client, owner, "post it now")
    assert reply["actions"] == []
    detail = (await client.get(f"{RUNS}{reply['run_id']}", headers=bearer(owner))).json()
    assert detail["trace"][0]["ok"] is False and "Draft this exact sale" in detail["trace"][0]["result"]
    assert (await client.get(APPROVALS, headers=bearer(owner))).json()["total"] == 0


async def test_the_permission_gate_runs_in_the_agent_so_staff_cannot_ask_for_manager_tools(
    client: AsyncClient, app_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    staff = await member(client, app_engine, owner, "staff")
    turns = [
        Turn(tool_calls=[ToolCall("record_payment", {"customer_id": items["ali"]["id"], "amount": "100", "method": "cash"})]),
        Turn(tool_calls=[ToolCall("get_profit", {"period": "today"})]),
        Turn(tool_calls=[ToolCall("adjust_stock", {"product_id": items["shirt"]["id"], "delta": 5, "reason": "adjustment", "note": None})]),
        Turn(text="I am not allowed to do those for you."),
    ]
    use_model(monkeypatch, PricedReplay(turns))
    reply = await say(client, staff, "pay, profit and add stock please")
    detail = (await client.get(f"{RUNS}{reply['run_id']}", headers=bearer(owner))).json()
    assert [(s["tool"], s["ok"]) for s in detail["trace"]] == [("record_payment", False), ("get_profit", False), ("adjust_stock", False)]
    assert all("Not allowed" in s["result"] for s in detail["trace"])
    assert reply["actions"] == [] and (await client.get(APPROVALS, headers=bearer(owner))).json()["total"] == 0


async def test_an_agent_cannot_reach_another_shops_products_or_customers(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    theirs = await shop(client, a)
    await product(client, b, "OWN", "10.00", 5)
    args = {"items": [{"product_id": theirs["shirt"]["id"], "qty": 1, "unit_price": None}], "customer_id": theirs["ali"]["id"], "payment_method": "cash", "amount_paid": None, "discount": None}
    use_model(monkeypatch, PricedReplay([Turn(tool_calls=[ToolCall("draft_order", args)]), Turn(text="That did not work.")]))
    reply = await say(client, b, "sell their shirt")
    detail = (await client.get(f"{RUNS}{reply['run_id']}", headers=bearer(b))).json()
    result = detail["trace"][0]["result"].lower()
    assert "not in your shop" in result or "not found" in result
    assert (await client.get(f"{RUNS}{reply['run_id']}", headers=bearer(a))).status_code == 404


async def test_the_owners_switch_stops_the_agent_before_any_tool_runs(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    manager = await member(client, app_engine, owner, "manager")
    assert (await client.put(f"{RUNS}switch", json={"enabled": False}, headers=bearer(manager))).status_code == 403
    off = await client.put(f"{RUNS}switch", json={"enabled": False}, headers=bearer(owner))
    assert off.status_code == 200 and off.json()["enabled"] is False

    paused = await say(client, manager, "sell 1 classic shirt")
    assert paused["outcome"] == "paused" and "paused" in paused["reply"] and paused["actions"] == []
    run = (await client.get(f"{RUNS}{paused['run_id']}", headers=bearer(owner))).json()
    assert run["trace"] == [], "no tool ran"

    on = await client.put(f"{RUNS}switch", json={"enabled": True}, headers=bearer(owner))
    assert on.json()["enabled"] is True
    assert (await say(client, manager, "sell 1 classic shirt"))["outcome"] == "ok"
    tenant_id = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tenant_id) as db:
        actions = set((await db.execute(text("SELECT action FROM audit_logs WHERE action LIKE 'agents.%'"))).scalars())
    assert actions == {"agents.switched_off", "agents.switched_on"}


async def test_the_platform_wide_switch_also_stops_every_shop(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    monkeypatch.setattr(settings, "AGENTS_ENABLED", False)
    assert (await say(client, owner, "sell 1 classic shirt"))["outcome"] == "paused"
    assert (await client.get(f"{RUNS}status", headers=bearer(owner))).json()["enabled"] is False


async def test_the_monthly_spend_cap_stops_runs_with_a_clear_message_and_warns_at_80_percent(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    monkeypatch.setattr(settings, "AGENT_MONTHLY_SPEND_CAP_USD", 0.0001)  # 100 micro-dollars; one scripted model call costs 28
    first = await say(client, owner, "sell 1 classic shirt", "c1")  # find, draft, answer: 3 calls = 84 micro-dollars
    assert first["outcome"] == "ok" and first["notice"] and "80%" in first["notice"]
    second = await say(client, owner, "sell 1 classic shirt", "c2")  # still under the cap when it starts, ends over it
    assert second["outcome"] == "ok"
    blocked = await say(client, owner, "sell 1 classic shirt", "c3")
    assert blocked["outcome"] == "spend_limit" and "allowance" in blocked["reply"]
    status = (await client.get(f"{RUNS}status", headers=bearer(owner))).json()
    assert status["percent_used"] >= 100 and status["runs_this_month"] == 3


async def test_a_run_that_needs_too_many_steps_stops_and_changes_nothing(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    monkeypatch.setattr(settings, "AGENT_MAX_TOOL_CALLS", 2)
    reply = await say(client, owner, "sell 2 classic shirt to ali")  # needs find, find, draft, answer: more than 3 turns
    assert reply["outcome"] == "step_limit" and "more steps" in reply["reply"] and reply["actions"] == []


async def test_a_provider_failure_after_a_proposal_rolls_the_proposal_back(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    await say(client, owner, "sell 1 classic shirt", "f1")  # drafts it with the scripted model
    args = {"items": [{"product_id": items["shirt"]["id"], "qty": 1, "unit_price": None}], "customer_id": None, "payment_method": "cash", "amount_paid": None, "discount": None}
    use_model(monkeypatch, FailingAfter([Turn(tool_calls=[ToolCall("post_order", args)])]))
    reply = await say(client, owner, "yes", "f1")
    assert reply["outcome"] == "failed" and "too long" in reply["reply"] and reply["actions"] == []
    assert (await client.get(APPROVALS, params={"status": "pending"}, headers=bearer(owner))).json()["total"] == 0, "no half-made approval"
    assert "Traceback" not in reply["reply"]


async def test_the_trace_holds_no_personal_data(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    pii = await client.post(
        "/api/v1/customers/",
        json={"phone": "+923009876543", "name": "Zainab Fixture", "email": "zainab.fixture@example.com", "address": "House 7 Gulberg"},
        headers=bearer(owner),
    )
    assert pii.status_code == 201
    await propose_sale(client, owner, "sell 1 classic shirt to zainab")
    await say(client, owner, "who is zainab fixture 0300 9876543 zainab.fixture@example.com", "p2")

    tenant_id = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tenant_id) as db:
        rows = (await db.execute(text("SELECT input_text || ' ' || output_text || ' ' || trace_json::text FROM agent_runs"))).scalars().all()
    blob = " ".join(rows).lower()
    assert blob.strip(), "runs were recorded"
    for secret in ("zainab", "fixture", "9876543", "zainab.fixture", "gulberg"):
        assert secret not in blob, f"'{secret}' leaked into the stored trace"
    assert "[customer]" in blob and "find_customer" in blob, "the trace still shows what happened, minus the person"

    listed = json.dumps((await client.get(RUNS, headers=bearer(owner))).json()).lower()
    assert "zainab" not in listed and "9876543" not in listed


async def test_every_agent_proposal_leaves_audit_rows(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    sent = await propose_sale(client, owner)
    await client.post(f"{APPROVALS}{sent['actions'][0]['id']}/approve", headers=bearer(owner))
    tenant_id = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tenant_id) as db:
        actions = [r[0] for r in (await db.execute(text("SELECT action FROM audit_logs ORDER BY created_at"))).all()]
    for expected in ("agent.action_requested", "agent.action_approved", "agent.action_executed", "order.posted", "stock.moved"):
        assert expected in actions, f"missing audit row {expected}"


async def test_two_identical_proposals_in_one_conversation_make_one_approval(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    await propose_sale(client, owner)
    again = await say(client, owner, "yes")  # the person says yes twice
    assert again["actions"] == [] and "Sent for approval" in again["reply"]
    assert (await client.get(APPROVALS, params={"status": "pending"}, headers=bearer(owner))).json()["total"] == 1


async def test_the_auto_post_limit_lets_small_sales_through_and_defaults_to_asking(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    asked = await propose_sale(client, owner, "sell 1 classic shirt", "d1")
    assert asked["actions"] and await stock(client, owner, items["shirt"]) == 10  # default limit 0: always ask

    from decimal import Decimal

    monkeypatch.setattr(settings, "AGENT_AUTO_POST_LIMIT", Decimal("3000"))
    await say(client, owner, "sell 1 classic shirt", "d2")
    posted = await say(client, owner, "yes", "d2")
    assert posted["actions"] == [] and "Posted" in posted["reply"]
    assert await stock(client, owner, items["shirt"]) == 9
    monkeypatch.setattr(settings, "AGENT_AUTO_POST_LIMIT", Decimal("1000"))
    over = await propose_sale(client, owner, "sell 2 classic shirt", "d3")  # Rs 5,000: above the limit of 1,000
    assert over["actions"], "a sale above the limit still waits for approval"


async def test_unknown_products_and_customers_are_explained(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    assert "could not find" in (await say(client, owner, "sell 1 unicorn saddle", "x1"))["reply"].lower()
    assert "customer" in (await say(client, owner, "sell 1 classic shirt to nobody", "x2"))["reply"].lower()


async def test_staff_see_prices_and_stock_but_the_agent_hides_cost_and_credit(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    staff = await member(client, app_engine, owner, "staff")
    await customer(client, owner, "+923001110099")
    reply = await say(client, staff, "sell 1 classic shirt to ali", "s9")
    detail = (await client.get(f"{RUNS}{reply['run_id']}", headers=bearer(owner))).json()
    blob = json.dumps(detail["trace"])
    assert "1800" not in blob, "staff never see cost, so neither does their agent"
    assert items["shirt"]["id"] in blob
