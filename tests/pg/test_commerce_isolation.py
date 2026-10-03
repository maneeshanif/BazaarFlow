"""Task 56: tenant A cannot read or write tenant B's commerce rows, through the API or straight at the database."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.tenancy import apply_context
from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg

URL = "/api/v1/inventory/"


def item(sku: str) -> dict[str, object]:
    return {"sku": sku, "name": "Thing", "price": "10.00", "qty_on_hand": 4}


async def test_a_shop_only_lists_its_own_products(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await client.post(URL, json=item("A-ONLY"), headers=bearer(a))
    await client.post(URL, json=item("B-ONLY"), headers=bearer(b))
    assert [p["sku"] for p in (await client.get(URL, headers=bearer(a))).json()["items"]] == ["A-ONLY"]
    assert [p["sku"] for p in (await client.get(URL, headers=bearer(b))).json()["items"]] == ["B-ONLY"]


async def test_another_shops_product_id_is_a_404_for_every_operation(client: AsyncClient) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    pid = (await client.post(URL, json=item("A-1"), headers=bearer(a))).json()["id"]
    hb = bearer(b)
    assert (await client.get(f"{URL}{pid}", headers=hb)).status_code == 404
    assert (await client.patch(f"{URL}{pid}", json={"name": "Hijacked"}, headers=hb)).status_code == 404
    assert (await client.delete(f"{URL}{pid}", headers=hb)).status_code == 404
    assert (await client.get(f"{URL}{pid}/stock-movements", headers=hb)).status_code == 404
    move = {"delta": 5, "reason": "purchase"}
    assert (await client.post(f"{URL}{pid}/stock-movements", json=move, headers=hb)).status_code == 404
    untouched = (await client.get(f"{URL}{pid}", headers=bearer(a))).json()
    assert untouched["name"] == "Thing" and untouched["qty_on_hand"] == 4


async def test_a_vendor_from_another_shop_cannot_be_attached(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    vendor_id = uuid.uuid4()
    session = AsyncSession(app_engine)
    await session.begin()
    try:
        await apply_context(session, tenant_id=uuid.UUID(b["tenant_id"]))
        await session.execute(
            text(
                "INSERT INTO vendors (id, tenant_id, name, balance, created_at, updated_at) "
                "VALUES (:id, :t, 'B vendor', 0, now(), now())"
            ),
            {"id": vendor_id, "t": uuid.UUID(b["tenant_id"])},
        )
        await session.commit()
    finally:
        await session.close()
    body = {**item("A-2"), "vendor_id": str(vendor_id)}
    res = await client.post(URL, json=body, headers=bearer(a))
    assert res.status_code == 422 and res.json()["code"] == "unknown_vendor"


async def _as(engine: AsyncEngine, tenant_id: uuid.UUID | None) -> AsyncSession:
    session = AsyncSession(engine, expire_on_commit=False)
    await session.begin()
    await apply_context(session, tenant_id=tenant_id)
    return session


async def test_the_database_refuses_a_cross_tenant_write_even_from_trusted_code(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    a_id, b_id = uuid.UUID(a["tenant_id"]), uuid.UUID(b["tenant_id"])
    await client.post(URL, json=item("B-1"), headers=bearer(b))

    session = await _as(app_engine, a_id)
    try:
        # Inserting a row that claims shop B while acting as shop A is refused by the row level security policy.
        with pytest.raises(DBAPIError):
            await session.execute(
                text(
                    "INSERT INTO products (id, tenant_id, sku, name, price, active, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :t, 'X', 'Sneaky', 1, true, now(), now())"
                ),
                {"t": b_id},
            )
    finally:
        await session.rollback()

    session = await _as(app_engine, a_id)
    try:
        # Updating or deleting shop B's rows as shop A matches nothing.
        updated = await session.execute(text("UPDATE products SET name = 'Hijacked' WHERE tenant_id = :t"), {"t": b_id})
        deleted = await session.execute(text("DELETE FROM inventory_items WHERE tenant_id = :t"), {"t": b_id})
        assert (updated.rowcount, deleted.rowcount) == (0, 0)  # type: ignore[attr-defined]
    finally:
        await session.rollback()


@pytest.mark.parametrize(
    "table", ["products", "inventory_items", "stock_movements", "orders", "order_items", "payments", "ledger_entries"]
)
async def test_no_tenant_context_returns_nothing(client: AsyncClient, app_engine: AsyncEngine, table: str) -> None:
    a = await register(client, "Shop A")
    await client.post(URL, json=item("A-1"), headers=bearer(a))
    session = await _as(app_engine, None)
    try:
        assert (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one() == 0
    finally:
        await session.rollback()


@pytest.mark.parametrize("table", ["stock_movements", "ledger_entries"])
async def test_history_tables_are_append_only_for_the_application_role(
    client: AsyncClient, app_engine: AsyncEngine, table: str
) -> None:
    a = await register(client, "Shop A")
    await client.post(URL, json=item("A-1"), headers=bearer(a))
    a_id = uuid.UUID(a["tenant_id"])
    for statement in (f"UPDATE {table} SET created_at = now()", f"DELETE FROM {table}"):
        session = await _as(app_engine, a_id)
        try:
            with pytest.raises(DBAPIError):
                await session.execute(text(statement))
        finally:
            await session.rollback()
