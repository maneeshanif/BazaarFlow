"""CRUD operations for the InventoryItem entity.

Every function takes the ``tenant_id`` explicitly and filters on it. This is defense in depth on top
of Postgres row-level security (PRD §3.5). Functions flush but never commit: the request dependency
owns the transaction so the transaction-local ``app.tenant_id`` setting stays in force.
"""
from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryItem


async def get_all_items(db: AsyncSession, tenant_id: UUID) -> List[InventoryItem]:
    result = await db.execute(select(InventoryItem).where(InventoryItem.tenant_id == tenant_id))
    return list(result.scalars().all())


async def get_item_by_sku(db: AsyncSession, tenant_id: UUID, sku: str) -> Optional[InventoryItem]:
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.tenant_id == tenant_id, InventoryItem.sku == sku)
    )
    return result.scalar_one_or_none()


async def create_item(db: AsyncSession, tenant_id: UUID, **kwargs: Any) -> InventoryItem:
    item = InventoryItem(tenant_id=tenant_id, **kwargs)
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def update_item(db: AsyncSession, tenant_id: UUID, sku: str, **kwargs: Any) -> Optional[InventoryItem]:
    item = await get_item_by_sku(db, tenant_id, sku)
    if not item:
        return None
    for k, v in kwargs.items():
        setattr(item, k, v)
    await db.flush()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, tenant_id: UUID, sku: str) -> bool:
    item = await get_item_by_sku(db, tenant_id, sku)
    if not item:
        return False
    await db.delete(item)
    await db.flush()
    return True
