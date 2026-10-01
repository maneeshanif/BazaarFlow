"""Row-level security behaviour against real Postgres, as the application role (PRD §3.5, §3.8, §19).

These are the Phase 0 exit tests: two tenants exist, and neither can see or change the other's rows,
and with no tenant context nothing is visible at all.
"""

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

TENANT_TABLES = [
    "customers",
    "facebook_accounts",
    "inventory_items",
    "marketing_posts",
    "memberships",
    "messages",
    "orders",
    "scheduled_campaigns",
    "support_tickets",
    "tenant_integrations",
    "vendors",
]


async def _session(engine: AsyncEngine, tenant_id: uuid.UUID | None = None, user_id: uuid.UUID | None = None) -> AsyncSession:
    session = AsyncSession(engine, expire_on_commit=False)
    await session.begin()
    await apply_context(session, tenant_id=tenant_id, user_id=user_id)
    return session


async def test_no_context_means_no_rows(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    for acct in (a, b):
        res = await client.post("/api/v1/customers/", json={"phone": "+923000000001", "name": "Walk-in"}, headers=bearer(acct))
        assert res.status_code == 201, res.text

    session = await _session(app_engine)  # no app.tenant_id, no app.user_id
    try:
        for table in [*TENANT_TABLES, "tenants", "audit_logs"]:
            count = (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()
            assert count == 0, f"{table} leaked {count} rows without a tenant context"
    finally:
        await session.rollback()
        await session.close()


async def test_a_tenant_context_only_sees_its_own_rows(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    for acct in (a, b):
        await client.post("/api/v1/customers/", json={"phone": "+923000000002", "name": "Someone"}, headers=bearer(acct))
    tenant_a = uuid.UUID(a["tenant_id"])
    tenant_b = uuid.UUID(b["tenant_id"])

    session = await _session(app_engine, tenant_id=tenant_a)
    try:
        for table in TENANT_TABLES:
            ids = {r[0] for r in (await session.execute(text(f"SELECT DISTINCT tenant_id FROM {table}"))).all()}
            assert ids <= {tenant_a}, f"{table} exposes another tenant: {ids}"
        seen = {r[0] for r in (await session.execute(text("SELECT id FROM tenants"))).all()}
        assert seen == {tenant_a}
        audit = {r[0] for r in (await session.execute(text("SELECT DISTINCT tenant_id FROM audit_logs"))).all()}
        assert audit == {tenant_a}
        assert tenant_b not in audit
    finally:
        await session.rollback()
        await session.close()


async def test_cannot_modify_or_create_rows_of_another_tenant(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await client.post("/api/v1/customers/", json={"phone": "+923000000003", "name": "B's customer"}, headers=bearer(b))
    tenant_a = uuid.UUID(a["tenant_id"])
    tenant_b = uuid.UUID(b["tenant_id"])

    session = await _session(app_engine, tenant_id=tenant_a)
    try:
        updated = await session.execute(text("UPDATE customers SET name = 'pwned' WHERE tenant_id = :t"), {"t": tenant_b})
        assert updated.rowcount == 0
        deleted = await session.execute(text("DELETE FROM customers WHERE tenant_id = :t"), {"t": tenant_b})
        assert deleted.rowcount == 0
    finally:
        await session.rollback()
        await session.close()

    for statement in (
        "INSERT INTO customers (id, tenant_id, phone, created_at, updated_at) VALUES (gen_random_uuid(), :t, '+92300999', now(), now())",
    ):
        session = await _session(app_engine, tenant_id=tenant_a)
        try:
            with pytest.raises(DBAPIError):
                await session.execute(text(statement), {"t": tenant_b})
        finally:
            await session.rollback()
            await session.close()


async def test_moving_a_row_to_another_tenant_is_rejected(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    await client.post("/api/v1/customers/", json={"phone": "+923000000004", "name": "Mine"}, headers=bearer(a))
    session = await _session(app_engine, tenant_id=uuid.UUID(a["tenant_id"]))
    try:
        with pytest.raises(DBAPIError):
            await session.execute(
                text("UPDATE customers SET tenant_id = :b WHERE tenant_id = :a"),
                {"a": uuid.UUID(a["tenant_id"]), "b": uuid.UUID(b["tenant_id"])},
            )
    finally:
        await session.rollback()
        await session.close()


async def test_audit_log_is_append_only_for_the_application(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    for statement in ("UPDATE audit_logs SET action = 'tampered'", "DELETE FROM audit_logs"):
        session = await _session(app_engine, tenant_id=uuid.UUID(a["tenant_id"]))
        try:
            with pytest.raises(DBAPIError):
                await session.execute(text(statement))
        finally:
            await session.rollback()
            await session.close()


async def test_a_user_can_read_only_their_own_memberships(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    await register(client, "Shop B")
    me = await client.get("/api/v1/auth/me", headers=bearer(a))
    user_id = uuid.UUID(me.json()["user"]["id"])

    session = await _session(app_engine, user_id=user_id)  # login-time context: user only, no tenant
    try:
        rows = (await session.execute(text("SELECT tenant_id, user_id FROM memberships"))).all()
        assert {r.user_id for r in rows} == {user_id}
        assert {r.tenant_id for r in rows} == {uuid.UUID(a["tenant_id"])}
    finally:
        await session.rollback()
        await session.close()
