"""CRUD operations for MarketingPost and ScheduledCampaign entities.

Every function takes the ``tenant_id`` explicitly and filters on it. This is defense in depth on top
of Postgres row-level security (PRD §3.5). Functions flush but never commit: the request dependency
owns the transaction so the transaction-local ``app.tenant_id`` setting stays in force.
"""
from __future__ import annotations

from typing import Any, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketing import MarketingPost, ScheduledCampaign


async def get_posts(db: AsyncSession, tenant_id: UUID) -> List[MarketingPost]:
    result = await db.execute(select(MarketingPost).where(MarketingPost.tenant_id == tenant_id))
    return list(result.scalars().all())


async def get_scheduled_campaigns(db: AsyncSession, tenant_id: UUID) -> List[ScheduledCampaign]:
    result = await db.execute(select(ScheduledCampaign).where(ScheduledCampaign.tenant_id == tenant_id))
    return list(result.scalars().all())


async def create_post(db: AsyncSession, tenant_id: UUID, **kwargs: Any) -> MarketingPost:
    post = MarketingPost(tenant_id=tenant_id, **kwargs)
    db.add(post)
    await db.flush()
    await db.refresh(post)
    return post
