"""The agent command center (PRD D-003): how much the AI did, how often people agreed, what it cost, what it saved.

Figures come straight from ``agent_runs`` and ``agent_actions``. The time saved is an estimate with a stated rule
(``MINUTES_PER_OK_RUN`` per run that finished and ``MINUTES_PER_EXECUTED_ACTION`` per approved action that ran), shown
beside the number so nobody mistakes it for a measurement.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import Principal
from app.models.agent import ActionStatus, AgentAction
from app.models.agent_run import AgentRun
from app.schemas.agent import AgentApprovalRate, AgentDashboard, AgentSpend, AgentTimeSaved
from app.schemas.dashboard import CountFigure, DashboardRange
from app.services import agent_run_service
from app.services.dashboard_service import _change, bounds

MINUTES_PER_OK_RUN = 2
MINUTES_PER_EXECUTED_ACTION = 3
APPROVED_STATES = (ActionStatus.approved.value, ActionStatus.executed.value, ActionStatus.failed.value)


async def _runs(db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime, outcome: str | None = None) -> int:
    conditions = [AgentRun.tenant_id == tenant_id, AgentRun.created_at >= start, AgentRun.created_at < end]
    if outcome is not None:
        conditions.append(AgentRun.outcome == outcome)
    return int((await db.execute(select(func.count()).select_from(AgentRun).where(*conditions))).scalar_one())


async def _actions(db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime, states: tuple[str, ...]) -> int:
    return int(
        (
            await db.execute(
                select(func.count())
                .select_from(AgentAction)
                .where(
                    AgentAction.tenant_id == tenant_id,
                    AgentAction.created_at >= start,
                    AgentAction.created_at < end,
                    AgentAction.status.in_(states),
                )
            )
        ).scalar_one()
    )


async def dashboard(db: AsyncSession, principal: Principal, range_: DashboardRange, *, now: datetime | None = None) -> AgentDashboard:
    tenant = principal.tenant_id
    now_utc = now or datetime.now(timezone.utc)
    (start, end), (prev_start, prev_end) = bounds(range_, now_utc)
    (today_start, today_end), _ = bounds("today", now_utc)

    runs = await _runs(db, tenant, start, end)
    runs_before = await _runs(db, tenant, prev_start, prev_end)
    failed = await _runs(db, tenant, start, end, "failed")
    failed_before = await _runs(db, tenant, prev_start, prev_end, "failed")
    ok_runs = await _runs(db, tenant, start, end, "ok")

    approved = await _actions(db, tenant, start, end, APPROVED_STATES)
    rejected = await _actions(db, tenant, start, end, (ActionStatus.rejected.value,))
    executed = await _actions(db, tenant, start, end, (ActionStatus.executed.value,))
    decided = approved + rejected

    status = await agent_run_service.status(db, principal)
    ever = (await db.execute(select(func.count()).select_from(AgentRun).where(AgentRun.tenant_id == tenant))).scalar_one()
    return AgentDashboard(
        range=range_,
        runs_today=await _runs(db, tenant, today_start, today_end),
        runs=CountFigure(value=runs, previous=runs_before, change_percent=_change(runs, runs_before)),
        failed_runs=CountFigure(value=failed, previous=failed_before, change_percent=_change(failed, failed_before)),
        approval=AgentApprovalRate(
            approved=approved, rejected=rejected, rate_percent=int(round(approved * 100 / decided)) if decided else None
        ),
        spend=AgentSpend(month_spend_usd=status.month_spend_usd, month_cap_usd=status.month_cap_usd, percent_used=status.percent_used),
        time_saved=AgentTimeSaved(
            minutes=ok_runs * MINUTES_PER_OK_RUN + executed * MINUTES_PER_EXECUTED_ACTION,
            ok_runs=ok_runs,
            executed_actions=executed,
            assumption=(
                f"Estimate: {MINUTES_PER_OK_RUN} minutes for every chat the AI finished and "
                f"{MINUTES_PER_EXECUTED_ACTION} minutes for every approved action it carried out."
            ),
        ),
        enabled=status.enabled,
        is_empty=ever == 0,
        generated_at=now_utc,
    )
