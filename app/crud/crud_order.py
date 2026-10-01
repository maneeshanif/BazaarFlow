"""CRUD operations for the Order entity.

Every function takes the ``tenant_id`` explicitly and filters on it. This is defense in depth on top
of Postgres row-level security (PRD §3.5). Functions flush but never commit: the request dependency
owns the transaction so the transaction-local ``app.tenant_id`` setting stays in force.
"""
from __future__ import annotations

from typing import Any, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order


async def get_orders(db: AsyncSession, tenant_id: UUID) -> List[Order]:
    result = await db.execute(select(Order).where(Order.tenant_id == tenant_id))
    return list(result.scalars().all())


async def create_order(db: AsyncSession, tenant_id: UUID, **kwargs: Any) -> Order:
    order = Order(tenant_id=tenant_id, **kwargs)
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return order
