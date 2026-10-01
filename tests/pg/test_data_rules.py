"""Task 03 behaviour: soft delete, per-tenant uniqueness with soft delete, optimistic concurrency, NUMERIC money."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm.exc import StaleDataError

from app.core.tenancy import tenant_session
from app.crud import crud_inventory
from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg


async def test_deleting_a_customer_is_soft_and_the_phone_can_be_reused(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    headers = bearer(acct)
    created = (await client.post("/api/v1/customers/", json={"phone": "+923005550001", "name": "Old"}, headers=headers)).json()
    assert (await client.delete(f"/api/v1/customers/{created['id']}", headers=headers)).status_code == 204

    assert (await client.get("/api/v1/customers/", headers=headers)).json() == []
    async with tenant_session(uuid.UUID(acct["tenant_id"])) as session:
        row = (await session.execute(text("SELECT deleted_at FROM customers WHERE id = :i"), {"i": uuid.UUID(created["id"])})).one()
        assert row.deleted_at is not None, "the row must still exist, marked deleted"

    again = await client.post("/api/v1/customers/", json={"phone": "+923005550001", "name": "New"}, headers=headers)
    assert again.status_code == 201, again.text  # uniqueness only applies to live rows
    assert (await client.post("/api/v1/customers/", json={"phone": "+923005550001", "name": "Dup"}, headers=headers)).status_code == 409


async def test_a_soft_deleted_item_does_not_show_up_in_inventory_lookups(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as session:
        await crud_inventory.create_item(session, tenant_id, sku="S-1", name="Shirt", price=Decimal("2500.50"), stock_count=5)
    async with tenant_session(tenant_id) as session:
        assert await crud_inventory.delete_item(session, tenant_id, "S-1") is True
    async with tenant_session(tenant_id) as session:
        assert await crud_inventory.get_item_by_sku(session, tenant_id, "S-1") is None
        assert await crud_inventory.get_all_items(session, tenant_id) == []
        # and the sku can be created again
        await crud_inventory.create_item(session, tenant_id, sku="S-1", name="Shirt v2", price=Decimal("2600.00"), stock_count=1)


async def test_money_round_trips_as_an_exact_decimal(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as session:
        await crud_inventory.create_item(session, tenant_id, sku="M-1", name="Mug", price=Decimal("0.10"), stock_count=1)
    async with tenant_session(tenant_id) as session:
        item = await crud_inventory.get_item_by_sku(session, tenant_id, "M-1")
        assert item is not None and item.price == Decimal("0.10")
        assert item.price + Decimal("0.20") == Decimal("0.30")  # would fail with binary floats


async def test_two_writers_cannot_silently_overwrite_each_other(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as session:
        await crud_inventory.create_item(session, tenant_id, sku="V-1", name="Widget", price=Decimal("10.00"), stock_count=10)

    # Both writers read version 1. The first commits (version 2); the second then tries to write from its stale
    # copy and must be refused rather than silently overwrite the first writer's change.
    first_cm = tenant_session(tenant_id)
    second_cm = tenant_session(tenant_id)
    first = await first_cm.__aenter__()
    second = await second_cm.__aenter__()
    try:
        a = await crud_inventory.get_item_by_sku(first, tenant_id, "V-1")
        b = await crud_inventory.get_item_by_sku(second, tenant_id, "V-1")
        assert a is not None and b is not None
        a.stock_count = 7
        await first_cm.__aexit__(None, None, None)  # commit
        b.stock_count = 3
        with pytest.raises(StaleDataError):
            await second.flush()
    finally:
        await second_cm.__aexit__(None, None, None)


async def test_the_same_sku_cannot_exist_twice_for_one_tenant_but_can_for_two(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    for acct in (a, b):
        tid = uuid.UUID(acct["tenant_id"])
        async with tenant_session(tid) as session:
            await crud_inventory.create_item(session, tid, sku="SAME", name="X", price=Decimal("1.00"), stock_count=1)
    tid = uuid.UUID(a["tenant_id"])
    with pytest.raises(IntegrityError):
        async with tenant_session(tid) as session:
            await crud_inventory.create_item(session, tid, sku="SAME", name="Y", price=Decimal("1.00"), stock_count=1)


async def test_a_malformed_customer_id_is_a_404_not_a_validation_error(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    res = await client.delete("/api/v1/customers/not-a-uuid", headers=bearer(acct))
    assert res.status_code == 404


async def test_exports_skip_soft_deleted_rows_and_serialise_decimals(
    client: AsyncClient, app_engine: AsyncEngine, tmp_path: pytest.TempPathFactory
) -> None:
    import json

    from app.cli.export import export_data

    acct = await register(client, "Shop A")
    tenant_id = uuid.UUID(acct["tenant_id"])
    async with tenant_session(tenant_id) as session:
        await crud_inventory.create_item(session, tenant_id, sku="KEEP", name="Keep", price=Decimal("12.50"), stock_count=1)
        await crud_inventory.create_item(session, tenant_id, sku="GONE", name="Gone", price=Decimal("1.00"), stock_count=1)
    async with tenant_session(tenant_id) as session:
        await crud_inventory.delete_item(session, tenant_id, "GONE")

    out = tmp_path / "inventory.json"  # type: ignore[operator]
    await export_data(tenant_id, "inventory", "json", str(out))
    exported = json.loads(out.read_text(encoding="utf-8"))
    assert [row["sku"] for row in exported] == ["KEEP"]
    assert exported[0]["price"] == "12.50"
