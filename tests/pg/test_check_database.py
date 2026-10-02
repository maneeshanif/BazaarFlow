"""Task 09 done-condition: app.cli.check_database passes on a correctly provisioned database and catches regressions."""

from __future__ import annotations

import asyncpg
import pytest

from app.cli.check_database import run_checks

pytestmark = pytest.mark.pg


async def test_a_correctly_provisioned_and_migrated_database_passes(pg_urls: dict[str, str]) -> None:
    assert await run_checks(pg_urls["admin_plain"]) == []


async def test_it_reports_a_data_api_grant_and_a_missing_policy(pg_urls: dict[str, str]) -> None:
    conn = await asyncpg.connect(pg_urls["admin_plain"])
    try:
        await conn.execute("GRANT SELECT ON customers TO anon")
        await conn.execute("ALTER TABLE vendors NO FORCE ROW LEVEL SECURITY")
        problems = await run_checks(pg_urls["admin_plain"])
        assert any("anon" in p and "customers" in p for p in problems), problems
        assert any("vendors" in p and "FORCE" in p for p in problems), problems
    finally:
        await conn.execute("REVOKE ALL ON customers FROM anon")
        await conn.execute("ALTER TABLE vendors FORCE ROW LEVEL SECURITY")
        await conn.close()
    assert await run_checks(pg_urls["admin_plain"]) == []
