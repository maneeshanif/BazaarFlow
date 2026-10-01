"""SQLAlchemy 2.0 async engine + session factory.

Automatically uses:
  - Supabase PostgreSQL if DATABASE_URL starts with postgresql
  - Local SQLite (aiosqlite) as a zero-config fallback for development
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import settings, to_async_url


def _build_engine() -> AsyncEngine:
    url = to_async_url(settings.DATABASE_URL)
    connect_args: dict[str, Any] = {}
    kwargs: dict[str, Any] = {}

    if settings.is_sqlite:
        # SQLite needs check_same_thread disabled for async
        connect_args = {"check_same_thread": False}
    else:
        # Supabase's transaction pooler (port 6543) does not support prepared statements, so
        # asyncpg's statement cache must be off (PRD §3.8, RK-09).
        connect_args = {"statement_cache_size": 0}
        kwargs = {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 5}
        url = make_url(url).update_query_dict({"prepared_statement_cache_size": "0"}).render_as_string(
            hide_password=False
        )

    return create_async_engine(
        url,
        echo=not settings.is_production,
        connect_args=connect_args,
        **kwargs,
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
    """FastAPI dependency � yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
