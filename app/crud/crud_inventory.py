"""CRUD operations for the InventoryItem entity."""
from __future__ import annotations
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryItem


async def get_all_items(db: AsyncSession) -> List[InventoryItem]:
    result = await db.execute(select(InventoryItem))
    return list(result.scalars().all())


async def get_item_by_sku(db: AsyncSession, sku: str) -> Optional[InventoryItem]:
    result = await db.execute(select(InventoryItem).where(InventoryItem.sku == sku))
    return result.scalar_one_or_none()


async def create_item(db: AsyncSession, **kwargs) -> InventoryItem:
    item = InventoryItem(**kwargs)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(db: AsyncSession, sku: str, **kwargs) -> Optional[InventoryItem]:
    item = await get_item_by_sku(db, sku)
    if not item:
        return None
    for k, v in kwargs.items():
        setattr(item, k, v)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, sku: str) -> bool:
    item = await get_item_by_sku(db, sku)
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True
