"""Tasks 36 and 48: the home dashboard (PRD F-004, D-001). Every figure is checked against a hand-computed dataset.

Dataset (today unless noted), all in one shop:
  order 1: 2 x Shirt (Rs 1,000, cost 600) cash            -> Rs 2,000, profit Rs 800
  order 2: 1 x Cap   (Rs 500, no cost, reorder at 5) udhaar to Ali -> Rs 500, no profit known; Cap stock 4, low
  order 3: 1 x Shirt cash, made yesterday                 -> Rs 1,000, profit Rs 400
  one sales approval waiting (from the chat)
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from tests.pg.agent_support import propose_sale
from tests.pg.agent_support import scripted_provider as scripted_provider  # noqa: F401  (autouse fixture)
from tests.pg.conftest import bearer, member, register
from tests.pg.test_sales_api import SALES, customer, product, sale

pytestmark = pytest.mark.pg

SUMMARY = "/api/v1/dashboard/summary"


async def seeded(client: AsyncClient, owner: dict[str, Any], engine: AsyncEngine) -> None:
    shirt = await product(client, owner, "SHIRT", "1000.00", 20, name="Classic Shirt", cost="600.00")
    cap = await product(client, owner, "CAP", "500.00", 5, name="Cap", cost=None, reorder_level=5)
    ali = await customer(client, owner, "+923001110001")
    assert (await client.post(SALES, json=sale([(shirt, 2)]), headers=bearer(owner))).status_code == 201
    assert (
        await client.post(
            SALES, json=sale([(cap, 1)], payment_method="udhaar", customer_id=ali["id"]), headers=bearer(owner)
        )
    ).status_code == 201
    old = await client.post(SALES, json=sale([(shirt, 1)]), headers=bearer(owner))
    assert old.status_code == 201
    async with tenant_session(uuid.UUID(owner["tenant_id"])) as db:
        await db.execute(
            text("UPDATE orders SET created_at = now() - interval '1 day' WHERE id = :id"), {"id": old.json()["id"]}
        )
    await propose_sale(client, owner, "sell 1 classic shirt to ali")


async def test_every_card_matches_the_hand_computed_value(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    await seeded(client, owner, app_engine)
    body = (await client.get(SUMMARY, headers=bearer(owner))).json()
    assert body["role"] == "owner" and body["range"] == "today"
    assert (body["sales"]["value"], body["sales"]["previous"], body["sales"]["change_percent"]) == (
        "2500.00",
        "1000.00",
        150,
    )
    assert (body["orders"]["value"], body["orders"]["previous"], body["orders"]["change_percent"]) == (2, 1, 100)
    assert (body["profit"]["value"], body["profit"]["previous"], body["profit"]["change_percent"]) == (
        "800.00",
        "400.00",
        100,
    )
    assert body["profit"]["orders_without_cost"] == 1
    assert body["low_stock"] == 1
    assert body["unpaid_udhaar"] == "500.00"
    assert body["approvals_waiting"] == 1
    assert body["briefing"] == (
        "Today you made Rs 2,500 from 2 orders, up 150% on the period before. 1 item is low on stock. "
        "Customers owe Rs 500 in total; Ali owes the most, Rs 500. 1 request is waiting for your approval."
    )


async def test_the_trend_has_seven_local_days_oldest_first(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    await seeded(client, owner, app_engine)
    trend = (await client.get(SUMMARY, headers=bearer(owner))).json()["trend"]
    assert len(trend) == 7 and [d["day"] for d in trend] == sorted(d["day"] for d in trend)
    assert [(d["total"], d["orders"]) for d in trend[-2:]] == [("1000.00", 1), ("2500.00", 2)]
    assert all((d["total"], d["orders"]) == ("0.00", 0) for d in trend[:5])


async def test_the_ranges_change_the_window_and_the_comparison(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    await seeded(client, owner, app_engine)
    week = (await client.get(SUMMARY, params={"range": "7d"}, headers=bearer(owner))).json()
    assert (week["sales"]["value"], week["orders"]["value"], week["sales"]["change_percent"]) == ("3500.00", 3, None)
    month = (await client.get(SUMMARY, params={"range": "30d"}, headers=bearer(owner))).json()
    assert month["range"] == "30d" and month["sales"]["value"] == "3500.00"
    assert (await client.get(SUMMARY, params={"range": "yesterday"}, headers=bearer(owner))).status_code == 422


async def test_staff_never_see_profit_udhaar_approvals_or_the_briefing(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    owner = await register(client, "Shop A")
    await seeded(client, owner, app_engine)
    staff = await member(client, app_engine, owner, "staff")
    body = (await client.get(SUMMARY, headers=bearer(staff))).json()
    assert (
        body["role"] == "staff"
        and body["sales"]["value"] == "2500.00"
        and body["orders"]["value"] == 2
        and body["low_stock"] == 1
    )
    assert (body["profit"], body["unpaid_udhaar"], body["approvals_waiting"], body["briefing"]) == (
        None,
        None,
        None,
        None,
    )
    assert "600" not in (await client.get(SUMMARY, headers=bearer(staff))).text


async def test_a_manager_sees_the_owner_view(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    await seeded(client, owner, app_engine)
    manager = await member(client, app_engine, owner, "manager")
    body = (await client.get(SUMMARY, headers=bearer(manager))).json()
    assert body["role"] == "manager" and body["profit"]["value"] == "800.00" and body["briefing"]


async def test_an_empty_shop_shows_zeros_and_a_plain_briefing_not_an_error(client: AsyncClient) -> None:
    owner = await register(client, "Shop A")
    res = await client.get(SUMMARY, headers=bearer(owner))
    assert res.status_code == 200
    body = res.json()
    assert (body["sales"]["value"], body["sales"]["change_percent"], body["orders"]["value"], body["low_stock"]) == (
        "0.00",
        None,
        0,
        0,
    )
    assert (body["profit"]["value"], body["unpaid_udhaar"], body["approvals_waiting"]) == ("0.00", "0.00", 0)
    assert body["briefing"] == "Today there are no sales yet."
    assert len(body["trend"]) == 7 and all(d["orders"] == 0 for d in body["trend"])


async def test_figures_never_cross_shops_and_the_route_needs_a_login(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    a, b = await register(client, "Shop A"), await register(client, "Shop B")
    await seeded(client, a, app_engine)
    other = (await client.get(SUMMARY, headers=bearer(b))).json()
    assert (
        other["sales"]["value"],
        other["orders"]["value"],
        other["low_stock"],
        other["unpaid_udhaar"],
        other["approvals_waiting"],
    ) == ("0.00", 0, 0, "0.00", 0)
    assert (await client.get(SUMMARY)).status_code == 401
