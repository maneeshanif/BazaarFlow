"""CRUD operations for MarketingPost and ScheduledCampaign entities."""
from __future__ import annotations
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketing import MarketingPost, ScheduledCampaign


async def get_posts_by_vendor(db: AsyncSession, vendor_id: UUID) -> List[MarketingPost]:
    result = await db.execute(
        select(MarketingPost).where(MarketingPost.vendor_id == vendor_id)
    )
    return list(result.scalars().all())


async def get_campaigns_by_vendor(
    db: AsyncSession, vendor_id: UUID
) -> List[ScheduledCampaign]:
    result = await db.execute(
        select(ScheduledCampaign).where(ScheduledCampaign.vendor_id == vendor_id)
    )
    return list(result.scalars().all())


async def create_post(db: AsyncSession, **kwargs) -> MarketingPost:
    post = MarketingPost(**kwargs)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post
