"""Provision the three database roles BazaarFlow needs (PRD §3.8).

Run once per Supabase project (as the ``postgres`` admin user) BEFORE the first migration::

    uv run python -m app.cli.provision_db --admin-url postgresql://postgres:...@host:5432/postgres

Roles created (idempotent; passwords are (re)set on every run):

* ``migrator``  - owns the schema objects; used only by Alembic over the direct connection.
* ``app_user``  - API runtime role: DML on business tables, ``NOBYPASSRLS``, no DDL.
* ``report_ro`` - read-only reporting role, RLS applies.

Passwords come from the environment (``MIGRATOR_PASSWORD``, ``APP_USER_PASSWORD``,
``REPORT_RO_PASSWORD``) so they never appear on a command line or in source control.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys

import asyncpg

_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _statements(db_name: str, migrator_pw: str, app_pw: str, report_pw: str) -> list[str]:
    if not _IDENT.match(db_name):
        raise ValueError(f"unsafe database name: {db_name!r}")
    stmts: list[str] = []
    for role, pw in (("migrator", migrator_pw), ("app_user", app_pw), ("report_ro", report_pw)):
        stmts.append(
            f"""DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{role}') THEN
    CREATE ROLE {role} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  END IF;
END $$"""
        )
        stmts.append(f"ALTER ROLE {role} WITH LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {_quote_literal(pw)}")
        stmts.append(f"GRANT CONNECT ON DATABASE {db_name} TO {role}")
        stmts.append(f"GRANT USAGE ON SCHEMA public TO {role}")
    stmts.append("GRANT CREATE ON SCHEMA public TO migrator")
    # Tables created by migrator are automatically usable by the runtime and reporting roles.
    stmts += [
        "ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user",
        "ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO app_user",
        "ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA public GRANT SELECT ON TABLES TO report_ro",
    ]
    return stmts


async def provision(admin_url: str, db_name: str, migrator_pw: str, app_pw: str, report_pw: str) -> None:
    conn = await asyncpg.connect(admin_url)
    try:
        for stmt in _statements(db_name, migrator_pw, app_pw, report_pw):
            await conn.execute(stmt)
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--admin-url", required=True, help="postgresql:// URL of the admin (postgres) user")
    parser.add_argument("--database", default="postgres", help="database the roles get CONNECT on")
    args = parser.parse_args()
    passwords = {}
    for env in ("MIGRATOR_PASSWORD", "APP_USER_PASSWORD", "REPORT_RO_PASSWORD"):
        value = os.environ.get(env, "")
        if not value:
            print(f"error: set {env} in the environment", file=sys.stderr)
            return 2
        passwords[env] = value
    asyncio.run(
        provision(
            args.admin_url,
            args.database,
            passwords["MIGRATOR_PASSWORD"],
            passwords["APP_USER_PASSWORD"],
            passwords["REPORT_RO_PASSWORD"],
        )
    )
    print("roles provisioned: migrator, app_user, report_ro")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
