"""Task 72 (F-011): the shop-wide stock movements list: roles, filters, tenant isolation."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg

INV = "/api/v1/inventory/"
LIST = "/api/v1/inventory/movements"


async def _product(client: AsyncClient, acct: dict[str, Any], sku: str, qty: int = 5) -> dict[str, Any]:
    res = await client.post(INV, json={"sku": sku, "name": f"Item {sku}", "price": "100.00", "qty_on_hand": qty}, headers=bearer(acct))
    assert res.status_code == 201, res.text
    body: dict[str, Any] = res.json()
    return body


async def test_lists_every_movement_of_the_shop_newest_first_with_product_names(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    a = await _product(client, acct, "A-1")
    b = await _product(client, acct, "B-1")
    await client.post(f"{INV}{a['id']}/stock-movements", json={"delta": 3, "reason": "purchase"}, headers=bearer(acct))
    res = await client.get(LIST, headers=bearer(acct))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["items"][0]["reason"] == "purchase" and body["items"][0]["sku"] == "A-1"
    assert {i["product_name"] for i in body["items"]} == {"Item A-1", "Item B-1"}
    assert b["id"] in {i["product_id"] for i in body["items"]}


async def test_filters_by_product_reason_and_date(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    a = await _product(client, acct, "A-1")
    await _product(client, acct, "B-1")
    await client.post(f"{INV}{a['id']}/stock-movements", json={"delta": -1, "reason": "adjustment"}, headers=bearer(acct))
    by_product = (await client.get(LIST, params={"product_id": a["id"]}, headers=bearer(acct))).json()
    assert by_product["total"] == 2
    by_reason = (await client.get(LIST, params={"reason": "adjustment"}, headers=bearer(acct))).json()
    assert by_reason["total"] == 1 and by_reason["items"][0]["delta"] == -1
    future = (await client.get(LIST, params={"since": "2999-01-01T00:00:00Z"}, headers=bearer(acct))).json()
    assert future["total"] == 0 and future["items"] == []
    bad = await client.get(LIST, params={"reason": "theft"}, headers=bearer(acct))
    assert bad.status_code == 422


async def test_pagination_walks_all_rows(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    for n in range(3):
        await _product(client, acct, f"P-{n}")
    first = (await client.get(LIST, params={"limit": 2}, headers=bearer(acct))).json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    second = (await client.get(LIST, params={"limit": 2, "cursor": first["next_cursor"]}, headers=bearer(acct))).json()
    assert len(second["items"]) == 1 and second["next_cursor"] is None


async def test_staff_get_403_and_another_shop_sees_nothing(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    other = await register(client, "Shop B")
    await _product(client, owner, "A-1")
    staff = await member(client, app_engine, owner, "staff")
    assert (await client.get(LIST, headers=bearer(staff))).status_code == 403
    assert (await client.get(LIST, headers=bearer(other))).json()["total"] == 0
    manager = await member(client, app_engine, owner, "manager")
    assert (await client.get(LIST, headers=bearer(manager))).status_code == 200
