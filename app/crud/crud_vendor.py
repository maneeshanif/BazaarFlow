"""CRUD operations for the Vendor entity."""
from __future__ import annotations
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor import Vendor


async def get_all_vendors(db: AsyncSession) -> List[Vendor]:
    result = await db.execute(select(Vendor))
    return list(result.scalars().all())


async def get_vendor_by_id(db: AsyncSession, vendor_id: UUID) -> Optional[Vendor]:
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    return result.scalar_one_or_none()


async def create_vendor(db: AsyncSession, **kwargs) -> Vendor:
    vendor = Vendor(**kwargs)
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return vendor


async def delete_vendor(db: AsyncSession, vendor_id: UUID) -> bool:
    vendor = await get_vendor_by_id(db, vendor_id)
    if not vendor:
        return False
    await db.delete(vendor)
    await db.commit()
    return True
