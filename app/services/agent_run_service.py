"""The agent activity log (PRD F-022) and the shop's AI switch and allowance (build-plan task 64)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.runtime import month_spend_micros, tenant_cap_micros
from app.core.audit import record_audit
from app.core.problems import NotFound
from app.core.settings import settings
from app.core.tenancy import Principal
from app.models.agent_run import AgentRun
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.agent import AgentRunDetail, AgentRunOut, AgentStatus


def _usd(micros: int, places: int = 4) -> str:
    return f"{Decimal(micros) / Decimal(1_000_000):.{places}f}"


def _out(run: AgentRun, user_name: str | None) -> AgentRunOut:
    return AgentRunOut(
        id=run.id,
        user_id=run.user_id,
        user_name=user_name,
        agent=run.agent,
        session_id=run.session_id,
        outcome=run.outcome,  # type: ignore[arg-type]
        input_text=run.input_text,
        output_text=run.output_text,
        tokens_in=run.tokens_in,
        tokens_out=run.tokens_out,
        spend_usd=_usd(run.spend_micros),
        duration_ms=run.duration_ms,
        action_ids=run.action_ids,
        created_at=run.created_at,
    )


async def list_runs(
    db: AsyncSession, principal: Principal, *, outcome: str | None, agent: str | None, limit: int, offset: int
) -> tuple[list[AgentRunOut], int]:
    conditions: list[Any] = [AgentRun.tenant_id == principal.tenant_id]
    if outcome:
        conditions.append(AgentRun.outcome == outcome)
    if agent:
        conditions.append(AgentRun.agent == agent)
    total = (await db.execute(select(func.count()).select_from(select(AgentRun.id).where(*conditions).subquery()))).scalar_one()
    rows = (
        await db.execute(
            select(AgentRun, User.name, User.email)
            .outerjoin(User, User.id == AgentRun.user_id)
            .where(*conditions)
            .order_by(AgentRun.created_at.desc(), AgentRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [_out(r, name or email) for r, name, email in rows], int(total)


async def get_run(db: AsyncSession, principal: Principal, run_id: uuid.UUID) -> AgentRunDetail:
    row = (
        await db.execute(
            select(AgentRun, User.name, User.email)
            .outerjoin(User, User.id == AgentRun.user_id)
            .where(AgentRun.id == run_id, AgentRun.tenant_id == principal.tenant_id)
        )
    ).first()
    if row is None:
        raise NotFound("Agent run")
    run, name, email = row
    return AgentRunDetail(**_out(run, name or email).model_dump(), trace=run.trace_json)


async def status(db: AsyncSession, principal: Principal) -> AgentStatus:
    enabled_row = (await db.execute(select(Tenant.agents_enabled).where(Tenant.id == principal.tenant_id))).scalar_one_or_none()
    spent = await month_spend_micros(db, principal.tenant_id)
    runs = (
        await db.execute(
            select(func.count()).select_from(AgentRun).where(AgentRun.tenant_id == principal.tenant_id)
        )
    ).scalar_one()
    cap = await tenant_cap_micros(db, principal.tenant_id)
    return AgentStatus(
        enabled=bool(enabled_row) and settings.AGENTS_ENABLED,
        month_spend_usd=_usd(spent, 2),
        month_cap_usd=_usd(cap, 2),
        percent_used=int(spent * 100 / cap) if cap > 0 else 0,
        runs_this_month=int(runs),
    )


async def set_switch(db: AsyncSession, principal: Principal, enabled: bool) -> AgentStatus:
    await db.execute(update(Tenant).where(Tenant.id == principal.tenant_id).values(agents_enabled=enabled))
    record_audit(
        db,
        "agents.switched_on" if enabled else "agents.switched_off",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="tenant",
        entity_id=principal.tenant_id,
        after={"agents_enabled": enabled},
    )
    return await status(db, principal)
