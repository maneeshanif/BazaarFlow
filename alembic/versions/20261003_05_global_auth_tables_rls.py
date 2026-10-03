"""explicit RLS and an app_user policy on the global auth tables

Hosted Postgres (Supabase) runs an event trigger that enables row level security on every table created in
`public`. Without a policy that blocks everyone except the table owner, so app_user could not insert users
(first real Supabase seed: "new row violates row-level security policy for table users"). The global auth tables are
read and written before a tenant is known, so their policy is "app_user may do anything"; every other role,
including report_ro, sees no rows (this also keeps password hashes out of the reporting role's reach).

Revision ID: 20261003_05
Revises: 20261002_04
Create Date: 2026-10-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261003_05"
down_revision: str | None = "20261002_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GLOBAL_AUTH_TABLES = ("users", "refresh_tokens", "login_attempts")


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return  # SQLite (fast unit tests) has no row level security
    for table in GLOBAL_AUTH_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS app_user_only ON {table}")
        op.execute(f"CREATE POLICY app_user_only ON {table} FOR ALL TO app_user USING (true) WITH CHECK (true)")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in GLOBAL_AUTH_TABLES:
        op.execute(f"DROP POLICY IF EXISTS app_user_only ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
