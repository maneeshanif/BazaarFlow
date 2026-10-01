"""CRUD operations for the Customer entity.

Every function takes the ``tenant_id`` explicitly and filters on it. This is defense in depth on top
of Postgres row-level security (PRD §3.5). Functions flush but never commit: the request dependency
owns the transaction so the transaction-local ``app.tenant_id`` setting stays in force.
"""
from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


async def get_customers(db: AsyncSession, tenant_id: UUID) -> List[Customer]:
    result = await db.execute(select(Customer).where(Customer.tenant_id == tenant_id))
    return list(result.scalars().all())


async def get_customer_by_phone(db: AsyncSession, tenant_id: UUID, phone: str) -> Optional[Customer]:
    result = await db.execute(
        select(Customer).where(Customer.tenant_id == tenant_id, Customer.phone == phone)
    )
    return result.scalar_one_or_none()


async def upsert_customer(db: AsyncSession, tenant_id: UUID, phone: str, **kwargs: Any) -> Customer:
    customer = await get_customer_by_phone(db, tenant_id, phone)
    if customer:
        for k, v in kwargs.items():
            setattr(customer, k, v)
    else:
        customer = Customer(tenant_id=tenant_id, phone=phone, **kwargs)
        db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer
