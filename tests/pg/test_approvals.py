"""The agent approval queue against real Postgres (PRD §36.7, W-005)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.agents.context import ToolContext
from app.core.tenancy import tenant_session
from app.models.agent import ActionStatus
from app.models.tenant import TenantRole
from app.services import approvals
from tests.pg.conftest import register

pytestmark = pytest.mark.pg


@asynccontextmanager
async def _ctx(tenant_id: str, role: TenantRole) -> AsyncIterator[ToolContext]:
    async with tenant_session(uuid.UUID(tenant_id), uuid.uuid4()) as session:
        yield ToolContext(tenant_id=uuid.UUID(tenant_id), user_id=uuid.uuid4(), role=role, session=session)


async def _file(tenant_id: str, payload: dict[str, Any] | None = None) -> uuid.UUID:
    async with _ctx(tenant_id, TenantRole.staff) as ctx:
        action = await approvals.request_action(
            ctx,
            agent="sales",
            tool="post_order",
            summary="Sell 5 shirts to Ali",
            payload=payload or {"sku": "SHIRT-1", "qty": 5},
        )
        return action.id


async def test_a_requested_action_is_pending_and_audited(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    action_id = await _file(acct["tenant_id"])
    async with _ctx(acct["tenant_id"], TenantRole.manager) as ctx:
        action = await approvals._get(ctx, action_id)
        assert action.status == ActionStatus.pending.value
        assert action.payload_hash == approvals.payload_hash({"sku": "SHIRT-1", "qty": 5})
        rows = (await ctx.session.execute(text("SELECT action FROM audit_logs"))).all()
        assert "agent.action_requested" in {r[0] for r in rows}


async def test_staff_cannot_decide_but_a_manager_can_and_execution_runs_the_stored_payload_once(
    client: AsyncClient, app_engine: AsyncEngine
) -> None:
    acct = await register(client, "Shop A")
    action_id = await _file(acct["tenant_id"])
    executed: list[dict[str, Any]] = []

    async def executor(payload: dict[str, Any]) -> None:
        executed.append(payload)

    async with _ctx(acct["tenant_id"], TenantRole.staff) as ctx:
        with pytest.raises(PermissionError):
            await approvals.decide(ctx, action_id, approve=True)

    async with _ctx(acct["tenant_id"], TenantRole.manager) as ctx:
        # nothing runs before approval
        with pytest.raises(approvals.ApprovalError):
            await approvals.execute(ctx, action_id, executor)
        await approvals.decide(ctx, action_id, approve=True, note="ok")
        done = await approvals.execute(ctx, action_id, executor)
        assert done.status == ActionStatus.executed.value
        # and it cannot run twice
        with pytest.raises(approvals.ApprovalError):
            await approvals.execute(ctx, action_id, executor)
    assert executed == [{"sku": "SHIRT-1", "qty": 5}]


async def test_a_rejected_action_never_executes(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    action_id = await _file(acct["tenant_id"])
    async with _ctx(acct["tenant_id"], TenantRole.owner) as ctx:
        await approvals.decide(ctx, action_id, approve=False, note="no")

        async def executor(payload: dict[str, Any]) -> None:
            raise AssertionError("must not run")

        with pytest.raises(approvals.ApprovalError):
            await approvals.execute(ctx, action_id, executor)


async def test_a_tampered_payload_is_refused_at_execution(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    action_id = await _file(acct["tenant_id"])
    async with _ctx(acct["tenant_id"], TenantRole.manager) as ctx:
        await approvals.decide(ctx, action_id, approve=True)
        await ctx.session.execute(
            text("UPDATE agent_actions SET payload_json = CAST(:p AS json) WHERE id = :i"),
            {"p": '{"sku": "SHIRT-1", "qty": 5000}', "i": action_id},
        )
        ran = False

        async def executor(payload: dict[str, Any]) -> None:
            nonlocal ran
            ran = True

        with pytest.raises(approvals.ApprovalError, match="hash"):
            await approvals.execute(ctx, action_id, executor)
        assert ran is False


async def test_an_expired_action_cannot_be_approved(client: AsyncClient, app_engine: AsyncEngine) -> None:
    acct = await register(client, "Shop A")
    async with _ctx(acct["tenant_id"], TenantRole.staff) as ctx:
        action = await approvals.request_action(
            ctx, agent="sales", tool="post_order", summary="old", payload={"a": 1}, ttl_hours=-1
        )
        action_id = action.id
    async with _ctx(acct["tenant_id"], TenantRole.owner) as ctx:
        with pytest.raises(approvals.ApprovalError, match="expired"):
            await approvals.decide(ctx, action_id, approve=True)


async def test_another_tenant_cannot_see_or_decide_the_action(client: AsyncClient, app_engine: AsyncEngine) -> None:
    a = await register(client, "Shop A")
    b = await register(client, "Shop B")
    action_id = await _file(a["tenant_id"])
    async with _ctx(b["tenant_id"], TenantRole.owner) as ctx:
        with pytest.raises(approvals.ApprovalError, match="not found"):
            await approvals.decide(ctx, action_id, approve=True)
        assert (await ctx.session.execute(text("SELECT count(*) FROM agent_actions"))).scalar_one() == 0
