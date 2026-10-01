"""Architecture tests over the migrated Postgres schema (PRD §3.7 constraints 1, 6, 8, 12; §3.8).

They introspect the real database after ``alembic upgrade head``, so a new table without a
``tenant_id`` and row-level security (or with a Data API grant) fails CI instead of shipping.
"""

from __future__ import annotations

import asyncpg
import pytest
from sqlalchemy import Float

from app.core.database import Base
from app.models import *  # noqa: F403 - register every model on Base.metadata

pytestmark = pytest.mark.pg

# Tables that are intentionally not tenant-owned. Add to this list only with a written reason.
GLOBAL_TABLES = {
    "users": "identity is global; tenants reach users through memberships",
    "tenants": "the isolation boundary itself; RLS is keyed on its own id",
    "alembic_version": "migration bookkeeping",
    "refresh_tokens": "auth bookkeeping read before a tenant is known; token stored as a SHA-256 hash",
    "login_attempts": "lockout counters keyed by a hash of the e-mail, read before a tenant is known",
}


def test_every_business_table_declares_tenant_id() -> None:
    missing = [
        name for name, table in Base.metadata.tables.items() if name not in GLOBAL_TABLES and "tenant_id" not in table.c
    ]
    assert not missing, f"Tables without tenant_id: {missing}"


def test_no_float_columns_in_the_model() -> None:
    floats = [
        f"{table.name}.{col.name}"
        for table in Base.metadata.tables.values()
        for col in table.c
        if isinstance(col.type, Float)
    ]
    assert not floats, f"Use NUMERIC for money, not float: {floats}"


async def test_every_table_has_forced_rls_and_a_policy(admin_conn: asyncpg.Connection) -> None:
    rows = await admin_conn.fetch(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, "
        "(SELECT count(*) FROM pg_policies p WHERE p.tablename = c.relname AND p.schemaname = 'public') AS policies "
        "FROM pg_class c WHERE c.relkind = 'r' AND c.relnamespace = 'public'::regnamespace"
    )
    by_name = {r["relname"]: r for r in rows}
    assert set(Base.metadata.tables) <= set(by_name), "model tables missing from the migrated database"
    bad = []
    for name in Base.metadata.tables:
        if name in {"users", "refresh_tokens", "login_attempts"}:
            continue
        r = by_name[name]
        if not (r["relrowsecurity"] and r["relforcerowsecurity"] and r["policies"] >= 1):
            bad.append(name)
    assert not bad, f"Tables without ENABLE+FORCE RLS and a policy: {bad}"


async def test_data_api_roles_have_no_access_to_public_tables(admin_conn: asyncpg.Connection) -> None:
    leaks = await admin_conn.fetch(
        "SELECT r.rolname, c.relname FROM pg_roles r, pg_class c "
        "WHERE r.rolname IN ('anon', 'authenticated') AND c.relkind = 'r' AND c.relnamespace = 'public'::regnamespace "
        "AND (has_table_privilege(r.rolname, c.oid, 'SELECT') OR has_table_privilege(r.rolname, c.oid, 'INSERT') "
        "OR has_table_privilege(r.rolname, c.oid, 'UPDATE') OR has_table_privilege(r.rolname, c.oid, 'DELETE'))"
    )
    assert not leaks, f"anon/authenticated can still reach: {[(r['rolname'], r['relname']) for r in leaks]}"


async def test_application_roles_cannot_bypass_rls_or_change_schema(admin_conn: asyncpg.Connection) -> None:
    roles = await admin_conn.fetch(
        "SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles "
        "WHERE rolname IN ('app_user', 'report_ro', 'migrator')"
    )
    assert {r["rolname"] for r in roles} == {"app_user", "report_ro", "migrator"}
    for r in roles:
        assert not r["rolsuper"] and not r["rolbypassrls"] and not r["rolcreaterole"] and not r["rolcreatedb"], r["rolname"]
    can_ddl = await admin_conn.fetchval("SELECT has_schema_privilege('app_user', 'public', 'CREATE')")
    assert can_ddl is False, "app_user must not be able to create objects"
    can_write = await admin_conn.fetchval("SELECT has_table_privilege('report_ro', 'customers', 'INSERT')")
    assert can_write is False, "report_ro must be read-only"
