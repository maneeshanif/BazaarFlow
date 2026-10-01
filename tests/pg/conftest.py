"""Real-Postgres fixtures for the RLS, auth and schema tests (marker ``pg``).

A throwaway Postgres 16 container is started once per session, the three roles are provisioned the same
way as on Supabase (``app.cli.provision_db``), the Supabase ``anon``/``authenticated`` roles are added with
default grants so the lockdown migration has something to revoke, and Alembic runs as ``migrator``.
The application then connects as ``app_user`` (NOBYPASSRLS), exactly like production.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import asyncpg
import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from alembic import command
from app.cli.provision_db import provision
from app.core import database
from app.core.settings import settings
from app.main import app

ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "bazaarflow"
ADMIN_PW = "admin-pw"
MIGRATOR_PW = "migrator-pw"
APP_PW = "app-pw"
REPORT_PW = "report-pw"


async def _prepare(admin_url: str) -> None:
    conn = await asyncpg.connect(admin_url)
    try:
        # Mimic Supabase: these roles exist and receive default grants on new tables.
        for role in ("anon", "authenticated"):
            await conn.execute(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='{role}') "
                f"THEN CREATE ROLE {role} NOLOGIN; END IF; END $$"
            )
            await conn.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
    finally:
        await conn.close()
    await provision(admin_url, DB_NAME, MIGRATOR_PW, APP_PW, REPORT_PW)
    conn = await asyncpg.connect(admin_url)
    try:
        for role in ("anon", "authenticated"):
            await conn.execute(
                f"ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public GRANT ALL ON TABLES TO {role}"
            )
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def pg_urls() -> Iterator[dict[str, str]]:
    with PostgresContainer("postgres:16", username="postgres", password=ADMIN_PW, dbname=DB_NAME, driver=None) as pg:
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)

        def url(user: str, pw: str, scheme: str = "postgresql+asyncpg") -> str:
            return f"{scheme}://{user}:{pw}@{host}:{port}/{DB_NAME}"

        asyncio.run(_prepare(url("postgres", ADMIN_PW, "postgresql")))

        settings.DATABASE_URL_MIGRATIONS = url("migrator", MIGRATOR_PW)
        cfg = Config(str(ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(ROOT / "alembic"))
        command.upgrade(cfg, "head")

        yield {
            "admin": url("postgres", ADMIN_PW),
            "admin_plain": url("postgres", ADMIN_PW, "postgresql"),
            "app": url("app_user", APP_PW),
            "report": url("report_ro", REPORT_PW),
        }


@pytest_asyncio.fixture
async def app_engine(pg_urls: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    """The application's engine: ``app_user`` over asyncpg, patched into the app's session factory."""
    engine = create_async_engine(pg_urls["app"], poolclass=NullPool, connect_args={"statement_cache_size": 0})
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(database, "AsyncSessionLocal", factory)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(app_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_conn(pg_urls: dict[str, str]) -> AsyncIterator[asyncpg.Connection]:
    """Superuser connection for inspecting catalogs (superusers bypass RLS, so never use it for isolation checks)."""
    conn = await asyncpg.connect(pg_urls["admin_plain"])
    try:
        yield conn
    finally:
        await conn.close()


async def register(client: AsyncClient, shop: str = "Ali Mart", email: str | None = None) -> dict[str, Any]:
    """Register a user + tenant through the real API; returns the token response plus the credentials."""
    email = email or f"owner-{uuid.uuid4().hex[:10]}@example.com"
    password = "correct-horse-battery"
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Owner",
            "email": email,
            "password": password,
            "shop_name": shop,
            "phone": "+923001234567",
            "accept_terms": True,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    return {**body, "email": email, "password": password}


def bearer(account: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {account['access_token']}"}
