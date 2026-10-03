"""Task 44: the approvals center (PRD F-021): list, approve, reject, edit; roles; the payload hash; failures."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from app.evals.replay import ToolCall, Turn
from tests.pg.agent_support import APPROVALS, PricedReplay, propose_sale, say, shop, stock, use_model
from tests.pg.agent_support import scripted_provider as scripted_provider  # noqa: F401  (autouse fixture)
from tests.pg.conftest import bearer, member, register
from tests.pg.test_sales_api import SALES, sale

pytestmark = pytest.mark.pg


async def pending(client: AsyncClient, acct: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (await client.get(APPROVALS, params={"status": "pending"}, headers=bearer(acct))).json()["items"]
    return items


async def test_only_owners_and_managers_see_and_decide_approvals(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    staff = await member(client, app_engine, owner, "staff")
    sent = await propose_sale(client, staff)
    aid = sent["actions"][0]["id"]
    assert (await client.get(APPROVALS, headers=bearer(staff))).status_code == 403
    assert (await client.get(f"{APPROVALS}{aid}", headers=bearer(staff))).status_code == 403
    assert (await client.post(f"{APPROVALS}{aid}/approve", headers=bearer(staff))).status_code == 403
    assert (await client.post(f"{APPROVALS}{aid}/reject", json={"reason": "no"}, headers=bearer(staff))).status_code == 403
    assert (await client.patch(f"{APPROVALS}{aid}", json={"payload": {}}, headers=bearer(staff))).status_code == 403
    assert (await client.get(APPROVALS)).status_code == 401
    assert len(await pending(client, owner)) == 1


async def test_listing_filters_pages_and_isolates_shops(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await shop(client, a)
    for i in range(3):
        await propose_sale(client, a, f"sell {i + 1} classic shirt", f"s{i}")
    first = (await client.get(APPROVALS, params={"limit": 2}, headers=bearer(a))).json()
    assert first["total"] == 3 and len(first["items"]) == 2 and first["next_cursor"]
    rest = (await client.get(APPROVALS, params={"limit": 2, "cursor": first["next_cursor"]}, headers=bearer(a))).json()
    assert len(rest["items"]) == 1
    assert (await client.get(APPROVALS, params={"status": "bogus"}, headers=bearer(a))).status_code == 422
    assert (await client.get(APPROVALS, headers=bearer(b))).json()["total"] == 0
    other = first["items"][0]["id"]
    for call in (client.get(f"{APPROVALS}{other}", headers=bearer(b)), client.post(f"{APPROVALS}{other}/approve", headers=bearer(b))):
        assert (await call).status_code == 404


async def test_approving_twice_runs_it_once(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    sent = await propose_sale(client, owner)
    aid = sent["actions"][0]["id"]
    assert (await client.post(f"{APPROVALS}{aid}/approve", headers=bearer(owner))).status_code == 200
    again = await client.post(f"{APPROVALS}{aid}/approve", headers=bearer(owner))
    assert again.status_code == 409 and "executed" in again.json()["detail"]
    assert await stock(client, owner, items["shirt"]) == 8
    assert (await client.get("/api/v1/orders/", headers=bearer(owner))).json()["total"] == 1


async def test_rejecting_needs_a_reason_and_is_final(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    aid = (await propose_sale(client, owner))["actions"][0]["id"]
    assert (await client.post(f"{APPROVALS}{aid}/reject", json={}, headers=bearer(owner))).status_code == 422
    assert (await client.post(f"{APPROVALS}{aid}/reject", json={"reason": "no"}, headers=bearer(owner))).status_code == 422
    assert (await client.post(f"{APPROVALS}{aid}/reject", json={"reason": "Not today"}, headers=bearer(owner))).status_code == 200
    assert (await client.post(f"{APPROVALS}{aid}/reject", json={"reason": "Again"}, headers=bearer(owner))).status_code == 409
    assert (await client.patch(f"{APPROVALS}{aid}", json={"payload": {}}, headers=bearer(owner))).status_code == 409


async def test_an_unanswered_request_expires_and_cannot_be_approved(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    aid = (await propose_sale(client, owner))["actions"][0]["id"]
    tenant_id = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tenant_id) as db:
        await db.execute(text("UPDATE agent_actions SET expires_at = now() - interval '1 hour'"))
    listed = (await client.get(APPROVALS, headers=bearer(owner))).json()["items"][0]
    assert listed["status"] == "expired"
    assert (await client.post(f"{APPROVALS}{aid}/approve", headers=bearer(owner))).status_code == 409
    assert await stock(client, owner, items["shirt"]) == 10


async def test_editing_changes_what_runs_and_what_was_approved_is_what_runs(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    aid = (await propose_sale(client, owner))["actions"][0]["id"]
    card = (await client.get(f"{APPROVALS}{aid}", headers=bearer(owner))).json()
    edited_payload = {**card["payload"], "items": [{**card["payload"]["items"][0], "qty": 1}]}
    edited = await client.patch(f"{APPROVALS}{aid}", json={"payload": edited_payload}, headers=bearer(owner))
    assert edited.status_code == 200 and edited.json()["payload"]["items"][0]["qty"] == 1 and edited.json()["status"] == "pending"
    assert (await client.post(f"{APPROVALS}{aid}/approve", headers=bearer(owner))).json()["status"] == "executed"
    assert await stock(client, owner, items["shirt"]) == 9, "one shirt, the edited quantity"
    tenant_id = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tenant_id) as db:
        actions = set((await db.execute(text("SELECT action FROM audit_logs"))).scalars())
    assert "agent.action_edited" in actions


async def test_an_edit_must_pass_the_same_checks_as_a_new_request(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    await shop(client, owner)
    aid = (await propose_sale(client, owner))["actions"][0]["id"]
    payload = (await client.get(f"{APPROVALS}{aid}", headers=bearer(owner))).json()["payload"]
    too_many = await client.patch(f"{APPROVALS}{aid}", json={"payload": {**payload, "items": [{**payload["items"][0], "qty": 999}]}}, headers=bearer(owner))
    assert too_many.status_code == 422 and "Not enough stock" in too_many.json()["detail"]
    junk = await client.patch(f"{APPROVALS}{aid}", json={"payload": {"items": []}}, headers=bearer(owner))
    assert junk.status_code == 422
    assert (await client.get(f"{APPROVALS}{aid}", headers=bearer(owner))).json()["payload"] == payload, "a refused edit changes nothing"


async def test_an_approval_that_the_rules_now_refuse_fails_without_changing_anything(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    aid = (await propose_sale(client, owner))["actions"][0]["id"]  # asks for 2 of 10
    sold_out = await client.post(SALES, json=sale([(items["shirt"], 9)]), headers=bearer(owner))  # someone sells 9 meanwhile
    assert sold_out.status_code == 201
    result = await client.post(f"{APPROVALS}{aid}/approve", headers=bearer(owner))
    assert result.status_code == 200 and result.json()["status"] == "failed"
    assert "enough stock" in (result.json()["decision_note"] or "").lower()
    assert await stock(client, owner, items["shirt"]) == 1
    assert (await client.get("/api/v1/orders/", headers=bearer(owner))).json()["total"] == 1, "only the manual sale exists"


async def test_a_payload_changed_behind_the_scenes_is_refused(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    aid = (await propose_sale(client, owner))["actions"][0]["id"]
    tenant_id = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tenant_id) as db:
        await db.execute(text("UPDATE agent_actions SET payload_json = jsonb_set(payload_json::jsonb, '{items,0,qty}', '9')::json"))
    result = await client.post(f"{APPROVALS}{aid}/approve", headers=bearer(owner))
    assert result.status_code == 409 and "no longer matches" in result.json()["detail"]
    assert await stock(client, owner, items["shirt"]) == 10


async def test_a_payment_and_a_stock_correction_go_through_the_same_approval(
    client: AsyncClient, app_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    manager = await member(client, app_engine, owner, "manager")
    await client.post(SALES, json=sale([(items["shirt"], 1)], payment_method="udhaar", customer_id=items["ali"]["id"]), headers=bearer(owner))
    turns = [
        Turn(tool_calls=[ToolCall("record_payment", {"customer_id": items["ali"]["id"], "amount": "1000", "method": "cash"})]),
        Turn(tool_calls=[ToolCall("adjust_stock", {"product_id": items["shirt"]["id"], "delta": 5, "reason": "purchase", "note": "Restock"})]),
        Turn(text="Both sent for approval."),
    ]
    use_model(monkeypatch, PricedReplay(turns))
    reply = await say(client, manager, "ali paid 1000 and add 5 shirts")
    assert [a["tool"] for a in reply["actions"]] == ["record_payment", "adjust_stock"]
    assert await stock(client, owner, items["shirt"]) == 9 and (await client.get(f"/api/v1/customers/{items['ali']['id']}", headers=bearer(owner))).json()["balance"] == "2500.00"

    for action in reply["actions"]:
        done = await client.post(f"{APPROVALS}{action['id']}/approve", headers=bearer(owner))
        assert done.status_code == 200 and done.json()["status"] == "executed", done.text
    assert await stock(client, owner, items["shirt"]) == 14
    assert (await client.get(f"/api/v1/customers/{items['ali']['id']}", headers=bearer(owner))).json()["balance"] == "1500.00"
    moves = (await client.get(f"/api/v1/inventory/{items['shirt']['id']}/stock-movements", headers=bearer(owner))).json()["items"]
    assert moves[0]["actor_type"] == "agent" and moves[0]["reason"] == "purchase"


async def test_each_approval_explains_itself_in_plain_words(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = await register(client, "Shop A")
    items = await shop(client, owner)
    sale_card = (await propose_sale(client, owner))["actions"][0]["id"]
    card = (await client.get(f"{APPROVALS}{sale_card}", headers=bearer(owner))).json()
    assert card["details"][0] == "2 x Classic Shirt" and card["details"][1] == "Customer: Ali Raza"
    assert "Total Rs 5,000.00" in card["details"][2] and "paid now Rs 5,000.00 by cash" in card["details"][2]

    await client.post(SALES, json=sale([(items["shirt"], 1)], payment_method="udhaar", customer_id=items["ali"]["id"]), headers=bearer(owner))
    turns = [
        Turn(tool_calls=[ToolCall("record_payment", {"customer_id": items["ali"]["id"], "amount": "1000", "method": "cash"})]),
        Turn(tool_calls=[ToolCall("adjust_stock", {"product_id": items["shirt"]["id"], "delta": 5, "reason": "purchase", "note": None})]),
        Turn(text="sent"),
    ]
    use_model(monkeypatch, PricedReplay(turns))
    reply = await say(client, owner, "pay and restock", "x9")
    texts = [(await client.get(f"{APPROVALS}{a['id']}", headers=bearer(owner))).json()["details"][0] for a in reply["actions"]]
    assert texts == ["Rs 1,000.00 (cash) from Ali Raza", "Classic Shirt: +5 (purchase); 9 in stock now"]
