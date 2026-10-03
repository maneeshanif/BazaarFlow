"""Task 58: a backup can be restored, completely and inside the recovery target (PRD §18: RTO 4 h, RPO 24 h).

The drill uses the same commands as ``scripts/backup.sh`` (custom-format ``pg_dump``, ``pg_restore``) inside the
throwaway Postgres container: dump a database holding two demo shops, restore it into a fresh database, then check that
every table has the same number of rows, that row level security is still on and forced, and that the policies work
(one shop's session still sees only its own rows). The restore is timed and compared with the target.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Iterator
from urllib.parse import urlparse

import asyncpg
import pytest
from httpx import AsyncClient

from tests.pg.agent_support import scripted_provider as scripted_provider  # noqa: F401  (autouse fixture)
from tests.pg.conftest import ADMIN_PW, DB_NAME, bearer

pytestmark = pytest.mark.pg

RTO_SECONDS = 4 * 3600  # PRD §18


def docker(*args: str, check: bool = True) -> str:
    done = subprocess.run(["docker", *args], capture_output=True, text=True, check=False)
    if check and done.returncode != 0:
        raise AssertionError(f"docker {' '.join(args[:3])} failed: {done.stderr.strip()[:400]}")
    return done.stdout


@pytest.fixture
def container(pg_urls: dict[str, str]) -> Iterator[str]:
    port = urlparse(pg_urls["admin_plain"]).port
    rows = [line.split(" ", 1) for line in docker("ps", "--format", "{{.Names}} {{.Ports}}").splitlines() if " " in line]
    names = [name for name, ports in rows if f":{port}->" in ports]
    assert names, "the throwaway Postgres container was not found"
    yield names[0]
    docker("exec", names[0], "rm", "-f", "/tmp/drill.dump", check=False)


async def table_counts(url: str) -> dict[str, int]:
    conn = await asyncpg.connect(url)
    try:
        tables = [
            r["tablename"]
            for r in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")
        ]
        return {t: await conn.fetchval(f'SELECT count(*) FROM "{t}"') for t in tables}
    finally:
        await conn.close()


async def test_a_backup_restores_completely_inside_the_recovery_target(
    client: AsyncClient, pg_urls: dict[str, str], container: str
) -> None:
    a = (await client.post("/api/v1/demo/start")).json()
    b = (await client.post("/api/v1/demo/start")).json()
    admin = pg_urls["admin_plain"]
    before = await table_counts(admin)
    assert before["orders"] >= 10 and before["tenants"] >= 2

    env = ("-e", f"PGPASSWORD={ADMIN_PW}")
    started = time.monotonic()
    docker(
        "exec",
        *env,
        container,
        "pg_dump",
        "-U",
        "postgres",
        "-Fc",
        "--no-owner",
        "-d",
        DB_NAME,
        "-f",
        "/tmp/drill.dump",
    )
    dump_seconds = time.monotonic() - started

    docker("exec", *env, container, "psql", "-U", "postgres", "-c", "DROP DATABASE IF EXISTS drill_restore")
    docker("exec", *env, container, "psql", "-U", "postgres", "-c", "CREATE DATABASE drill_restore")
    started = time.monotonic()
    docker(
        "exec", *env, container, "pg_restore", "-U", "postgres", "--no-owner", "-d", "drill_restore", "/tmp/drill.dump"
    )
    restore_seconds = time.monotonic() - started
    print(
        f"BACKUP DRILL dump={dump_seconds:.1f}s restore={restore_seconds:.1f}s target={RTO_SECONDS}s rows={sum(before.values())}"
    )
    assert restore_seconds < RTO_SECONDS

    restored_url = admin.rsplit("/", 1)[0] + "/drill_restore"
    try:
        assert await table_counts(restored_url) == before  # every table, every row

        conn = await asyncpg.connect(restored_url)
        try:
            unsafe = await conn.fetch(
                "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname IN "
                "('orders','products','customers','agent_runs','ledger_entries','stock_movements') "
                "AND NOT (c.relrowsecurity AND c.relforcerowsecurity)"
            )
            assert unsafe == [], "row level security must survive a restore"
            policies = await conn.fetchval("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
            assert policies > 10
            # the policies still isolate: as the application role, with shop A's id, only shop A's rows are visible
            await conn.execute("CREATE ROLE drill_app NOLOGIN")
            await conn.execute("GRANT USAGE ON SCHEMA public TO drill_app")
            await conn.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO drill_app")
            async with conn.transaction():
                await conn.execute("SET LOCAL ROLE drill_app")
                await conn.execute("SELECT set_config('app.tenant_id', $1, true)", a["tenant_id"])
                tenants = await conn.fetch("SELECT id FROM tenants")
                orders = await conn.fetch("SELECT DISTINCT tenant_id FROM orders")
            assert [str(r["id"]) for r in tenants] == [a["tenant_id"]]
            assert [str(r["tenant_id"]) for r in orders] == [a["tenant_id"]] and b["tenant_id"] != a["tenant_id"]
        finally:
            await conn.close()
    finally:
        docker(
            "exec",
            *env,
            container,
            "psql",
            "-U",
            "postgres",
            "-c",
            "DROP DATABASE IF EXISTS drill_restore",
            check=False,
        )
        admin_conn = await asyncpg.connect(admin)
        try:
            await admin_conn.execute("DROP ROLE IF EXISTS drill_app")
        finally:
            await admin_conn.close()
    assert (
        await client.get("/api/v1/dashboard/summary", headers=bearer(a))
    ).status_code == 200  # the live database is untouched
