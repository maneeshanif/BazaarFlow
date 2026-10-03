"""Migration 20261003_06 on a database that already holds legacy inventory and orders (task 55).

Upgrade to revision 05, insert legacy rows in the old shape, upgrade to 06, then check that the catalog moved into
products with the same ids, opening stock became movements, legacy orders survived as drafts, and a downgrade works.
"""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

import asyncpg
import pytest

from alembic import command
from tests.pg import test_migration_04 as m04

pytestmark = pytest.mark.pg

TENANT = m04.TENANT
_cfg = m04._cfg
scratch_db = m04.scratch_db  # the throwaway-database fixture is shared with the migration 04 tests


async def _legacy(conn: asyncpg.Connection) -> dict[str, uuid.UUID]:
    await conn.execute(
        "INSERT INTO tenants (id, name, slug, plan, status, onboarding_state, timezone, currency, created_at, updated_at) "
        "VALUES ($1, 'T', 't', 'demo', 'active', 'created', 'Asia/Karachi', 'PKR', now(), now())",
        TENANT,
    )
    ids = {"with_stock": uuid.uuid4(), "no_sku": uuid.uuid4(), "deleted": uuid.uuid4()}
    for key, sku, stock, price, deleted in (
        ("with_stock", "SHIRT-1", 7, "2500.00", False),
        ("no_sku", None, 0, None, False),
        ("deleted", "OLD-1", 3, "10.00", True),
    ):
        await conn.execute(
            "INSERT INTO inventory_items (id, tenant_id, sku, name, category, stock_count, price, incoming_units, "
            "min_threshold, version, created_at, updated_at, deleted_at) "
            "VALUES ($1, $2, $3, $4, 'Apparel', $5, $6::numeric, 0, 2, 1, now(), now(), CASE WHEN $7 THEN now() END)",
            ids[key],
            TENANT,
            sku,
            f"Name {key}",
            stock,
            price,
            deleted,
        )
    await conn.execute(
        "INSERT INTO orders (id, tenant_id, customer_name, customer_phone, product_name, quantity, budget, "
        "payment_status, delivery_address, notes, version, created_at, updated_at) "
        "VALUES (gen_random_uuid(), $1, 'Ali', '+923001112222', 'Blue shirt', 2, 5000, 'pending', 'Lahore', 'urgent', 1, now(), now())",
        TENANT,
    )
    return ids


async def test_legacy_inventory_and_orders_move_into_the_new_model_without_loss(scratch_db: str) -> None:
    await asyncio.to_thread(command.upgrade, _cfg(), "20261003_05")
    conn = await asyncpg.connect(scratch_db)
    try:
        ids = await _legacy(conn)
    finally:
        await conn.close()

    await asyncio.to_thread(command.upgrade, _cfg(), "head")

    conn = await asyncpg.connect(scratch_db)
    try:
        products = {r["id"]: r for r in await conn.fetch("SELECT * FROM products")}
        assert set(products) == set(ids.values()), "every legacy row keeps its id"
        assert products[ids["with_stock"]]["sku"] == "SHIRT-1" and products[ids["with_stock"]]["price"] == Decimal(
            "2500.00"
        )
        assert products[ids["no_sku"]]["sku"].startswith("SKU-"), "a missing sku gets a generated one"
        assert products[ids["no_sku"]]["price"] == Decimal("0.00")
        assert products[ids["deleted"]]["deleted_at"] is not None, "soft-deleted rows stay soft-deleted"

        stock = {r["product_id"]: r for r in await conn.fetch("SELECT * FROM inventory_items")}
        assert (stock[ids["with_stock"]]["qty_on_hand"], stock[ids["with_stock"]]["reorder_level"]) == (7, 2)

        movements = await conn.fetch("SELECT product_id, delta, reason FROM stock_movements")
        assert {(m["product_id"], m["delta"], m["reason"]) for m in movements} == {
            (ids["with_stock"], 7, "opening"),
            (ids["deleted"], 3, "opening"),
        }, "quantity equals the sum of its movements from day one (zero stock needs no movement)"

        order = await conn.fetchrow("SELECT * FROM orders")
        assert order["status"] == "draft" and order["channel"] == "whatsapp" and order["total"] == Decimal("5000.00")
        for text_part in ("2 x Blue shirt", "Ali", "+923001112222", "Lahore", "urgent"):
            assert text_part in order["note"], f"the legacy order text '{text_part}' must survive in the note"
    finally:
        await conn.close()


async def test_the_migration_can_be_reversed(scratch_db: str) -> None:
    await asyncio.to_thread(command.upgrade, _cfg(), "20261003_05")
    conn = await asyncpg.connect(scratch_db)
    try:
        ids = await _legacy(conn)
    finally:
        await conn.close()
    await asyncio.to_thread(command.upgrade, _cfg(), "head")
    await asyncio.to_thread(command.downgrade, _cfg(), "20261003_05")

    conn = await asyncpg.connect(scratch_db)
    try:
        rows = {r["id"]: r for r in await conn.fetch("SELECT id, sku, name, stock_count, price FROM inventory_items")}
        assert set(rows) == set(ids.values())
        assert rows[ids["with_stock"]]["sku"] == "SHIRT-1" and rows[ids["with_stock"]]["stock_count"] == 7
        assert await conn.fetchval("SELECT count(*) FROM orders") == 1
        assert await conn.fetchval("SELECT to_regclass('products')") is None
    finally:
        await conn.close()
    await asyncio.to_thread(command.upgrade, _cfg(), "head")  # and forward again
