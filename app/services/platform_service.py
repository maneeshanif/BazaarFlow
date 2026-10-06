"""Platform admin (PRD F-025 tenants, D-004 overview): BazaarFlow operators look across shops and suspend one.

Every function here takes the session from ``get_platform_db`` (cross-tenant, audited per request). Reads go through
the narrow ``platform_select`` policies, so only tenants, memberships, orders, agent runs and messages are visible, and
never a shop's customers, products, money or conversations. The only write is a shop's status.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import Conflict, NotFound
from app.core.search import escape_like
from app.core.tenancy import Principal
from app.models.agent_run import AgentRun
from app.models.message import Message
from app.models.order import Order
from app.models.tenant import Membership, Tenant
from app.schemas.dashboard import CountFigure
from app.schemas.platform import PlatformOverview, PlatformTenantOut
from app.services.dashboard_service import _change
from app.services.report_service import SHOP_TZ

MICROS = Decimal(1_000_000)


async def _row(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise NotFound("Shop")
    return tenant


async def _decorate(db: AsyncSession, tenants: list[Tenant]) -> list[PlatformTenantOut]:
    ids = [t.id for t in tenants]
    users: dict[uuid.UUID, int] = {}
    last: dict[uuid.UUID, datetime] = {}
    if ids:
        users = {
            tid: int(n)
            for tid, n in (
                await db.execute(
                    select(Membership.tenant_id, func.count()).where(Membership.tenant_id.in_(ids)).group_by(Membership.tenant_id)
                )
            ).all()
        }
        for table in (Order, AgentRun, Message):
            for tid, at in (
                await db.execute(select(table.tenant_id, func.max(table.created_at)).where(table.tenant_id.in_(ids)).group_by(table.tenant_id))
            ).all():
                if at is not None and (tid not in last or at > last[tid]):
                    last[tid] = at
    return [
        PlatformTenantOut(
            id=t.id,
            name=t.name,
            slug=t.slug,
            plan=t.plan,
            status=t.status,  # type: ignore[arg-type]
            city=t.city,
            is_demo=t.demo_expires_at is not None,
            onboarding_state=t.onboarding_state,
            agents_enabled=t.agents_enabled,
            users=users.get(t.id, 0),
            last_activity_at=last.get(t.id),
            created_at=t.created_at,
        )
        for t in tenants
    ]


async def list_tenants(
    db: AsyncSession, *, q: str | None, status: str | None, include_demo: bool, limit: int, offset: int
) -> tuple[list[PlatformTenantOut], int]:
    conditions: list[Any] = []
    if q:
        like = f"%{escape_like(q.strip())}%"
        conditions.append(or_(Tenant.name.ilike(like, escape="\\"), Tenant.slug.ilike(like, escape="\\")))
    if status:
        conditions.append(Tenant.status == status)
    if not include_demo:
        conditions.append(Tenant.demo_expires_at.is_(None))
    total = (await db.execute(select(func.count()).select_from(Tenant).where(*conditions))).scalar_one()
    rows = (
        await db.execute(select(Tenant).where(*conditions).order_by(Tenant.created_at.desc(), Tenant.id).limit(limit).offset(offset))
    ).scalars().all()
    return await _decorate(db, list(rows)), int(total)


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> PlatformTenantOut:
    return (await _decorate(db, [await _row(db, tenant_id)]))[0]


async def set_status(
    db: AsyncSession, principal: Principal, tenant_id: uuid.UUID, *, status: str, reason: str | None
) -> PlatformTenantOut:
    """Suspend or reactivate a shop. An operator cannot lock their own shop (they could not undo it from inside)."""
    if status == "suspended" and tenant_id == principal.tenant_id:
        raise Conflict("You cannot suspend the shop you are signed in to", code="cannot_suspend_own_shop")
    tenant = await _row(db, tenant_id)
    before = tenant.status
    if before != status:
        tenant.status = status
        await db.flush()
        record_audit(
            db,
            "platform.tenant_suspended" if status == "suspended" else "platform.tenant_reactivated",
            tenant_id=None,
            actor_id=principal.user_id,
            entity="tenant",
            entity_id=tenant.id,
            before={"status": before},
            after={"status": status, "reason": reason, "name": tenant.name},
        )
        await db.refresh(tenant)
    return (await _decorate(db, [tenant]))[0]


async def overview(db: AsyncSession, *, now: datetime | None = None) -> PlatformOverview:
    now_utc = now or datetime.now(timezone.utc)
    week_ago = now_utc - timedelta(days=7)
    local = now_utc.astimezone(SHOP_TZ)
    today_start = datetime.combine(local.date(), datetime.min.time(), tzinfo=SHOP_TZ).astimezone(timezone.utc)

    real = Tenant.demo_expires_at.is_(None)
    total = int((await db.execute(select(func.count()).select_from(Tenant).where(real))).scalar_one())
    before = int((await db.execute(select(func.count()).select_from(Tenant).where(real, Tenant.created_at < week_ago))).scalar_one())
    demos = int((await db.execute(select(func.count()).select_from(Tenant).where(~real))).scalar_one())

    active_ids = union(
        select(Order.tenant_id).where(Order.created_at >= week_ago),
        select(AgentRun.tenant_id).where(AgentRun.created_at >= week_ago),
        select(Message.tenant_id).where(Message.created_at >= week_ago),
    ).subquery()
    active = int(
        (
            await db.execute(
                select(func.count()).select_from(active_ids).join(Tenant, Tenant.id == active_ids.c.tenant_id).where(real)
            )
        ).scalar_one()
    )

    messages_today = int((await db.execute(select(func.count()).select_from(Message).where(Message.created_at >= today_start))).scalar_one())
    messages_week = int((await db.execute(select(func.count()).select_from(Message).where(Message.created_at >= week_ago))).scalar_one())

    month_start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    spend = (
        await db.execute(select(func.coalesce(func.sum(AgentRun.spend_micros), 0)).where(AgentRun.created_at >= month_start))
    ).scalar_one()
    runs, failed = (
        await db.execute(
            select(func.count(), func.count().filter(AgentRun.outcome == "failed")).select_from(AgentRun).where(AgentRun.created_at >= week_ago)
        )
    ).one()

    return PlatformOverview(
        tenants=CountFigure(value=total, previous=before, change_percent=_change(total, before)),
        demo_tenants=demos,
        active_tenants_7d=active,
        messages_today=messages_today,
        messages_per_day_7d=int(round(messages_week / 7)),
        ai_spend_month_usd=(Decimal(int(spend)) / MICROS).quantize(Decimal("0.01")),
        agent_runs_7d=int(runs),
        error_rate_percent=int(round(int(failed) * 100 / int(runs))) if runs else None,
        is_empty=total == 0 and demos == 0,
        generated_at=now_utc,
    )
