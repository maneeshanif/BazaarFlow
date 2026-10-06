"""platform admin: cross-tenant reads, tenant suspension (Phase 2, tasks 79 and 82)

Revision ID: 20261006_11
Revises: 20261006_10
Create Date: 2026-10-06

* ``app_is_platform()`` reads the transaction-local setting ``app.platform_admin``. Only ``platform_session`` sets it,
  and only for a verified BazaarFlow operator (the ``is_platform_admin`` flag, re-checked on every request).
* A SELECT policy lets an operator read ``tenants``, ``memberships``, ``orders``, ``agent_runs`` and ``messages`` across
  shops (tenant list, activity, spend, error rate). Nothing else is opened.
* One UPDATE policy on ``tenants`` lets an operator change a shop's status (suspend, reactivate). Every platform
  request writes an audit row with no tenant.
* ``tenants.status`` is limited to ``active`` and ``suspended``.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261006_11"
down_revision: str | None = "20261006_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

READABLE = ("tenants", "memberships", "orders", "agent_runs", "messages")


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE FUNCTION app_is_platform() RETURNS boolean
        LANGUAGE sql STABLE
        AS $$ SELECT coalesce(current_setting('app.platform_admin', true), '') = 'true' $$
        """
    )
    for table in READABLE:
        op.execute(f"CREATE POLICY platform_select ON {table} FOR SELECT USING (app_is_platform())")
    op.execute("CREATE POLICY platform_update ON tenants FOR UPDATE USING (app_is_platform()) WITH CHECK (app_is_platform())")
    op.create_check_constraint("ck_tenants_status", "tenants", "status in ('active', 'suspended')")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_constraint("ck_tenants_status", "tenants", type_="check")
    op.execute("DROP POLICY IF EXISTS platform_update ON tenants")
    for table in READABLE:
        op.execute(f"DROP POLICY IF EXISTS platform_select ON {table}")
    op.execute("DROP FUNCTION IF EXISTS app_is_platform()")
