"""Provisioning as Supabase does it: the admin (`postgres`) is NOT a superuser, it only has CREATEROLE and owns the
database. Every other provisioning test uses a real superuser, which hides privilege problems that only a hosted
Postgres shows (found on the first real Supabase run: InsufficientPrivilegeError)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from app.cli.provision_db import provision

pytestmark = pytest.mark.pg

SUPER_PW = "super-pw"
ADMIN_PW = "hosted-admin-pw"


@pytest.fixture(scope="module")
def hosted_admin_url() -> Iterator[str]:
    with PostgresContainer("postgres:16", username="postgres", password=SUPER_PW, dbname="postgres", driver=None) as pg:
        host, port = pg.get_container_host_ip(), pg.get_exposed_port(5432)

        async def setup() -> None:
            conn = await asyncpg.connect(f"postgresql://postgres:{SUPER_PW}@{host}:{port}/postgres")
            try:
                # what a hosted provider gives you: a login that can create roles and databases, owns its database
                await conn.execute(f"CREATE ROLE hosted_admin LOGIN CREATEROLE CREATEDB PASSWORD '{ADMIN_PW}'")
                await conn.execute("CREATE DATABASE appdb OWNER hosted_admin")
            finally:
                await conn.close()

        asyncio.run(setup())
        yield f"postgresql://hosted_admin:{ADMIN_PW}@{host}:{port}/appdb"


async def test_provisioning_works_for_a_non_superuser_admin(hosted_admin_url: str) -> None:
    await provision(hosted_admin_url, "appdb", "migrator-pw", "app-pw", "report-pw")
    await provision(hosted_admin_url, "appdb", "migrator-pw-2", "app-pw-2", "report-pw-2")  # and it can be re-run

    conn = await asyncpg.connect(hosted_admin_url)
    try:
        rows = {
            r["rolname"]: r
            for r in await conn.fetch(
                "SELECT rolname, rolsuper, rolbypassrls, rolcanlogin FROM pg_roles "
                "WHERE rolname IN ('migrator', 'app_user', 'report_ro')"
            )
        }
        assert set(rows) == {"migrator", "app_user", "report_ro"}
        assert all(r["rolcanlogin"] and not r["rolsuper"] and not r["rolbypassrls"] for r in rows.values())
    finally:
        await conn.close()


async def test_the_runtime_role_can_use_tables_the_migrator_creates(hosted_admin_url: str) -> None:
    """The point of the default privileges: tables created by migrator are usable by app_user without extra grants."""
    await provision(hosted_admin_url, "appdb", "migrator-pw", "app-pw", "report-pw")
    host_port = hosted_admin_url.split("@")[1]
    migrator = await asyncpg.connect(f"postgresql://migrator:migrator-pw@{host_port}")
    try:
        await migrator.execute("CREATE TABLE public.probe (id int primary key)")
        await migrator.execute("INSERT INTO public.probe VALUES (1)")
    finally:
        await migrator.close()
    app = await asyncpg.connect(f"postgresql://app_user:app-pw@{host_port}")
    try:
        assert await app.fetchval("SELECT count(*) FROM public.probe") == 1
        await app.execute("INSERT INTO public.probe VALUES (2)")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await app.execute("DROP TABLE public.probe")
    finally:
        await app.close()
