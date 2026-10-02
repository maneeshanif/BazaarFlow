"""Verify a database against the PRD §3.8 security posture. Run it against every Supabase project after migrating.

    uv run python -m app.cli.check_database --admin-url postgresql://postgres:...@db.<ref>.supabase.co:5432/postgres

Checks (each failure is printed; exit code 1 when anything is wrong):
  * the roles migrator / app_user / report_ro exist and can neither bypass RLS nor create roles or databases
  * app_user cannot create objects; report_ro cannot write
  * every business table has ENABLE + FORCE row level security and at least one policy
  * the Supabase Data API roles (anon, authenticated) have no privileges on any public table
  * audit_logs is append-only for app_user
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import asyncpg

# Tables that are intentionally outside row level security (see tests/pg/test_schema_rules.py).
GLOBAL_TABLES = {"users", "refresh_tokens", "login_attempts", "alembic_version"}


async def run_checks(admin_url: str) -> list[str]:
    """Return a list of human-readable problems; empty means the database passes."""
    problems: list[str] = []
    conn = await asyncpg.connect(admin_url)
    try:
        roles = {
            r["rolname"]: r
            for r in await conn.fetch(
                "SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles "
                "WHERE rolname IN ('migrator', 'app_user', 'report_ro')"
            )
        }
        for name in ("migrator", "app_user", "report_ro"):
            r = roles.get(name)
            if r is None:
                problems.append(f"role {name} does not exist (run app.cli.provision_db)")
            elif r["rolsuper"] or r["rolbypassrls"] or r["rolcreaterole"] or r["rolcreatedb"]:
                problems.append(f"role {name} is too powerful (superuser / bypassrls / createrole / createdb)")
        if "app_user" in roles and await conn.fetchval("SELECT has_schema_privilege('app_user', 'public', 'CREATE')"):
            problems.append("app_user can create objects in schema public")

        tables = await conn.fetch(
            "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, "
            "(SELECT count(*) FROM pg_policies p WHERE p.tablename = c.relname AND p.schemaname = 'public') AS policies "
            "FROM pg_class c WHERE c.relkind = 'r' AND c.relnamespace = 'public'::regnamespace"
        )
        if not tables:
            problems.append("no tables in schema public (run alembic upgrade head)")
        for t in tables:
            if t["relname"] in GLOBAL_TABLES:
                continue
            if not (t["relrowsecurity"] and t["relforcerowsecurity"] and t["policies"] >= 1):
                problems.append(f"table {t['relname']} lacks ENABLE + FORCE row level security and a policy")

        for role in ("anon", "authenticated"):
            if not await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", role):
                continue  # not a Supabase database
            leaks = await conn.fetch(
                "SELECT c.relname FROM pg_class c WHERE c.relkind = 'r' AND c.relnamespace = 'public'::regnamespace AND ("
                "has_table_privilege($1, c.oid, 'SELECT') OR has_table_privilege($1, c.oid, 'INSERT') OR "
                "has_table_privilege($1, c.oid, 'UPDATE') OR has_table_privilege($1, c.oid, 'DELETE'))",
                role,
            )
            for leak in leaks:
                problems.append(f"Data API role {role} can access table {leak['relname']}")

        if "app_user" in roles and any(t["relname"] == "audit_logs" for t in tables):
            for priv in ("UPDATE", "DELETE", "TRUNCATE"):
                if await conn.fetchval("SELECT has_table_privilege('app_user', 'public.audit_logs', $1)", priv):
                    problems.append(f"app_user has {priv} on audit_logs (it must be append-only)")
        if "report_ro" in roles and any(t["relname"] == "customers" for t in tables):
            if await conn.fetchval("SELECT has_table_privilege('report_ro', 'public.customers', 'INSERT')"):
                problems.append("report_ro can write (it must be read-only)")
    finally:
        await conn.close()
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--admin-url", required=True, help="postgresql:// URL of an admin connection (direct, port 5432)")
    args = parser.parse_args()
    problems = asyncio.run(run_checks(args.admin_url))
    if problems:
        print("DATABASE CHECK FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("database check passed: roles, row level security, Data API lockdown, audit append-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
