"""Prepares the local development database (run by `docker compose -f docker-compose.dev.yml up`).

Idempotent: creates the Supabase-style roles, provisions migrator / app_user / report_ro, migrates to head and seeds the
demo shop. Local development only; every password here is a throwaway.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import asyncpg

from app.cli.provision_db import provision

ADMIN_URL = os.environ["DEV_ADMIN_URL"]
DB_NAME = os.environ.get("DEV_DB_NAME", "bazaarflow")


async def prepare() -> None:
    conn = await asyncpg.connect(ADMIN_URL)
    try:
        # Supabase has these roles already; the migrations revoke from them.
        for role in ("anon", "authenticated"):
            await conn.execute(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='{role}') "
                f"THEN CREATE ROLE {role} NOLOGIN; END IF; END $$"
            )
            await conn.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
    finally:
        await conn.close()
    await provision(
        ADMIN_URL,
        DB_NAME,
        os.environ["MIGRATOR_PASSWORD"],
        os.environ["APP_USER_PASSWORD"],
        os.environ["REPORT_RO_PASSWORD"],
    )


def run(*cmd: str) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    asyncio.run(prepare())
    run("alembic", "upgrade", "head")
    run(sys.executable, "-m", "app.cli.seed")
    print("database ready", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
