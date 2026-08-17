"""SQLAlchemy 2.0 async engine + session factory.

Automatically uses:
  - Supabase PostgreSQL if DATABASE_URL starts with postgresql
  - Local SQLite (aiosqlite) as a zero-config fallback for development
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import settings


def _build_engine():
    url = settings.DATABASE_URL
    connect_args = {}

    if settings.is_sqlite:
        # SQLite needs check_same_thread disabled for async
        connect_args = {"check_same_thread": False}

    return create_async_engine(
        url,
        echo=not settings.is_production,
        connect_args=connect_args,
    )


engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
