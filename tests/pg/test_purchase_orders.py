"""Draft purchase orders (PRD W-006 step 3): drafted beside the reorder message, sent with it, cancelled by a person."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.pg.agent_support import scripted_provider  # noqa: F401  (autouse fixture: the offline writer)
from tests.pg.channel_support import FakeProviders, connect_twilio
from tests.pg.conftest import bearer, member, register
from tests.pg.test_automations import enable, pending, run
from tests.pg.test_sales_api import product

pytestmark = pytest.mark.pg

PO = "/api/v1/purchase-orders/"


@pytest_asyncio.fixture(autouse=True)
async def clean_slate(admin_conn: asyncpg.Connection) -> None:
    await admin_conn.execute("DELETE FROM automations")
    await admin_conn.execute("DELETE FROM agent_actions WHERE tool = 'send_whatsapp_message'")


async def vendor(client: AsyncClient, owner: dict[str, Any], name: str = "Cloth House", phone: str | None = "+923009998888") -> dict[str, Any]:
    body: dict[str, Any] = {"name": name}
    if phone:
        body["phone"] = phone
    res = await client.post("/api/v1/vendors/", json=body, headers=bearer(owner))
    assert res.status_code == 201, res.text
    made: dict[str, Any] = res.json()
    return made


async def orders(client: AsyncClient, owner: dict[str, Any], **params: str) -> list[dict[str, Any]]:
    res = await client.get(PO, params=params, headers=bearer(owner))
    assert res.status_code == 200, res.text
    items: list[dict[str, Any]] = res.json()["items"]
    return items


async def test_low_stock_drafts_an_order_beside_the_message_and_sending_the_message_marks_it_sent(
    client: AsyncClient, providers: FakeProviders, admin_conn: asyncpg.Connection
) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    cloth = await vendor(client, owner)
    await product(client, owner, "SHIRT", "1000.00", 2, name="Classic Shirt", reorder_level=5, vendor_id=cloth["id"])
    await product(client, owner, "CAP", "500.00", 1, name="Cap", reorder_level=3, vendor_id=cloth["id"])
    await enable(client, owner, "low_stock_vendor_draft")

    await run(client, owner, "low_stock_vendor_draft")
    drafted = await orders(client, owner)
    assert len(drafted) == 1
    order = drafted[0]
    assert order["status"] == "drafted" and order["vendor_name"] == "Cloth House" and order["item_count"] == 2
    assert Decimal(order["total"]) == Decimal("780.00")  # (8 shirts + 5 caps) at the cost of 60.00 each

    waiting = await pending(client, owner)
    assert len(waiting) == 1 and order["action_id"] == waiting[0]["id"]
    await run(client, owner, "low_stock_vendor_draft")
    assert len(await orders(client, owner)) == 1  # the approval is still waiting: no second order

    detail = (await client.get(f"{PO}{order['id']}", headers=bearer(owner))).json()
    assert {i["name"]: i["qty"] for i in detail["items"]} == {"Classic Shirt": 8, "Cap": 5}

    approved = await client.post(f"/api/v1/approvals/{waiting[0]['id']}/approve", headers=bearer(owner))
    assert approved.status_code == 200, approved.text
    sent = (await client.get(f"{PO}{order['id']}", headers=bearer(owner))).json()
    assert sent["status"] == "sent" and sent["sent_at"] is not None
    actions = await admin_conn.fetch(
        "SELECT action FROM audit_logs WHERE entity = 'purchase_order' AND entity_id = $1 ORDER BY created_at", order["id"]
    )
    assert [a["action"] for a in actions] == ["purchase_order.drafted", "purchase_order.sent"]


async def test_a_vendor_without_a_phone_leaves_a_draft_with_no_message_and_is_drafted_only_once(client: AsyncClient, providers: FakeProviders) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    nophone = await vendor(client, owner, "Street Wholesaler", phone=None)
    await product(client, owner, "ROPE", "50.00", 0, name="Rope", reorder_level=2, vendor_id=nophone["id"])
    await enable(client, owner, "low_stock_vendor_draft")

    done = await run(client, owner, "low_stock_vendor_draft")
    assert "no vendor phone number" in done["summary"]
    drafted = await orders(client, owner)
    assert len(drafted) == 1 and drafted[0]["status"] == "drafted" and drafted[0]["vendor_has_phone"] is False
    assert drafted[0]["action_id"] is None and await pending(client, owner) == []
    await run(client, owner, "low_stock_vendor_draft")
    assert len(await orders(client, owner)) == 1


async def test_a_draft_can_be_cancelled_but_a_sent_order_cannot(client: AsyncClient, providers: FakeProviders, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    await connect_twilio(client, owner)
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    nophone = await vendor(client, owner, "Street Wholesaler", phone=None)
    await product(client, owner, "ROPE", "50.00", 0, name="Rope", reorder_level=2, vendor_id=nophone["id"])
    await enable(client, owner, "low_stock_vendor_draft")
    await run(client, owner, "low_stock_vendor_draft")
    order = (await orders(client, owner))[0]

    assert (await client.get(PO, headers=bearer(staff))).status_code == 403  # PRD role matrix: managers and up
    assert (await client.post(f"{PO}{order['id']}/cancel", headers=bearer(staff))).status_code == 403
    cancelled = await client.post(f"{PO}{order['id']}/cancel", headers=bearer(manager))
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    again = await client.post(f"{PO}{order['id']}/cancel", headers=bearer(owner))
    assert again.status_code == 409 and again.json()["code"] == "not_a_draft"
    assert [o["status"] for o in await orders(client, owner, status="cancelled")] == ["cancelled"]


async def test_a_shop_never_sees_another_shops_orders(client: AsyncClient, providers: FakeProviders) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    nophone = await vendor(client, a, "Street Wholesaler", phone=None)
    await product(client, a, "ROPE", "50.00", 0, name="Rope", reorder_level=2, vendor_id=nophone["id"])
    await enable(client, a, "low_stock_vendor_draft")
    await run(client, a, "low_stock_vendor_draft")
    order = (await orders(client, a))[0]

    assert await orders(client, b) == []
    assert (await client.get(f"{PO}{order['id']}", headers=bearer(b))).status_code == 404
    assert (await client.post(f"{PO}{order['id']}/cancel", headers=bearer(b))).status_code == 404
