"""Read-only async database engine.

Used by analytics and logs endpoints so they can never accidentally
write to the database.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import settings

# Build a read-only DATABASE_URL by appending the sslmode hint
_RO_URL = settings.DATABASE_URL

_ro_engine = create_async_engine(
    _RO_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    execution_options={"readonly": True},  # psycopg3 / asyncpg honour this
)

AsyncROSession = async_sessionmaker(
    _ro_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_ro_db():
    """FastAPI dependency � yields a read-only DB session."""
    async with AsyncROSession() as session:
        yield session
