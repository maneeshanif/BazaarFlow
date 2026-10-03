"""The global auth tables (users, refresh_tokens, login_attempts) work on a hosted Postgres that switches RLS on for
every new table (Supabase's `ensure_rls` event trigger).

Found on the first real Supabase seed: the trigger enabled RLS on these tables with NO policy, so app_user could not
insert a user and registration and login were impossible. They now have RLS plus one explicit policy for app_user,
which also keeps report_ro from reading password hashes.
"""

from __future__ import annotations

import asyncpg
import pytest
from httpx import AsyncClient

from app.cli.check_database import run_checks
from tests.pg.conftest import register

pytestmark = pytest.mark.pg

GLOBAL_AUTH_TABLES = ("users", "refresh_tokens", "login_attempts")


async def test_each_global_auth_table_has_rls_and_an_explicit_policy_for_app_user_only(
    admin_conn: asyncpg.Connection,
) -> None:
    for table in GLOBAL_AUTH_TABLES:
        row = await admin_conn.fetchrow(
            "SELECT relrowsecurity FROM pg_class WHERE oid = $1::regclass", f"public.{table}"
        )
        assert row["relrowsecurity"], f"{table}: RLS must be on (Supabase turns it on anyway; be explicit)"
        policies = await admin_conn.fetch(
            "SELECT policyname, roles, cmd FROM pg_policies WHERE schemaname = 'public' AND tablename = $1", table
        )
        assert len(policies) == 1, f"{table}: expected exactly one policy, got {policies}"
        assert list(policies[0]["roles"]) == ["app_user"], f"{table}: the policy must be limited to app_user"
        assert policies[0]["cmd"] == "ALL"


async def test_registration_and_login_work_with_rls_on(client: AsyncClient) -> None:
    acct = await register(client, "Shop RLS")
    login = await client.post("/api/v1/auth/login", json={"email": acct["email"], "password": acct["password"]})
    assert login.status_code == 200, login.text


async def test_the_reporting_role_cannot_read_password_hashes_or_tokens(
    pg_urls: dict[str, str], client: AsyncClient
) -> None:
    await register(client, "Shop Hashes")  # make sure there is at least one user and one refresh token
    conn = await asyncpg.connect(pg_urls["report"].replace("postgresql+asyncpg://", "postgresql://", 1))
    try:
        for table in GLOBAL_AUTH_TABLES:
            assert await conn.fetchval(f"SELECT count(*) FROM {table}") == 0, f"report_ro can see rows of {table}"
    finally:
        await conn.close()


async def test_check_database_flags_a_global_table_whose_rls_has_no_policy(pg_urls: dict[str, str]) -> None:
    conn = await asyncpg.connect(pg_urls["admin_plain"])
    try:
        await conn.execute("DROP POLICY app_user_only ON users")
        problems = await run_checks(pg_urls["admin_plain"])
        assert any("users" in p and "policy" in p for p in problems), problems
    finally:
        await conn.execute("CREATE POLICY app_user_only ON users FOR ALL TO app_user USING (true) WITH CHECK (true)")
        await conn.close()
    assert await run_checks(pg_urls["admin_plain"]) == []


async def test_check_database_flags_a_global_table_with_rls_switched_off(pg_urls: dict[str, str]) -> None:
    """Off would also work, but the project's rule is explicit RLS everywhere (the Supabase advisor flags 'off')."""
    conn = await asyncpg.connect(pg_urls["admin_plain"])
    try:
        await conn.execute("ALTER TABLE login_attempts DISABLE ROW LEVEL SECURITY")
        problems = await run_checks(pg_urls["admin_plain"])
        assert any("login_attempts" in p for p in problems), problems
    finally:
        await conn.execute("ALTER TABLE login_attempts ENABLE ROW LEVEL SECURITY")
        await conn.close()
    assert await run_checks(pg_urls["admin_plain"]) == []
