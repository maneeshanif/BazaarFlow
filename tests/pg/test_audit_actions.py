"""Task 06 acceptance: each audited action in PRD §14.1 writes exactly one audit row (one test per action).

Actions of §14.1 whose feature does not exist yet are listed in ``NOT_YET_BUILT`` with the phase that builds them;
the test for each lands with that feature (and its task's acceptance criteria must include it).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.agents.context import ToolContext
from app.core.tenancy import tenant_session
from app.models.tenant import TenantRole
from app.services import approvals
from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg

# PRD §14.1 items without a feature yet -> the phase that builds them. Keep in sync with the PRD.
NOT_YET_BUILT = {
    "team and role changes": "phase 1 (F-019 Team and roles)",
    "integration connect/disconnect": "phase 2 (F-018 Integrations)",
    "product create/update/delete and stock movements": "phase 1 (inventory on the database)",
    "order post and reversal": "phase 1 (sales on the database)",
    "payment and ledger entries": "phase 1 (customers and udhaar)",
    "campaign create/publish/delete": "phase 2 (marketing on the database)",
    "platform-admin impersonation and system_session operations": "phase 2 (platform admin)",
}


async def _count(conn: asyncpg.Connection, tenant_id: str | None, action: str) -> int:
    if tenant_id is None:
        return int(await conn.fetchval("SELECT count(*) FROM audit_logs WHERE action = $1 AND tenant_id IS NULL", action))
    return int(
        await conn.fetchval("SELECT count(*) FROM audit_logs WHERE action = $1 AND tenant_id = $2", action, uuid.UUID(tenant_id))
    )


@asynccontextmanager
async def _ctx(tenant_id: str, role: TenantRole) -> AsyncIterator[ToolContext]:
    async with tenant_session(uuid.UUID(tenant_id), uuid.uuid4()) as session:
        yield ToolContext(tenant_id=uuid.UUID(tenant_id), user_id=uuid.uuid4(), role=role, session=session)


async def test_failed_login_writes_exactly_one_tenantless_row_with_a_masked_email(
    client: AsyncClient, app_engine: AsyncEngine, admin_conn: asyncpg.Connection
) -> None:
    email = f"ghost-{uuid.uuid4().hex[:8]}@example.com"
    before = await admin_conn.fetchval("SELECT count(*) FROM audit_logs WHERE action = 'auth.login_failed' AND tenant_id IS NULL")
    assert (await client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password-1"})).status_code == 401
    after = await admin_conn.fetchval("SELECT count(*) FROM audit_logs WHERE action = 'auth.login_failed' AND tenant_id IS NULL")
    assert after - before == 1
    row = await admin_conn.fetchrow("SELECT after_json::text AS j FROM audit_logs WHERE action = 'auth.login_failed' ORDER BY created_at DESC LIMIT 1")
    assert email not in row["j"], "the raw e-mail must never be stored"
    assert "g***@example.com" in row["j"]


async def test_login_writes_exactly_one_row(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    acct = await register(client, "Shop A")
    await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})
    assert await _count(admin_conn, acct["tenant_id"], "auth.login") == 1


async def test_tenant_switch_writes_exactly_one_row(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    acct = await register(client, "Shop A")
    res = await client.post("/api/v1/auth/switch-tenant", json={"tenant_id": acct["tenant_id"]}, headers=bearer(acct))
    assert res.status_code == 200
    assert await _count(admin_conn, acct["tenant_id"], "auth.switch_tenant") == 1


async def test_tenant_creation_writes_exactly_one_row(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    acct = await register(client, "Shop A")
    assert await _count(admin_conn, acct["tenant_id"], "tenant.registered") == 1


async def _file(tenant_id: str) -> uuid.UUID:
    async with _ctx(tenant_id, TenantRole.staff) as ctx:
        action = await approvals.request_action(
            ctx, agent="sales", tool="post_order", summary="Sell 5 shirts", payload={"sku": "S", "qty": 5}
        )
        return action.id


async def test_agent_action_request_is_audited_with_tool_and_payload_hash(
    client: AsyncClient, app_engine: AsyncEngine, admin_conn: asyncpg.Connection
) -> None:
    acct = await register(client, "Shop A")
    await _file(acct["tenant_id"])
    assert await _count(admin_conn, acct["tenant_id"], "agent.action_requested") == 1
    row = await admin_conn.fetchrow(
        "SELECT actor_type, after_json::text AS j FROM audit_logs WHERE action = 'agent.action_requested' AND tenant_id = $1",
        uuid.UUID(acct["tenant_id"]),
    )
    assert row["actor_type"] == "agent"
    assert approvals.payload_hash({"sku": "S", "qty": 5}) in row["j"] and "post_order" in row["j"]


async def test_approve_reject_and_execute_each_write_one_row(
    client: AsyncClient, app_engine: AsyncEngine, admin_conn: asyncpg.Connection
) -> None:
    acct = await register(client, "Shop A")
    tid = acct["tenant_id"]
    approved, rejected = await _file(tid), await _file(tid)

    async def ok(_: dict[str, Any]) -> None: ...

    async with _ctx(tid, TenantRole.manager) as ctx:
        await approvals.decide(ctx, approved, approve=True)
        await approvals.decide(ctx, rejected, approve=False)
        await approvals.execute(ctx, approved, ok)
    assert await _count(admin_conn, tid, "agent.action_approved") == 1
    assert await _count(admin_conn, tid, "agent.action_rejected") == 1
    assert await _count(admin_conn, tid, "agent.action_executed") == 1
    result = await admin_conn.fetchval(
        "SELECT after_json::text FROM audit_logs WHERE action = 'agent.action_executed' AND tenant_id = $1", uuid.UUID(tid)
    )
    assert "executed" in result and approvals.payload_hash({"sku": "S", "qty": 5}) in result, "result and payload hash are recorded"


async def test_a_failed_execution_is_audited_once(client: AsyncClient, app_engine: AsyncEngine, admin_conn: asyncpg.Connection) -> None:
    acct = await register(client, "Shop A")
    tid = acct["tenant_id"]
    action_id = await _file(tid)

    async def boom(_: dict[str, Any]) -> None:
        raise RuntimeError("stock changed")

    async with _ctx(tid, TenantRole.owner) as ctx:
        await approvals.decide(ctx, action_id, approve=True)
        done = await approvals.execute(ctx, action_id, boom)
        assert done.status == "failed"
    assert await _count(admin_conn, tid, "agent.action_failed") == 1
    assert await _count(admin_conn, tid, "agent.action_executed") == 0


async def test_expiry_is_persisted_and_audited_once_by_the_sweep(
    client: AsyncClient, app_engine: AsyncEngine, admin_conn: asyncpg.Connection
) -> None:
    acct = await register(client, "Shop A")
    tid = acct["tenant_id"]
    async with _ctx(tid, TenantRole.staff) as ctx:
        old = await approvals.request_action(ctx, agent="sales", tool="post_order", summary="old", payload={"a": 1}, ttl_hours=-1)
        fresh = await approvals.request_action(ctx, agent="sales", tool="post_order", summary="new", payload={"a": 2})
        old_id, fresh_id = old.id, fresh.id

    async with _ctx(tid, TenantRole.owner) as ctx:
        expired = await approvals.expire_due(ctx)
    assert expired == 1
    async with _ctx(tid, TenantRole.owner) as ctx:
        assert await approvals.expire_due(ctx) == 0, "running the sweep again must not audit again"
        statuses = {r[0]: r[1] for r in (await ctx.session.execute(text("SELECT id, status FROM agent_actions"))).all()}
    assert statuses[old_id] == "expired" and statuses[fresh_id] == "pending"
    assert await _count(admin_conn, tid, "agent.action_expired") == 1
    async with _ctx(tid, TenantRole.owner) as ctx:
        with pytest.raises(approvals.ApprovalError, match="not pending"):
            await approvals.decide(ctx, old_id, approve=True)


async def test_audit_rows_carry_the_request_id_of_the_response(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    acct = await register(client, "Shop A")
    res = await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})
    request_id = res.headers["X-Request-ID"]
    stored = await admin_conn.fetchval("SELECT request_id FROM audit_logs WHERE action = 'auth.login' AND tenant_id = $1", uuid.UUID(acct["tenant_id"]))
    assert stored == request_id


async def test_no_audit_row_contains_a_password_token_or_full_email(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    acct = await register(client, "Shop A")
    await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})
    await client.post("/api/v1/auth/refresh", json={"refresh_token": acct["refresh_token"]})
    rows = await admin_conn.fetch(
        "SELECT coalesce(before_json::text, '') || coalesce(after_json::text, '') AS blob FROM audit_logs WHERE tenant_id = $1",
        uuid.UUID(acct["tenant_id"]),
    )
    blob = " ".join(r["blob"] for r in rows)
    for secret in (acct["password"], acct["refresh_token"], acct["access_token"], acct["email"]):
        assert secret not in blob


def test_every_unbuilt_audited_action_is_assigned_to_a_phase() -> None:
    assert all(NOT_YET_BUILT.values())
