"""Tasks 74 and 80 (F-013, D-002): finance overview, cash book and the owner's finance dashboard.

Every KPI is checked against a hand-computed dataset, all in one shop (days are the shop's local days):
  order 1: 2 x Shirt (Rs 1,000, cost 600) cash, today              -> Rs 2,000, profit Rs 800
  order 2: 1 x Cap   (Rs 500, no cost) udhaar to Ali, today        -> Rs 500 on credit, profit unknown
  order 3: 1 x Shirt cash, 1 day ago                               -> Rs 1,000, profit Rs 400
  order 4: 3 x Shirt udhaar to Bina, 20 days ago                   -> Rs 3,000 on credit, profit Rs 1,200
  Bina pays Rs 1,000 today (clears her oldest credit first)        -> she still owes Rs 2,000, 20 days old
  vendor: bill Rs 5,000 due 10 days ago, Rs 1,000 paid today       -> owed Rs 4,000, all of it overdue
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import asyncpg
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from tests.pg.conftest import bearer, member, register
from tests.pg.test_sales_api import SALES, customer, product, sale

pytestmark = pytest.mark.pg

OVERVIEW = "/api/v1/finance/overview"
DASHBOARD = "/api/v1/finance/dashboard"
LEDGER = "/api/v1/finance/ledger"


async def _backdate(owner: dict[str, Any], admin: asyncpg.Connection, order_id: str, days: int) -> None:
    tenant_id = uuid.UUID(owner["tenant_id"])
    async with tenant_session(tenant_id) as db:
        await db.execute(text(f"UPDATE orders SET created_at = now() - interval '{days} days' WHERE id = :id"), {"id": order_id})
        await db.execute(text(f"UPDATE payments SET created_at = now() - interval '{days} days' WHERE order_id = :id"), {"id": order_id})
    # ledger entries are append-only for the application role, so the test moves them as the superuser
    await admin.execute(
        f"UPDATE ledger_entries SET created_at = now() - interval '{days} days' WHERE ref_id = $1", uuid.UUID(order_id)
    )


async def seeded(client: AsyncClient, owner: dict[str, Any], admin: asyncpg.Connection) -> None:
    shirt = await product(client, owner, "SHIRT", "1000.00", 50, name="Classic Shirt", cost="600.00")
    cap = await product(client, owner, "CAP", "500.00", 50, name="Cap", cost=None)
    ali = await customer(client, owner, "+923001110001")
    bina = (
        await client.post("/api/v1/customers/", json={"phone": "+923001110002", "name": "Bina"}, headers=bearer(owner))
    ).json()
    assert (await client.post(SALES, json=sale([(shirt, 2)]), headers=bearer(owner))).status_code == 201
    r2 = await client.post(SALES, json=sale([(cap, 1)], payment_method="udhaar", customer_id=ali["id"]), headers=bearer(owner))
    assert r2.status_code == 201, r2.text
    r3 = await client.post(SALES, json=sale([(shirt, 1)]), headers=bearer(owner))
    r4 = await client.post(SALES, json=sale([(shirt, 3)], payment_method="udhaar", customer_id=bina["id"]), headers=bearer(owner))
    assert r3.status_code == 201 and r4.status_code == 201
    await _backdate(owner, admin, r3.json()["id"], 1)
    await _backdate(owner, admin, r4.json()["id"], 20)
    pay = await client.post(f"/api/v1/customers/{bina['id']}/payments", json={"amount": "1000.00", "method": "cash"}, headers=bearer(owner))
    assert pay.status_code == 201, pay.text
    vendor = (await client.post("/api/v1/vendors/", json={"name": "Cloth House"}, headers=bearer(owner))).json()
    past = (date.today() - timedelta(days=10)).isoformat()
    await client.post(f"/api/v1/vendors/{vendor['id']}/bills", json={"amount": "5000.00", "due_date": past}, headers=bearer(owner))
    await client.post(f"/api/v1/vendors/{vendor['id']}/payments", json={"amount": "1000.00", "method": "bank"}, headers=bearer(owner))


async def test_every_kpi_matches_the_hand_computed_value(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    owner = await register(client, "Shop A")
    await seeded(client, owner, admin_conn)
    body = (await client.get(DASHBOARD, params={"range": "30d"}, headers=bearer(owner))).json()
    assert body["role"] == "owner" and body["range"] == "30d" and body["is_empty"] is False
    assert (body["revenue"]["value"], body["revenue"]["previous"], body["revenue"]["change_percent"]) == ("6500.00", "0.00", None)
    assert body["split"] == {"paid_now": "3000.00", "on_credit": "3500.00", "credit_percent": 54}
    assert body["gross_margin"] == {
        "margin_percent": 40,
        "profit": "2400.00",
        "revenue_counted": "6000.00",
        "orders_without_cost": 1,
    }
    assert body["payables"] == {"total": "4000.00", "overdue": "4000.00", "vendors": 1}
    assert body["receivables"]["total"] == "2500.00"
    assert [(b["label"], b["amount"], b["customers"]) for b in body["receivables"]["buckets"]] == [
        ("0 to 7 days", "500.00", 1),
        ("8 to 14 days", "0.00", 0),
        ("15 to 30 days", "2000.00", 1),
        ("Over 30 days", "0.00", 0),
    ]


async def test_the_trend_has_one_point_per_local_day_and_adds_up_to_revenue(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    owner = await register(client, "Shop A")
    await seeded(client, owner, admin_conn)
    week = (await client.get(OVERVIEW, params={"range": "7d"}, headers=bearer(owner))).json()
    assert len(week["trend"]) == 7 and [d["day"] for d in week["trend"]] == sorted(d["day"] for d in week["trend"])
    assert [(d["revenue"], d["orders"]) for d in week["trend"][-2:]] == [("1000.00", 1), ("2500.00", 2)]
    assert week["revenue"]["value"] == "3500.00"  # the 20-day-old order is outside a 7-day window
    month = (await client.get(OVERVIEW, params={"range": "30d"}, headers=bearer(owner))).json()
    assert len(month["trend"]) == 30
    assert sum(float(d["revenue"]) for d in month["trend"]) == 6500.0


async def test_the_cash_book_lists_money_in_and_out_newest_first(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    owner = await register(client, "Shop A")
    await seeded(client, owner, admin_conn)
    book = (await client.get(LEDGER, headers=bearer(owner))).json()
    assert book["total"] == 4
    created = [e["created_at"] for e in book["items"]]
    assert created == sorted(created, reverse=True)
    kinds = sorted((e["direction"], e["kind"], e["amount"]) for e in book["items"])
    assert kinds == [
        ("in", "sale_payment", "1000.00"),
        ("in", "sale_payment", "2000.00"),
        ("in", "udhaar_payment", "1000.00"),
        ("out", "vendor_payment", "1000.00"),
    ]
    only_out = (await client.get(LEDGER, params={"direction": "out"}, headers=bearer(owner))).json()
    assert only_out["total"] == 1 and only_out["items"][0]["kind"] == "vendor_payment"
    future = (await client.get(LEDGER, params={"since": "2999-01-01T00:00:00Z"}, headers=bearer(owner))).json()
    assert future["total"] == 0
    page = (await client.get(LEDGER, params={"limit": 3}, headers=bearer(owner))).json()
    assert len(page["items"]) == 3 and page["next_cursor"]
    assert (await client.get(LEDGER, params={"direction": "sideways"}, headers=bearer(owner))).status_code == 422


async def test_a_manager_sees_no_margin_or_payables_and_cannot_open_the_owner_dashboard(
    client: AsyncClient, app_engine: AsyncEngine, admin_conn: asyncpg.Connection
) -> None:
    owner = await register(client, "Shop A")
    await seeded(client, owner, admin_conn)
    manager = await member(client, app_engine, owner, "manager")
    body = (await client.get(OVERVIEW, headers=bearer(manager))).json()
    assert body["role"] == "manager" and body["gross_margin"] is None and body["payables"] is None
    assert body["revenue"]["value"] == "6500.00" and body["receivables"]["total"] == "2500.00"
    assert (await client.get(DASHBOARD, headers=bearer(manager))).status_code == 403
    assert (await client.get(LEDGER, headers=bearer(manager))).status_code == 200


async def test_staff_cannot_open_any_finance_endpoint(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    staff = await member(client, app_engine, owner, "staff")
    for url in (OVERVIEW, DASHBOARD, LEDGER):
        assert (await client.get(url, headers=bearer(staff))).status_code == 403
        assert (await client.get(url)).status_code == 401


async def test_an_empty_shop_shows_zeros_and_an_empty_flag_not_an_error(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    res = await client.get(DASHBOARD, headers=bearer(owner))
    assert res.status_code == 200
    body = res.json()
    assert body["is_empty"] is True
    assert (body["revenue"]["value"], body["split"]["credit_percent"], body["receivables"]["total"]) == ("0.00", None, "0.00")
    assert body["gross_margin"]["margin_percent"] is None and body["payables"]["total"] == "0.00"
    assert (await client.get(LEDGER, headers=bearer(owner))).json() == {"items": [], "total": 0, "next_cursor": None}


async def test_a_shop_only_sees_its_own_money(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await seeded(client, a, admin_conn)
    other = (await client.get(DASHBOARD, headers=bearer(b))).json()
    assert other["is_empty"] is True and other["revenue"]["value"] == "0.00"
    assert (await client.get(LEDGER, headers=bearer(b))).json()["total"] == 0


async def test_an_unknown_range_is_a_422(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    assert (await client.get(OVERVIEW, params={"range": "yesterday"}, headers=bearer(owner))).status_code == 422
