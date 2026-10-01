"""CRUD operations for the User entity (global table: users belong to tenants via memberships)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, password: str, name: str | None = None) -> User:
    user = User(email=email.lower(), hashed_password=hash_password(password), name=name)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
