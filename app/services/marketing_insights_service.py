"""Marketing insights (PRD F-017): posts published, failed and queued, a daily trend, and comment counts from Facebook.

The counts come from our own posts table, so they are exact. Comment counts are fetched live for the latest published
posts, best effort: when Facebook is not connected, refuses the token or does not answer, the page still shows everything
else and says engagement is unavailable and why (the provider failure is recorded like any other).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.problems import DomainError
from app.core.tenancy import Principal
from app.integrations.http import ProviderError
from app.models.marketing import MarketingPost
from app.schemas.dashboard import CountFigure, DashboardRange
from app.schemas.marketing_insights import InsightDay, MarketingInsights, TopPost
from app.services import integration_service
from app.services.dashboard_service import _change, bounds
from app.services.report_service import SHOP_TZ

TOP = 5


async def _count(db: AsyncSession, tenant_id: uuid.UUID, status: str, start: datetime | None = None, end: datetime | None = None) -> int:
    when = MarketingPost.published_at if status == "published" else MarketingPost.updated_at
    conditions = [MarketingPost.tenant_id == tenant_id, MarketingPost.status == status]
    if start is not None and end is not None:
        conditions += [when >= start, when < end]
    return int((await db.execute(select(func.count()).select_from(MarketingPost).where(*conditions))).scalar_one())


async def insights(db: AsyncSession, principal: Principal, range_: DashboardRange, *, now: datetime | None = None) -> MarketingInsights:
    tenant = principal.tenant_id
    moment = now or datetime.now(timezone.utc)
    (start, end), (prev_start, prev_end) = bounds(range_, moment)
    published = await _count(db, tenant, "published", start, end)
    before = await _count(db, tenant, "published", prev_start, prev_end)
    failed = await _count(db, tenant, "failed", start, end)
    queued = await _count(db, tenant, "queued")
    from_schedule = int(
        (
            await db.execute(
                select(func.count())
                .select_from(MarketingPost)
                .where(
                    MarketingPost.tenant_id == tenant,
                    MarketingPost.status == "published",
                    MarketingPost.source == "schedule",
                    MarketingPost.published_at >= start,
                    MarketingPost.published_at < end,
                )
            )
        ).scalar_one()
    )

    days = 30 if range_ == "30d" else 7
    local_today = moment.astimezone(SHOP_TZ).date()
    first = local_today - timedelta(days=days - 1)
    window_start = datetime.combine(first, datetime.min.time(), tzinfo=SHOP_TZ).astimezone(timezone.utc)
    local_day = func.date(func.timezone("Asia/Karachi", MarketingPost.published_at))
    found: dict[date, int] = {
        d: int(n)
        for d, n in (
            await db.execute(
                select(local_day, func.count())
                .where(MarketingPost.tenant_id == tenant, MarketingPost.status == "published", MarketingPost.published_at >= window_start)
                .group_by(local_day)
            )
        ).all()
    }
    trend = [InsightDay(day=first + timedelta(days=i), published=found.get(first + timedelta(days=i), 0)) for i in range(days)]

    latest = (
        await db.execute(
            select(MarketingPost)
            .where(MarketingPost.tenant_id == tenant, MarketingPost.status == "published", MarketingPost.fb_post_id.is_not(None))
            .order_by(MarketingPost.published_at.desc(), MarketingPost.id)
            .limit(TOP)
        )
    ).scalars().all()
    top = [TopPost(id=p.id, title=p.title or "", published_at=p.published_at or p.created_at, comments=None) for p in latest]
    engagement, note = "unavailable", None
    try:
        adapter = await integration_service.adapter_for(db, tenant, "facebook")
    except DomainError as error:
        engagement, note = "not_connected", error.detail
    else:
        try:
            for item, post in zip(top, latest, strict=True):
                item.comments = len(await adapter.fetch_comments(str(post.fb_post_id)))
            engagement = "available"
        except ProviderError as error:
            await integration_service.record_failure(db, tenant, "facebook", error)
            note = "Facebook did not answer, so comment counts are not shown right now."
        finally:
            await adapter.aclose()

    total_posts = int(
        (
            await db.execute(
                select(func.count())
                .select_from(MarketingPost)
                .where(MarketingPost.tenant_id == tenant, MarketingPost.status.in_(("published", "failed", "queued")))
            )
        ).scalar_one()
    )
    return MarketingInsights(
        range=range_,
        published=CountFigure(value=published, previous=before, change_percent=_change(published, before)),
        failed=failed,
        queued=queued,
        success_percent=int(round(published * 100 / (published + failed))) if published + failed else None,
        from_schedule=from_schedule,
        trend=trend,
        top_posts=top,
        engagement=engagement,  # type: ignore[arg-type]
        engagement_note=note,
        is_empty=total_posts == 0,
        generated_at=moment,
    )
