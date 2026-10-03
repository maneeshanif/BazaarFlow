"""Delete expired demo shops (PRD F-027: a visitor's temporary shop lives for DEMO_HOURS).

Run it on a schedule (hourly is plenty):

    uv run python -m app.cli.purge_demos

It needs the owner role (``DATABASE_URL_MIGRATIONS``): the application role may not delete from the append-only
stock and ledger tables, and a shop's data goes with the shop. Only tenants with ``demo_expires_at`` in the past are
touched; a real shop can never match because the column is null for it. The throwaway demo owners go too.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.settings import settings
from app.services.demo_service import DEMO_EMAIL_DOMAIN

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("bazaarflow.purge_demos")


async def purge(engine: AsyncEngine, *, now: datetime | None = None) -> int:
    """Delete every demo shop past its expiry. Returns how many shops were removed."""
    cutoff = now or datetime.now(timezone.utc)
    async with engine.begin() as conn:
        ids = [
            row[0]
            for row in (
                await conn.execute(
                    text("SELECT id FROM tenants WHERE demo_expires_at IS NOT NULL AND demo_expires_at < :now"),
                    {"now": cutoff},
                )
            ).all()
        ]
        if not ids:
            return 0
        # audit rows are not tied to the tenant by a foreign key, so they are removed with the shop explicitly
        await conn.execute(text("DELETE FROM audit_logs WHERE tenant_id = ANY(:ids)"), {"ids": ids})
        await conn.execute(text("DELETE FROM tenants WHERE id = ANY(:ids)"), {"ids": ids})
        # the throwaway owners: demo addresses that no longer belong to any shop
        await conn.execute(
            text(
                "DELETE FROM refresh_tokens WHERE user_id IN ("
                " SELECT id FROM users WHERE email LIKE :pattern"
                " AND NOT EXISTS (SELECT 1 FROM memberships m WHERE m.user_id = users.id))"
            ),
            {"pattern": f"%@{DEMO_EMAIL_DOMAIN}"},
        )
        await conn.execute(
            text(
                "DELETE FROM users WHERE email LIKE :pattern AND NOT EXISTS (SELECT 1 FROM memberships m WHERE m.user_id = users.id)"
            ),
            {"pattern": f"%@{DEMO_EMAIL_DOMAIN}"},
        )
    return len(ids)


async def main() -> None:
    engine = create_async_engine(settings.migrations_url, poolclass=NullPool, connect_args={"statement_cache_size": 0})
    try:
        removed = await purge(engine)
    finally:
        await engine.dispose()
    logger.info("removed %d expired demo shop(s)", removed)


if __name__ == "__main__":
    asyncio.run(main())
