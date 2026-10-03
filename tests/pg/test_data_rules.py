"""Task 03 behaviour: soft delete, per-tenant uniqueness with soft delete, optimistic concurrency, NUMERIC money."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm.exc import StaleDataError

from app.core.tenancy import tenant_session
from app.models.inventory import InventoryItem
from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg


async def test_deleting_a_customer_is_soft_and_the_phone_can_be_reused(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    acct = await register(client, "Shop A")
    headers = bearer(acct)
    created = (
        await client.post("/api/v1/customers/", json={"phone": "+923005550001", "name": "Old"}, headers=headers)
    ).json()
    assert (await client.delete(f"/api/v1/customers/{created['id']}", headers=headers)).status_code == 204

    assert (await client.get("/api/v1/customers/", headers=headers)).json()["items"] == []
    async with tenant_session(uuid.UUID(acct["tenant_id"])) as session:
        row = (
            await session.execute(
                text("SELECT deleted_at FROM customers WHERE id = :i"), {"i": uuid.UUID(created["id"])}
            )
        ).one()
        assert row.deleted_at is not None, "the row must still exist, marked deleted"

    again = await client.post("/api/v1/customers/", json={"phone": "+923005550001", "name": "New"}, headers=headers)
    assert again.status_code == 201, again.text  # uniqueness only applies to live rows
    assert (
        await client.post("/api/v1/customers/", json={"phone": "+923005550001", "name": "Dup"}, headers=headers)
    ).status_code == 409


def _product(sku: str, name: str = "Thing", price: str = "10.00", qty: int = 1) -> dict[str, object]:
    return {"sku": sku, "name": name, "price": price, "qty_on_hand": qty}


async def test_a_soft_deleted_product_is_hidden_and_its_sku_can_be_reused(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    acct = await register(client, "Shop A")
    headers = bearer(acct)
    created = (
        await client.post("/api/v1/inventory/", json=_product("S-1", "Shirt", "2500.50", 5), headers=headers)
    ).json()
    assert (await client.delete(f"/api/v1/inventory/{created['id']}", headers=headers)).status_code == 204
    assert (await client.get("/api/v1/inventory/", headers=headers)).json()["items"] == []
    assert (await client.get(f"/api/v1/inventory/{created['id']}", headers=headers)).status_code == 404
    again = await client.post("/api/v1/inventory/", json=_product("S-1", "Shirt v2", "2600.00"), headers=headers)
    assert again.status_code == 201, again.text


async def test_money_round_trips_as_an_exact_decimal(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    headers = bearer(acct)
    res = await client.post("/api/v1/inventory/", json=_product("M-1", "Mug", "0.10"), headers=headers)
    assert res.json()["price"] == "0.10"
    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as session:
        price = (await session.execute(text("SELECT price FROM products WHERE sku = 'M-1'"))).scalar_one()
        assert price == Decimal("0.10")
        assert price + Decimal("0.20") == Decimal("0.30")  # would fail with binary floats


async def test_two_writers_cannot_silently_overwrite_each_other(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    tenant_id = uuid.UUID(acct["tenant_id"])
    await client.post("/api/v1/inventory/", json=_product("V-1", "Widget", "10.00", 10), headers=bearer(acct))

    # Both writers read version 1. The first commits (version 2); the second then tries to write from its stale
    # copy and must be refused rather than silently overwrite the first writer's change.
    first_cm = tenant_session(tenant_id)
    second_cm = tenant_session(tenant_id)
    first = await first_cm.__aenter__()
    second = await second_cm.__aenter__()
    try:
        a = (await first.execute(select(InventoryItem))).scalar_one()
        b = (await second.execute(select(InventoryItem))).scalar_one()
        a.qty_on_hand = 7
        await first_cm.__aexit__(None, None, None)  # commit
        b.qty_on_hand = 3
        with pytest.raises(StaleDataError):
            await second.flush()
    finally:
        await second_cm.__aexit__(None, None, None)


async def test_the_same_sku_cannot_exist_twice_for_one_tenant_but_can_for_two(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    for acct in (a, b):
        assert (await client.post("/api/v1/inventory/", json=_product("SAME"), headers=bearer(acct))).status_code == 201
    dup = await client.post("/api/v1/inventory/", json=_product("SAME", "Why"), headers=bearer(a))
    assert dup.status_code == 409
    assert dup.json()["code"] == "duplicate_sku"


async def test_a_malformed_customer_id_is_a_404_not_a_validation_error(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    acct = await register(client, "Shop A")
    res = await client.delete("/api/v1/customers/not-a-uuid", headers=bearer(acct))
    assert res.status_code == 404


async def test_exports_skip_soft_deleted_rows_and_serialise_decimals(
    client: AsyncClient, app_engine: AsyncEngine, tmp_path: pytest.TempPathFactory
) -> None:
    import json

    from app.cli.export import export_data

    acct = await register(client, "Shop A")
    headers = bearer(acct)
    tenant_id = uuid.UUID(acct["tenant_id"])
    await client.post("/api/v1/inventory/", json=_product("KEEP", "Keep", "12.50"), headers=headers)
    gone = (await client.post("/api/v1/inventory/", json=_product("GONE", "Gone", "1.00"), headers=headers)).json()
    await client.delete(f"/api/v1/inventory/{gone['id']}", headers=headers)

    out = tmp_path / "inventory.json"  # type: ignore[operator]
    await export_data(tenant_id, "inventory", "json", str(out))
    exported = json.loads(out.read_text(encoding="utf-8"))
    assert [row["sku"] for row in exported] == ["KEEP"]
    assert exported[0]["price"] == "12.50"
