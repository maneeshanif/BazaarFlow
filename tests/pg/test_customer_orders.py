"""Customer order drafts (PRD W-003 step 2-3): a WhatsApp customer asks for products, the owner approves, the order posts."""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg
import pytest
from httpx import AsyncClient

from app.evals.replay import ReplayModel, ToolCall, Turn
from tests.pg.agent_support import scripted_provider, use_model  # noqa: F401  (autouse fixture + helper)
from tests.pg.channel_support import FakeProviders, connect_twilio, post_webhook, twilio_form
from tests.pg.conftest import bearer, register
from tests.pg.test_sales_api import product

pytestmark = pytest.mark.pg

APPROVALS = "/api/v1/approvals/"
ORDERS = "/api/v1/orders/"
CUSTOMERS = "/api/v1/customers/"


def ordering(product_id: str, qty: int, reply: str = "Thank you! The shop will confirm your order shortly.") -> ReplayModel:
    return ReplayModel(
        [
            Turn(tool_calls=[ToolCall("find_product", {"query": "shirt"})]),
            Turn(tool_calls=[ToolCall("request_order", {"items": [{"product_id": product_id, "qty": qty}]})]),
            Turn(text=reply),
        ]
    )


async def shop(client: AsyncClient, qty: int = 10) -> tuple[dict[str, Any], dict[str, Any]]:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    shirt = await product(client, owner, "SHIRT", "2500.00", qty, name="Classic Shirt", cost="1800.00")
    return owner, shirt


async def pending(client: AsyncClient, owner: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (await client.get(APPROVALS, params={"status": "pending"}, headers=bearer(owner))).json()["items"]
    return items


async def orders(client: AsyncClient, owner: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (await client.get(ORDERS, headers=bearer(owner))).json()["items"]
    return items


async def on_hand(client: AsyncClient, owner: dict[str, Any], item: dict[str, Any]) -> int:
    got: int = (await client.get(f"/api/v1/inventory/{item['id']}", headers=bearer(owner))).json()["qty_on_hand"]
    return got


async def test_a_customer_order_waits_for_approval_then_posts_on_credit_and_the_customer_is_told(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, shirt = await shop(client)
    use_model(monkeypatch, ordering(shirt["id"], 2))
    assert (await post_webhook(client, twilio_form(text="I want 2 classic shirts"))).status_code == 200

    waiting = await pending(client, owner)
    assert len(waiting) == 1 and waiting[0]["tool"] == "customer_order" and waiting[0]["agent"] == "customer"
    assert "2 x Classic Shirt" in waiting[0]["summary"] and "Sara" in waiting[0]["summary"] and "Rs 5,000" in waiting[0]["summary"]
    assert await orders(client, owner) == [] and await on_hand(client, owner, shirt) == 10  # nothing has changed yet
    assert len(providers.calls("twilio.send")) == 1  # only the AI's "the shop will confirm" reply so far

    approved = await client.post(f"{APPROVALS}{waiting[0]['id']}/approve", headers=bearer(owner))
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "executed"
    posted = await orders(client, owner)
    assert len(posted) == 1 and posted[0]["total"] == "5000.00" and posted[0]["channel"] == "whatsapp"
    assert await on_hand(client, owner, shirt) == 8

    made = (await client.get(CUSTOMERS, params={"q": "923001234567"}, headers=bearer(owner))).json()["items"]
    assert len(made) == 1 and made[0]["name"] == "Sara" and made[0]["balance"] == "5000.00"  # on credit until it is paid
    sent = providers.calls("twilio.send")
    assert len(sent) == 2 and b"confirmed" in sent[1].content and b"Rs+5%2C000" in sent[1].content


async def test_an_existing_customer_is_reused_and_a_rejected_order_posts_nothing(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, shirt = await shop(client)
    existing = await client.post(CUSTOMERS, json={"phone": "+923001234567", "name": "Sara Khan"}, headers=bearer(owner))
    assert existing.status_code == 201
    use_model(monkeypatch, ordering(shirt["id"], 1))
    await post_webhook(client, twilio_form(text="one shirt please"))
    waiting = await pending(client, owner)
    approved = await client.post(f"{APPROVALS}{waiting[0]['id']}/approve", headers=bearer(owner))
    assert approved.json()["status"] == "executed"
    listed = (await client.get(CUSTOMERS, headers=bearer(owner))).json()["items"]
    assert len(listed) == 1 and listed[0]["id"] == existing.json()["id"]  # not a second Sara

    use_model(monkeypatch, ordering(shirt["id"], 3))
    await post_webhook(client, twilio_form(text="three more please", sid="SM" + "2" * 32))
    second = (await pending(client, owner))[0]
    rejected = await client.post(f"{APPROVALS}{second['id']}/reject", json={"reason": "out of stock soon"}, headers=bearer(owner))
    assert rejected.status_code == 200
    assert len(await orders(client, owner)) == 1 and await on_hand(client, owner, shirt) == 9


async def test_more_than_the_shelf_holds_is_never_filed(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner, shirt = await shop(client, qty=3)
    use_model(monkeypatch, ordering(shirt["id"], 50, reply="Sorry, we only have 3 in stock."))
    await post_webhook(client, twilio_form(text="fifty shirts"))
    assert await pending(client, owner) == []
    assert await orders(client, owner) == []


async def test_stock_that_sold_out_before_approval_fails_the_order_with_a_reason(
    client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch, admin_conn: asyncpg.Connection
) -> None:
    owner, shirt = await shop(client)
    use_model(monkeypatch, ordering(shirt["id"], 5))
    await post_webhook(client, twilio_form(text="five shirts"))
    waiting = await pending(client, owner)
    await admin_conn.execute("UPDATE inventory_items SET qty_on_hand = 1 WHERE product_id = $1", uuid.UUID(shirt["id"]))
    result = await client.post(f"{APPROVALS}{waiting[0]['id']}/approve", headers=bearer(owner))
    assert result.status_code == 200 and result.json()["status"] == "failed"
    assert await orders(client, owner) == []
    assert len(providers.calls("twilio.send")) == 1  # the customer is not told "confirmed" for an order that did not post


async def test_another_shop_never_sees_the_request(client: AsyncClient, providers: FakeProviders, monkeypatch: pytest.MonkeyPatch) -> None:
    owner, shirt = await shop(client)
    other = await register(client, "Shop B")
    use_model(monkeypatch, ordering(shirt["id"], 1))
    await post_webhook(client, twilio_form(text="one shirt"))
    assert len(await pending(client, owner)) == 1
    assert await pending(client, other) == []
