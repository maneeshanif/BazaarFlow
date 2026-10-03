"""Tasks 55 and 41: the products + stock resource end to end (PRD F-010): validation, roles, pagination, error shape."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.tenancy import tenant_session
from tests.pg.conftest import bearer, member, register

pytestmark = pytest.mark.pg

URL = "/api/v1/inventory/"


def product(sku: str = "SKU-1", **over: object) -> dict[str, object]:
    return {"sku": sku, "name": "Classic Shirt", "price": "2500.00", "cost": "1800.00", "qty_on_hand": 10, **over}


async def test_create_returns_the_product_with_stock_and_writes_movement_and_audit(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    res = await client.post(URL, json=product(reorder_level=3), headers=bearer(acct))
    assert res.status_code == 201, res.text
    body = res.json()
    assert (body["sku"], body["price"], body["cost"], body["qty_on_hand"], body["reorder_level"]) == (
        "SKU-1",
        "2500.00",
        "1800.00",
        10,
        3,
    )
    assert body["low_stock"] is False and body["active"] is True

    moves = (await client.get(f"{URL}{body['id']}/stock-movements", headers=bearer(acct))).json()
    assert moves["total"] == 1
    assert (moves["items"][0]["delta"], moves["items"][0]["reason"]) == (10, "opening")

    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as session:
        actions = set(
            (
                await session.execute(text("SELECT action FROM audit_logs WHERE tenant_id = :t"), {"t": tenant_id})
            ).scalars()
        )
    assert {"product.created", "stock.moved"} <= actions


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("price", "-1"),
        ("price", "abc"),
        ("price", "1.234"),
        ("sku", ""),
        ("sku", "x" * 41),
        ("name", "a"),
        ("name", "n" * 121),
        ("qty_on_hand", -1),
        ("reorder_level", -5),
    ],
)
async def test_invalid_input_is_a_422_problem_with_the_field_named(
    client: AsyncClient, field: str, value: object
) -> None:
    acct = await register(client, "Shop A")
    res = await client.post(URL, json={**product(), field: value}, headers=bearer(acct))
    assert res.status_code == 422
    body = res.json()
    assert res.headers["content-type"].startswith("application/problem+json")
    assert body["status"] == 422 and body["code"] == "validation_failed" and body["request_id"]
    assert field in {e["field"] for e in body["errors"]}


async def test_a_missing_required_field_is_reported_per_field(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    res = await client.post(URL, json={"name": "No sku or price"}, headers=bearer(acct))
    assert res.status_code == 422
    assert {"sku", "price"} <= {e["field"] for e in res.json()["errors"]}


async def test_the_same_sku_twice_is_a_409_with_a_stable_code(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    await client.post(URL, json=product(), headers=bearer(acct))
    res = await client.post(URL, json=product(), headers=bearer(acct))
    assert res.status_code == 409
    assert res.json()["code"] == "duplicate_sku" and "SKU-1" in res.json()["detail"]


async def test_roles_owner_manager_staff(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    manager = await member(client, app_engine, owner, "manager")
    staff = await member(client, app_engine, owner, "staff")
    made = (await client.post(URL, json=product(), headers=bearer(manager))).json()
    pid = made["id"]
    assert (await client.post(URL, json=product("SKU-2"), headers=bearer(staff))).status_code == 403
    assert (await client.patch(f"{URL}{pid}", json={"name": "Renamed"}, headers=bearer(staff))).status_code == 403
    movement = {"delta": 1, "reason": "purchase"}
    assert (await client.post(f"{URL}{pid}/stock-movements", json=movement, headers=bearer(staff))).status_code == 403
    assert (await client.get(f"{URL}{pid}/stock-movements", headers=bearer(staff))).status_code == 403
    assert (
        await client.delete(f"{URL}{pid}", headers=bearer(manager))
    ).status_code == 403  # PRD 14.2: only the owner deletes
    assert (await client.patch(f"{URL}{pid}", json={"name": "Renamed"}, headers=bearer(manager))).status_code == 200
    assert (await client.delete(f"{URL}{pid}", headers=bearer(owner))).status_code == 204
    assert (await client.get(URL)).status_code == 401


async def test_staff_can_view_stock_but_never_sees_cost(client: AsyncClient, app_engine: AsyncEngine) -> None:
    owner = await register(client, "Shop A")
    staff = await member(client, app_engine, owner, "staff")
    await client.post(URL, json=product(), headers=bearer(owner))
    item = (await client.get(URL, headers=bearer(staff))).json()["items"][0]
    assert item["cost"] is None and item["price"] == "2500.00" and item["qty_on_hand"] == 10


async def test_pagination_sorting_and_search(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    for i, price in enumerate(["30.00", "10.00", "50.00", "20.00", "40.00"]):
        body = product(f"P-{i}", name=f"Item {i}", price=price, reorder_level=5, qty_on_hand=i)
        await client.post(URL, json=body, headers=h)

    first = (await client.get(URL, params={"limit": 2, "sort": "-price"}, headers=h)).json()
    assert [p["price"] for p in first["items"]] == ["50.00", "40.00"] and first["total"] == 5 and first["next_cursor"]
    page2 = {"limit": 2, "sort": "-price", "cursor": first["next_cursor"]}
    second = (await client.get(URL, params=page2, headers=h)).json()
    assert [p["price"] for p in second["items"]] == ["30.00", "20.00"]
    page3 = {"limit": 2, "sort": "-price", "cursor": second["next_cursor"]}
    last = (await client.get(URL, params=page3, headers=h)).json()
    assert [p["price"] for p in last["items"]] == ["10.00"] and last["next_cursor"] is None

    assert (await client.get(URL, params={"q": "item 3"}, headers=h)).json()["total"] == 1
    assert (await client.get(URL, params={"q": "%"}, headers=h)).json()["total"] == 0  # LIKE wildcards are escaped
    low = (await client.get(URL, params={"low_stock": "true"}, headers=h)).json()
    assert low["total"] == 5 and all(p["low_stock"] for p in low["items"])  # qty 0..4 <= reorder level 5

    assert (await client.get(URL, params={"cursor": "garbage"}, headers=h)).status_code == 400
    bad_sort = await client.get(URL, params={"sort": "tenant_id"}, headers=h)
    assert bad_sort.status_code == 400 and bad_sort.json()["code"] == "invalid_sort"
    assert (await client.get(URL, params={"limit": 101}, headers=h)).status_code == 422


async def test_update_cannot_change_quantity_or_tenant_and_rejects_duplicates(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    a = (await client.post(URL, json=product("A"), headers=h)).json()
    await client.post(URL, json=product("B"), headers=h)
    assert (await client.patch(f"{URL}{a['id']}", json={"qty_on_hand": 99}, headers=h)).status_code == 422
    assert (await client.patch(f"{URL}{a['id']}", json={"tenant_id": str(uuid.uuid4())}, headers=h)).status_code == 422
    assert (await client.patch(f"{URL}{a['id']}", json={}, headers=h)).status_code == 422
    assert (await client.patch(f"{URL}{a['id']}", json={"sku": "B"}, headers=h)).status_code == 409
    ok = await client.patch(f"{URL}{a['id']}", json={"price": "99.50", "reorder_level": 4}, headers=h)
    assert ok.status_code == 200 and ok.json()["price"] == "99.50" and ok.json()["reorder_level"] == 4


async def test_unknown_or_malformed_ids_are_404_or_422_never_500(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    assert (await client.get(f"{URL}{uuid.uuid4()}", headers=h)).status_code == 404
    assert (await client.get(f"{URL}not-a-uuid", headers=h)).status_code == 422
    assert (await client.post(URL, json=product(vendor_id=str(uuid.uuid4())), headers=h)).json()[
        "code"
    ] == "unknown_vendor"


async def test_stock_movements_keep_quantity_and_history_in_step(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    h = bearer(acct)
    made = (await client.post(URL, json=product(qty_on_hand=5), headers=h)).json()
    path = f"{URL}{made['id']}/stock-movements"
    add = await client.post(path, json={"delta": 7, "reason": "purchase", "note": "Restock"}, headers=h)
    assert add.status_code == 201 and add.json()["qty_on_hand"] == 12
    sub = await client.post(path, json={"delta": -2, "reason": "adjustment"}, headers=h)
    assert sub.json()["qty_on_hand"] == 10
    refuse = await client.post(path, json={"delta": -11, "reason": "adjustment"}, headers=h)
    assert refuse.status_code == 422 and refuse.json()["code"] == "insufficient_stock"
    assert (await client.post(path, json={"delta": 0, "reason": "adjustment"}, headers=h)).status_code == 422
    assert (await client.post(path, json={"delta": 1, "reason": "sale"}, headers=h)).status_code == 422

    moves = (await client.get(path, headers=h)).json()
    assert (
        moves["total"] == 3 and sum(m["delta"] for m in moves["items"]) == 10
    )  # history adds up to the quantity on hand


async def test_every_input_in_the_shared_contract_list_is_rejected(client: AsyncClient) -> None:
    """Task 52: the web client reads the same list (frontend/tests/ui/product-validation.test.ts)."""
    import json
    from pathlib import Path

    shared = json.loads((Path(__file__).resolve().parents[2] / "contracts" / "invalid-product-inputs.json").read_text("utf-8"))
    acct = await register(client, "Shop A")
    for case in shared["cases"]:
        res = await client.post(URL, json={**shared["base"], case["field"]: case["value"]}, headers=bearer(acct))
        assert res.status_code == 422, f"{case['field']}={case['value']!r} should be rejected"
        assert case["field"] in {e["field"] for e in res.json()["errors"]}
    ok = await client.post(URL, json=shared["base"], headers=bearer(acct))
    assert ok.status_code == 201, "the base input itself must be valid"
