"""Tenant context for database sessions (PRD §3.5, §3.8).

Isolation is enforced twice: CRUD functions filter on ``tenant_id`` explicitly, and Postgres
row-level security refuses rows whose ``tenant_id`` differs from the transaction-local setting
``app.tenant_id``. If the setting is missing the policies match nothing (fail closed).

``set_config(..., true)`` is transaction-local, which is what makes this safe behind the Supabase
transaction pooler: the value can never leak to another request that reuses the connection.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database
from app.models.tenant import TenantRole


@dataclass(frozen=True)
class Principal:
    """The authenticated caller, built from the verified JWT claims."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: TenantRole
    is_platform_admin: bool = False


def _is_postgres(session: AsyncSession) -> bool:
    bind = session.get_bind()
    return bind.dialect.name == "postgresql"


async def apply_context(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> None:
    """Set the transaction-local tenant/user context that the RLS policies read.

    A no-op on SQLite, which has no row-level security (SQLite is for fast unit tests only).
    """
    if not _is_postgres(session):
        return
    if tenant_id is not None:
        await session.execute(text("SELECT set_config('app.tenant_id', :v, true)"), {"v": str(tenant_id)})
    if user_id is not None:
        await session.execute(text("SELECT set_config('app.user_id', :v, true)"), {"v": str(user_id)})


@asynccontextmanager
async def tenant_session(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> AsyncIterator[AsyncSession]:
    """Open a transaction scoped to one tenant; commit on success, roll back on error."""
    async with database.AsyncSessionLocal() as session:
        async with session.begin():
            await apply_context(session, tenant_id=tenant_id, user_id=user_id)
            yield session


@asynccontextmanager
async def anonymous_session(user_id: uuid.UUID | None = None) -> AsyncIterator[AsyncSession]:
    """A transaction with no tenant (login, registration). RLS exposes only the caller's own rows."""
    async with database.AsyncSessionLocal() as session:
        async with session.begin():
            await apply_context(session, user_id=user_id)
            yield session
