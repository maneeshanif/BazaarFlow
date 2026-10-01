"""CRUD operations for the Vendor (supplier) entity.

Every function takes the ``tenant_id`` explicitly and filters on it. This is defense in depth on top
of Postgres row-level security (PRD §3.5). Functions flush but never commit: the request dependency
owns the transaction so the transaction-local ``app.tenant_id`` setting stays in force.
"""
from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor import Vendor


async def get_vendors(db: AsyncSession, tenant_id: UUID) -> List[Vendor]:
    result = await db.execute(select(Vendor).where(Vendor.tenant_id == tenant_id))
    return list(result.scalars().all())


async def get_vendor_by_id(db: AsyncSession, tenant_id: UUID, vendor_id: UUID) -> Optional[Vendor]:
    result = await db.execute(select(Vendor).where(Vendor.tenant_id == tenant_id, Vendor.id == vendor_id))
    return result.scalar_one_or_none()


async def create_vendor(db: AsyncSession, tenant_id: UUID, **kwargs: Any) -> Vendor:
    vendor = Vendor(tenant_id=tenant_id, **kwargs)
    db.add(vendor)
    await db.flush()
    await db.refresh(vendor)
    return vendor


async def delete_vendor(db: AsyncSession, tenant_id: UUID, vendor_id: UUID) -> bool:
    vendor = await get_vendor_by_id(db, tenant_id, vendor_id)
    if not vendor:
        return False
    await db.delete(vendor)
    await db.flush()
    return True
