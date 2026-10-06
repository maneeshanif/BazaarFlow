"""Marketing schedule (PRD F-015) and marketing activity (F-016): the shop's posting plan and what happened to each post.

The schedule is one row per shop; the scheduler (``marketing_publisher``) reads it. The activity list shows every post
that is on its way to Facebook or has been there: waiting for approval, approved, queued, published, failed (with the
reason) or cancelled, and lets a manager put an approved post in the queue, retry a failed one or cancel a queued one.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import Conflict, NotFound
from app.core.tenancy import Principal
from app.models.marketing import MarketingPost
from app.models.marketing_schedule import MarketingSchedule
from app.models.tenant import TenantIntegration
from app.schemas.marketing_schedule import ActivityOut, ActivityStatus, ScheduleIn, ScheduleOut

ACTIVITY_STATES: tuple[str, ...] = ("pending_approval", "approved", "queued", "published", "failed", "cancelled")
PAST_TOLERANCE = timedelta(minutes=1)


async def _facebook_connected(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
    status = (
        await db.execute(
            select(TenantIntegration.status).where(TenantIntegration.tenant_id == tenant_id, TenantIntegration.provider == "facebook")
        )
    ).scalar_one_or_none()
    return status == "connected"


async def _next_post_at(db: AsyncSession, tenant_id: uuid.UUID) -> datetime | None:
    return (
        await db.execute(
            select(func.min(MarketingPost.scheduled_for)).where(MarketingPost.tenant_id == tenant_id, MarketingPost.status == "queued")
        )
    ).scalar_one()


def _out(row: MarketingSchedule | None, *, connected: bool, next_at: datetime | None) -> ScheduleOut:
    if row is None:
        return ScheduleOut(enabled=False, configured=False, facebook_connected=connected, next_post_at=next_at)
    return ScheduleOut(
        enabled=row.enabled,
        goal=row.goal,  # type: ignore[arg-type]
        notes=row.notes,
        tone=row.tone,  # type: ignore[arg-type]
        language=row.language,  # type: ignore[arg-type]
        posts_per_day=row.posts_per_day,
        window_start=row.window_start,
        window_end=row.window_end,
        approval_mode=row.approval_mode,  # type: ignore[arg-type]
        configured=True,
        facebook_connected=connected,
        next_post_at=next_at,
    )


async def get_schedule(db: AsyncSession, principal: Principal) -> ScheduleOut:
    row = (await db.execute(select(MarketingSchedule).where(MarketingSchedule.tenant_id == principal.tenant_id))).scalar_one_or_none()
    return _out(row, connected=await _facebook_connected(db, principal.tenant_id), next_at=await _next_post_at(db, principal.tenant_id))


async def put_schedule(db: AsyncSession, principal: Principal, body: ScheduleIn) -> ScheduleOut:
    connected = await _facebook_connected(db, principal.tenant_id)
    if body.enabled and not connected:
        raise Conflict("Connect your Facebook page first: posts need somewhere to go.", code="facebook_not_connected")
    row = (await db.execute(select(MarketingSchedule).where(MarketingSchedule.tenant_id == principal.tenant_id))).scalar_one_or_none()
    before = None
    if row is None:
        row = MarketingSchedule(tenant_id=principal.tenant_id)
        db.add(row)
    else:
        before = {"enabled": row.enabled, "posts_per_day": row.posts_per_day, "approval_mode": row.approval_mode}
    for field, value in body.model_dump().items():
        setattr(row, field, value)
    await db.flush()
    record_audit(
        db,
        "marketing.schedule_saved",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="marketing_schedule",
        entity_id=row.id,
        before=before,
        after={"enabled": row.enabled, "posts_per_day": row.posts_per_day, "approval_mode": row.approval_mode, "goal": row.goal},
    )
    return _out(row, connected=connected, next_at=await _next_post_at(db, principal.tenant_id))


def _activity(post: MarketingPost) -> ActivityOut:
    return ActivityOut(
        id=post.id,
        title=post.title or "",
        message=post.message or "",
        status=post.status,  # type: ignore[arg-type]
        source=post.source,  # type: ignore[arg-type]
        scheduled_for=post.scheduled_for,
        published_at=post.published_at,
        attempts=post.attempts,
        last_error=post.last_error,
        created_at=post.created_at,
    )


async def list_activity(
    db: AsyncSession, principal: Principal, *, status: ActivityStatus | None, limit: int, offset: int
) -> tuple[list[ActivityOut], int]:
    conditions: list[Any] = [MarketingPost.tenant_id == principal.tenant_id, MarketingPost.status.in_((status,) if status else ACTIVITY_STATES)]
    total = (await db.execute(select(func.count()).select_from(MarketingPost).where(*conditions))).scalar_one()
    when = func.coalesce(MarketingPost.scheduled_for, MarketingPost.created_at)
    rows = (
        await db.execute(select(MarketingPost).where(*conditions).order_by(when.desc(), MarketingPost.id).limit(limit).offset(offset))
    ).scalars().all()
    return [_activity(p) for p in rows], int(total)


async def _post(db: AsyncSession, principal: Principal, post_id: uuid.UUID) -> MarketingPost:
    post = (
        await db.execute(
            select(MarketingPost).where(MarketingPost.id == post_id, MarketingPost.tenant_id == principal.tenant_id).with_for_update()
        )
    ).scalar_one_or_none()
    if post is None:
        raise NotFound("Post")
    return post


async def queue_post(db: AsyncSession, principal: Principal, post_id: uuid.UUID, when: datetime) -> ActivityOut:
    """Put an approved post in the publishing queue for ``when``."""
    post = await _post(db, principal, post_id)
    if post.status != "approved":
        raise Conflict("Only an approved post can be scheduled.", code="not_approved")
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if when < datetime.now(timezone.utc) - PAST_TOLERANCE:
        raise Conflict("Pick a time that has not passed yet.", code="time_in_the_past")
    if not await _facebook_connected(db, principal.tenant_id):
        raise Conflict("Connect your Facebook page first: posts need somewhere to go.", code="facebook_not_connected")
    post.status, post.scheduled_for, post.attempts, post.last_error = "queued", when, 0, None
    await db.flush()
    record_audit(
        db,
        "marketing.post_queued",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="marketing_post",
        entity_id=post.id,
        after={"scheduled_for": when.isoformat()},
    )
    return _activity(post)


async def retry_post(db: AsyncSession, principal: Principal, post_id: uuid.UUID) -> ActivityOut:
    post = await _post(db, principal, post_id)
    if post.status != "failed":
        raise Conflict("Only a failed post can be retried.", code="not_failed")
    post.status, post.scheduled_for, post.attempts, post.last_error = "queued", datetime.now(timezone.utc), 0, None
    await db.flush()
    record_audit(
        db, "marketing.post_retried", tenant_id=principal.tenant_id, actor_id=principal.user_id, entity="marketing_post", entity_id=post.id
    )
    return _activity(post)


async def cancel_post(db: AsyncSession, principal: Principal, post_id: uuid.UUID) -> ActivityOut:
    post = await _post(db, principal, post_id)
    if post.status not in {"queued", "approved"}:
        raise Conflict("Only a queued or approved post can be cancelled. A post waiting for approval is rejected in Approvals.", code="not_cancellable")
    post.status = "cancelled"
    await db.flush()
    record_audit(
        db, "marketing.post_cancelled", tenant_id=principal.tenant_id, actor_id=principal.user_id, entity="marketing_post", entity_id=post.id
    )
    return _activity(post)


# kept for the schedule form: the default window shown before anything is saved
DEFAULT_WINDOW = (time(10, 0), time(20, 0))
