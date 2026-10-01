"""CRUD operations for the Message entity.

Every function takes the ``tenant_id`` explicitly and filters on it. This is defense in depth on top
of Postgres row-level security (PRD §3.5). Functions flush but never commit: the request dependency
owns the transaction so the transaction-local ``app.tenant_id`` setting stays in force.
"""
from __future__ import annotations

from typing import Any, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


async def get_messages_by_customer(db: AsyncSession, tenant_id: UUID, customer_id: UUID) -> List[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.tenant_id == tenant_id, Message.customer_id == customer_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def create_message(db: AsyncSession, tenant_id: UUID, **kwargs: Any) -> Message:
    msg = Message(tenant_id=tenant_id, **kwargs)
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg
