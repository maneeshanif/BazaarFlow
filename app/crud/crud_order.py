"""CRUD operations for the Order entity."""
from __future__ import annotations
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order


async def get_all_orders(db: AsyncSession) -> List[Order]:
    result = await db.execute(select(Order))
    return list(result.scalars().all())


async def get_orders_by_vendor(db: AsyncSession, vendor_id: UUID) -> List[Order]:
    result = await db.execute(select(Order).where(Order.vendor_id == vendor_id))
    return list(result.scalars().all())


async def create_order(db: AsyncSession, **kwargs) -> Order:
    order = Order(**kwargs)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order
