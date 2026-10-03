"""Task 39: orders list and detail, and reversing a posted sale (PRD F-008, §13.2)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from tests.pg.conftest import bearer, member, register
from tests.pg.test_sales_api import SALES, STOCK, customer, product, qty, sale

pytestmark = pytest.mark.pg


async def reverse(client: AsyncClient, acct: dict[str, Any], order_id: str, reason: str = "Customer changed their mind") -> Any:
    return await client.post(f"/api/v1/orders/{order_id}/reverse", json={"reason": reason}, headers=bearer(acct))


async def test_reversing_a_cash_sale_puts_the_stock_back_and_keeps_the_history(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", "100.00", 10)
    order = (await client.post(SALES, json=sale([(p, 4)]), headers=bearer(acct))).json()
    assert await qty(client, acct, p) == 6

    res = await reverse(client, acct, order["id"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["status"], body["amount_paid"], body["amount_due"]) == ("reversed", "0.00", "0.00")
    assert body["payments"][0]["status"] == "reversed" and "Customer changed their mind" in body["note"]
    assert await qty(client, acct, p) == 10

    moves = (await client.get(f"{STOCK}{p['id']}/stock-movements", headers=bearer(acct))).json()["items"]
    assert [(m["delta"], m["reason"], m["ref_id"]) for m in moves[:2]] == [(4, "reversal", order["id"]), (-4, "sale", order["id"])]
    assert (await client.get("/api/v1/orders/", params={"status": "reversed"}, headers=bearer(acct))).json()["total"] == 1
    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as db:
        audit = (await db.execute(text("SELECT after_json->>'reason' FROM audit_logs WHERE action = 'order.reversed'"))).scalars().all()
    assert audit == ["Customer changed their mind"]


async def test_reversing_a_credit_sale_takes_it_off_the_customers_udhaar(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", "1000.00", 10)
    ali = await customer(client, acct)
    order = (await client.post(SALES, json=sale([(p, 2)], payment_method="udhaar", customer_id=ali["id"]), headers=bearer(acct))).json()
    assert (await client.get(f"/api/v1/customers/{ali['id']}", headers=bearer(acct))).json()["balance"] == "2000.00"
    assert (await reverse(client, acct, order["id"])).status_code == 200
    assert (await client.get(f"/api/v1/customers/{ali['id']}", headers=bearer(acct))).json()["balance"] == "0.00"
    ledger = (await client.get(f"/api/v1/customers/{ali['id']}/ledger", headers=bearer(acct))).json()["items"]
    assert [(e["direction"], e["amount"], e["balance_after"]) for e in ledger] == [("credit", "2000.00", "0.00"), ("debit", "2000.00", "2000.00")]


async def test_a_customer_who_already_paid_part_is_left_with_credit_after_a_reversal(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", "1000.00", 10)
    ali = await customer(client, acct)
    order = (await client.post(SALES, json=sale([(p, 1)], payment_method="udhaar", customer_id=ali["id"]), headers=bearer(acct))).json()
    await client.post(f"/api/v1/customers/{ali['id']}/payments", json={"amount": "400.00", "method": "cash"}, headers=bearer(acct))
    await reverse(client, acct, order["id"])
    # they paid 400 towards a sale that no longer exists: the shop now owes them that, shown as a negative balance
    assert (await client.get(f"/api/v1/customers/{ali['id']}", headers=bearer(acct))).json()["balance"] == "-400.00"


async def test_a_sale_can_only_be_reversed_once(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", qty=5)
    order = (await client.post(SALES, json=sale([(p, 2)]), headers=bearer(acct))).json()
    assert (await reverse(client, acct, order["id"])).status_code == 200
    again = await reverse(client, acct, order["id"])
    assert again.status_code == 422 and again.json()["code"] == "order_not_posted"
    assert await qty(client, acct, p) == 5, "the stock went back once, not twice"


async def test_two_simultaneous_reversals_reverse_once(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", qty=5)
    order = (await client.post(SALES, json=sale([(p, 2)]), headers=bearer(acct))).json()
    results = await asyncio.gather(*[reverse(client, acct, order["id"]) for _ in range(2)])
    assert sorted(r.status_code for r in results) == [200, 422]
    assert await qty(client, acct, p) == 5


async def test_the_reason_is_required_and_only_managers_may_reverse(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    p = await product(client, owner, "A", qty=9)
    order = (await client.post(SALES, json=sale([(p, 1)]), headers=bearer(staff))).json()
    assert (await reverse(client, staff, order["id"])).status_code == 403
    assert (await client.post(f"/api/v1/orders/{order['id']}/reverse", json={}, headers=bearer(manager))).status_code == 422
    assert (await reverse(client, manager, order["id"], reason="no")).status_code == 422
    assert (await reverse(client, manager, order["id"])).status_code == 200


async def test_another_shops_order_cannot_be_reversed(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    p = await product(client, a, "A", qty=5)
    order = (await client.post(SALES, json=sale([(p, 1)]), headers=bearer(a))).json()
    assert (await reverse(client, b, order["id"])).status_code == 404
    assert (await client.get(f"/api/v1/orders/{order['id']}", headers=bearer(a))).json()["status"] == "posted"
    assert await qty(client, a, p) == 4


async def test_a_reversed_sale_can_still_be_read_with_its_lines_and_payments(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    p = await product(client, acct, "A", "50.00", 5)
    order = (await client.post(SALES, json=sale([(p, 2)]), headers=bearer(acct))).json()
    await reverse(client, acct, order["id"])
    detail = (await client.get(f"/api/v1/orders/{order['id']}", headers=bearer(acct))).json()
    assert detail["status"] == "reversed" and detail["total"] == "100.00"
    assert [(i["product_name"], i["qty"], i["line_total"]) for i in detail["items"]] == [("Item A", 2, "100.00")]
