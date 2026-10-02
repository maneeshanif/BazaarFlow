"""Migration 20261002_04 on a database that already holds data (review findings on task 03).

Runs its own throwaway database inside the session container: upgrade to revision 03, insert awkward legacy
rows, upgrade to 04, check the money parsing rule and that soft-deleted rows survive a downgrade.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import asyncpg
import pytest
from alembic.config import Config

from alembic import command
from app.core.settings import settings
from tests.pg.conftest import ROOT

pytestmark = pytest.mark.pg

TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _cfg() -> Config:
    cfg = Config(str(Path(ROOT) / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(ROOT) / "alembic"))
    return cfg


@pytest.fixture
def scratch_db(pg_urls: dict[str, str]) -> Iterator[str]:
    """A fresh empty database; yields its asyncpg URL and points Alembic at it."""
    name = f"mig_{uuid.uuid4().hex[:8]}"
    admin = pg_urls["admin_plain"]

    async def _create() -> None:
        conn = await asyncpg.connect(admin)
        await conn.execute(f"CREATE DATABASE {name}")
        await conn.close()

    async def _drop() -> None:
        conn = await asyncpg.connect(admin)
        await conn.execute(f"DROP DATABASE {name} WITH (FORCE)")
        await conn.close()

    asyncio.run(_create())
    url = pg_urls["admin"].rsplit("/", 1)[0] + f"/{name}"
    previous = settings.DATABASE_URL_MIGRATIONS
    settings.DATABASE_URL_MIGRATIONS = url
    try:
        yield url.replace("+asyncpg", "")
    finally:
        settings.DATABASE_URL_MIGRATIONS = previous
        asyncio.run(_drop())


async def _seed_legacy_rows(url: str) -> None:
    conn = await asyncpg.connect(url)
    try:
        await conn.execute(
            "INSERT INTO tenants (id, name, slug, plan, status, onboarding_state, timezone, currency, created_at, updated_at) "
            "VALUES ($1, 'T', 't', 'demo', 'active', 'created', 'Asia/Karachi', 'PKR', now(), now())",
            TENANT,
        )
        prices = {
            "plain": "2500 PKR",
            "range": "2000-3000 PKR",
            "comma": "1,299.50",
            "words": "call us",
            "double-dot": "approx. 1.5.2",
            "huge": "99999999999999999999",
            "empty": "",
        }
        for sku, price in prices.items():
            await conn.execute(
                "INSERT INTO inventory_items (id, tenant_id, sku, name, stock_count, price, incoming_units, min_threshold, "
                "created_at, updated_at) VALUES (gen_random_uuid(), $1, $2, $2, 1, $3, 0, 0, now(), now())",
                TENANT,
                sku,
                price,
            )
    finally:
        await conn.close()


async def test_text_prices_become_numeric_using_the_first_number_and_never_abort_the_upgrade(scratch_db: str) -> None:
    await asyncio.to_thread(command.upgrade, _cfg(), "20261002_03")
    await _seed_legacy_rows(scratch_db)
    await asyncio.to_thread(command.upgrade, _cfg(), "20261002_04")  # must not raise, whatever the legacy text looked like

    conn = await asyncpg.connect(scratch_db)
    try:
        rows = {r["sku"]: r["price"] for r in await conn.fetch("SELECT sku, price FROM inventory_items")}
        versions = {r["version"] for r in await conn.fetch("SELECT version FROM inventory_items")}
    finally:
        await conn.close()
    assert rows["plain"] == Decimal("2500.00")
    assert rows["range"] == Decimal("2000.00"), "a range must not be glued into 20003000"
    assert rows["comma"] == Decimal("1299.50")
    assert rows["double-dot"] == Decimal("1.50")
    assert rows["words"] is None and rows["empty"] is None and rows["huge"] is None
    assert versions == {1}


async def test_downgrade_keeps_soft_deleted_rows_instead_of_deleting_them(scratch_db: str) -> None:
    await asyncio.to_thread(command.upgrade, _cfg(), "head")
    conn = await asyncpg.connect(scratch_db)
    try:
        await conn.execute(
            "INSERT INTO tenants (id, name, slug, plan, status, onboarding_state, timezone, currency, created_at, updated_at) "
            "VALUES ($1, 'T', 't', 'demo', 'active', 'created', 'Asia/Karachi', 'PKR', now(), now())",
            TENANT,
        )
        # the same phone twice: one live, one soft-deleted (allowed by the partial unique index)
        for deleted in (True, False):
            await conn.execute(
                "INSERT INTO customers (id, tenant_id, phone, created_at, updated_at, deleted_at) "
                "VALUES (gen_random_uuid(), $1, '+923001112222', now(), now(), CASE WHEN $2 THEN now() END)",
                TENANT,
                deleted,
            )
    finally:
        await conn.close()
    await asyncio.to_thread(command.downgrade, _cfg(), "20261002_03")
    conn = await asyncpg.connect(scratch_db)
    try:
        assert await conn.fetchval("SELECT count(*) FROM customers") == 2, "soft-deleted rows must survive a downgrade"
    finally:
        await conn.close()


async def test_downgrade_works_when_a_soft_deleted_sku_is_very_long(scratch_db: str) -> None:
    """The renamed sku (original + '#deleted-' + uuid) must still fit VARCHAR(100)."""
    await asyncio.to_thread(command.upgrade, _cfg(), "head")
    conn = await asyncpg.connect(scratch_db)
    try:
        await conn.execute(
            "INSERT INTO tenants (id, name, slug, plan, status, onboarding_state, timezone, currency, created_at, updated_at) "
            "VALUES ($1, 'T', 't', 'demo', 'active', 'created', 'Asia/Karachi', 'PKR', now(), now())",
            TENANT,
        )
        await conn.execute(
            "INSERT INTO inventory_items (id, tenant_id, sku, name, stock_count, incoming_units, min_threshold, version, "
            "created_at, updated_at, deleted_at) VALUES (gen_random_uuid(), $1, $2, 'x', 1, 0, 0, 1, now(), now(), now())",
            TENANT,
            "S" * 100,
        )
    finally:
        await conn.close()
    await asyncio.to_thread(command.downgrade, _cfg(), "20261002_03")  # must not fail with 'value too long'
    conn = await asyncpg.connect(scratch_db)
    try:
        assert await conn.fetchval("SELECT count(*) FROM inventory_items") == 1
    finally:
        await conn.close()
