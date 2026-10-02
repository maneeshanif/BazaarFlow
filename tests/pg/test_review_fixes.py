"""Regression tests for the independent review of tasks 04-14: races, revocation, partial writes, input limits."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.agents.context import ToolContext
from app.core.tenancy import apply_context, tenant_session
from app.models.customer import Customer
from app.models.tenant import TenantRole
from app.services import approvals
from tests.pg.conftest import bearer, register

pytestmark = pytest.mark.pg


@asynccontextmanager
async def _ctx(tenant_id: str, role: TenantRole) -> AsyncIterator[ToolContext]:
    async with tenant_session(uuid.UUID(tenant_id), uuid.uuid4()) as session:
        yield ToolContext(tenant_id=uuid.UUID(tenant_id), user_id=uuid.uuid4(), role=role, session=session)


async def test_concurrent_refreshes_with_one_token_succeed_only_once(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    results = await asyncio.gather(*[client.post("/api/v1/auth/refresh", json={"refresh_token": acct["refresh_token"]}) for _ in range(6)])
    codes = sorted(r.status_code for r in results)
    assert codes.count(200) == 1, f"a single refresh token must mint exactly one successor, got {codes}"


async def test_an_approved_action_runs_its_executor_exactly_once_under_concurrency(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    acct = await register(client, "Shop A")
    tid = acct["tenant_id"]
    async with _ctx(tid, TenantRole.manager) as ctx:
        action = await approvals.request_action(ctx, agent="sales", tool="post_order", summary="s", payload={"qty": 1})
        action_id = action.id
        await approvals.decide(ctx, action_id, approve=True)

    runs: list[int] = []

    async def executor(_: dict[str, Any]) -> None:
        runs.append(1)
        await asyncio.sleep(0.2)  # widen the race window

    async def attempt() -> str:
        try:
            async with _ctx(tid, TenantRole.manager) as ctx:
                done = await approvals.execute(ctx, action_id, executor)
                return done.status
        except approvals.ApprovalError:
            return "refused"

    outcomes = await asyncio.gather(*[attempt() for _ in range(4)])
    assert len(runs) == 1, f"executor ran {len(runs)} times"
    assert outcomes.count("executed") == 1


async def test_only_owners_and_managers_can_execute(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    tid = acct["tenant_id"]
    async with _ctx(tid, TenantRole.manager) as ctx:
        action = await approvals.request_action(ctx, agent="sales", tool="post_order", summary="s", payload={"qty": 1})
        await approvals.decide(ctx, action.id, approve=True)
        action_id = action.id

    async def noop(_: dict[str, Any]) -> None: ...

    async with _ctx(tid, TenantRole.staff) as ctx:
        with pytest.raises(PermissionError):
            await approvals.execute(ctx, action_id, noop)


async def test_a_failing_executor_leaves_no_partial_writes(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    tid = acct["tenant_id"]
    tenant_id = uuid.UUID(tid)
    async with _ctx(tid, TenantRole.manager) as ctx:
        action = await approvals.request_action(ctx, agent="sales", tool="post_order", summary="s", payload={"qty": 1})
        await approvals.decide(ctx, action.id, approve=True)
        action_id = action.id

    async with _ctx(tid, TenantRole.manager) as ctx:

        async def half_done(_: dict[str, Any]) -> None:
            ctx.session.add(Customer(tenant_id=tenant_id, phone="+923007770001", name="partial"))
            await ctx.session.flush()
            raise RuntimeError("second step failed")

        done = await approvals.execute(ctx, action_id, half_done)
        assert done.status == "failed"

    async with _ctx(tid, TenantRole.manager) as ctx:
        count = (await ctx.session.execute(text("SELECT count(*) FROM customers WHERE phone = '+923007770001'"))).scalar_one()
        assert count == 0, "the executor's partial writes must be rolled back"
        status = (await ctx.session.execute(text("SELECT status FROM agent_actions WHERE id = :i"), {"i": action_id})).scalar_one()
        assert status == "failed"


async def _set(app_engine: AsyncEngine, acct: dict[str, Any], sql: str) -> None:
    session = AsyncSession(app_engine)
    await session.begin()
    try:
        await apply_context(session, tenant_id=uuid.UUID(acct["tenant_id"]))
        await session.execute(text(sql))
        await session.commit()
    finally:
        await session.close()


async def test_a_deactivated_user_is_locked_out_of_every_route_including_legacy_ones(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    acct = await register(client, "Shop A")
    headers = bearer(acct)
    assert (await client.get("/api/vendors/", headers=headers)).status_code == 200
    await _set(app_engine, acct, "UPDATE users SET is_active = false")
    assert (await client.get("/api/vendors/", headers=headers)).status_code == 401
    assert (await client.get("/api/v1/customers/", headers=headers)).status_code == 401
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401


async def test_a_demoted_member_is_refused_on_legacy_routes_too(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    headers = bearer(acct)
    assert (await client.get("/api/vendors/", headers=headers)).status_code == 200
    await _set(app_engine, acct, "UPDATE memberships SET role = 'staff'")
    assert (await client.get("/api/vendors/", headers=headers)).status_code == 401


async def test_a_token_claiming_platform_admin_without_the_database_flag_is_refused(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    from app.core.security import create_access_token

    acct = await register(client, "Shop A")
    me = (await client.get("/api/v1/auth/me", headers=bearer(acct))).json()
    forged = create_access_token(
        me["user"]["id"], extra_claims={"tenant_id": acct["tenant_id"], "role": "owner", "pa": True}
    )
    assert (await client.get("/api/logs/", headers={"Authorization": f"Bearer {forged}"})).status_code == 401


async def test_customer_input_is_validated_and_concurrent_duplicates_give_409(client: AsyncClient) -> None:
    acct = await register(client, "Shop A")
    headers = bearer(acct)
    too_long_phone = await client.post("/api/v1/customers/", json={"phone": "+92" + "3" * 40, "name": "x"}, headers=headers)
    assert too_long_phone.status_code == 422
    too_long_name = await client.post("/api/v1/customers/", json={"phone": "+923001230001", "name": "n" * 300}, headers=headers)
    assert too_long_name.status_code == 422
    not_a_phone = await client.post("/api/v1/customers/", json={"phone": "hello", "name": "x"}, headers=headers)
    assert not_a_phone.status_code == 422

    results = await asyncio.gather(
        *[client.post("/api/v1/customers/", json={"phone": "+923001230002", "name": "dup"}, headers=headers) for _ in range(5)]
    )
    codes = sorted(r.status_code for r in results)
    assert codes.count(201) == 1 and all(c in (201, 409) for c in codes), codes


async def test_old_failed_login_attempts_are_purged(client: AsyncClient, admin_conn: asyncpg.Connection) -> None:
    stale_hash = uuid.uuid4().hex * 2
    await admin_conn.execute(
        "INSERT INTO login_attempts (id, email_hash, succeeded, created_at) VALUES (gen_random_uuid(), $1, false, $2)",
        stale_hash[:64],
        datetime.now(timezone.utc) - timedelta(days=3),
    )
    acct = await register(client, "Shop A")
    await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})
    left = await admin_conn.fetchval("SELECT count(*) FROM login_attempts WHERE email_hash = $1", stale_hash[:64])
    assert left == 0, "attempts older than the lockout window must be cleaned up"
