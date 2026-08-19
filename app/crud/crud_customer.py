"""CRUD operations for the Customer entity."""
from __future__ import annotations
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


async def get_customers_by_vendor(db: AsyncSession, vendor_id: UUID) -> List[Customer]:
    result = await db.execute(select(Customer).where(Customer.vendor_id == vendor_id))
    return list(result.scalars().all())


async def get_customer_by_phone(
    db: AsyncSession, vendor_id: UUID, phone: str
) -> Optional[Customer]:
    result = await db.execute(
        select(Customer).where(
            Customer.vendor_id == vendor_id, Customer.phone == phone
        )
    )
    return result.scalar_one_or_none()


async def upsert_customer(
    db: AsyncSession, vendor_id: UUID, phone: str, **kwargs
) -> Customer:
    customer = await get_customer_by_phone(db, vendor_id, phone)
    if customer:
        for k, v in kwargs.items():
            setattr(customer, k, v)
    else:
        customer = Customer(vendor_id=vendor_id, phone=phone, **kwargs)
        db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer
