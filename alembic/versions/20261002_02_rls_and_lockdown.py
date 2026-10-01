"""row level security, helper functions and Data API lockdown

Revision ID: 20261002_02
Revises: 20261002_01
Create Date: 2026-10-02

Implements PRD §3.5 and §3.8:

* ``app_tenant_id()`` / ``app_user_id()`` read the transaction-local settings the API sets per request.
  When a setting is missing they return NULL, so every policy matches nothing (fail closed).
* Every tenant-owned table gets ENABLE + FORCE row level security and a ``tenant_isolation`` policy.
* ``memberships`` and ``tenants`` additionally expose the caller's own rows (needed at login, before a
  tenant has been chosen).
* ``audit_logs`` is append-only for the application role and may hold NULL-tenant rows (failed logins).
* ``anon`` / ``authenticated`` (Supabase Data API roles) lose every grant on the public schema.
"""

from __future__ import annotations

from alembic import op

revision = "20261002_02"
down_revision = "20261002_01"
branch_labels = None
depends_on = None

# Tables whose rows all carry a non-null tenant_id and share the same isolation policy.
TENANT_TABLES = [
    "customers",
    "facebook_accounts",
    "inventory_items",
    "marketing_posts",
    "memberships",
    "messages",
    "orders",
    "scheduled_campaigns",
    "support_tickets",
    "tenant_integrations",
    "vendors",
]


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION app_tenant_id() RETURNS uuid
        LANGUAGE sql STABLE
        AS $$ SELECT nullif(current_setting('app.tenant_id', true), '')::uuid $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION app_user_id() RETURNS uuid
        LANGUAGE sql STABLE
        AS $$ SELECT nullif(current_setting('app.user_id', true), '')::uuid $$
        """
    )

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
              USING (tenant_id = app_tenant_id())
              WITH CHECK (tenant_id = app_tenant_id())
            """
        )

    # A user can always read their own memberships (login lists them before a tenant is chosen).
    op.execute(
        "CREATE POLICY own_memberships ON memberships FOR SELECT USING (user_id = app_user_id())"
    )

    # tenants: RLS is keyed on the table's own id.
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_self ON tenants
          USING (id = app_tenant_id())
          WITH CHECK (id = app_tenant_id())
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_of_member ON tenants FOR SELECT
          USING (id IN (SELECT tenant_id FROM memberships WHERE user_id = app_user_id()))
        """
    )

    # audit_logs: readable per tenant, insertable with or without a tenant, never updated or deleted.
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY audit_select ON audit_logs FOR SELECT USING (tenant_id = app_tenant_id())")
    op.execute(
        """
        CREATE POLICY audit_insert ON audit_logs FOR INSERT
          WITH CHECK (tenant_id IS NULL OR tenant_id = app_tenant_id())
        """
    )

    # Roles may not exist (e.g. a throwaway database in CI); grants are applied only when they do.
    op.execute(
        """
        DO $$
        DECLARE r text;
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
            REVOKE UPDATE, DELETE, TRUNCATE ON audit_logs FROM app_user;
          END IF;
          FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
              EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', r);
              EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', r);
              EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM %I', r);
            END IF;
          END LOOP;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_insert ON audit_logs")
    op.execute("DROP POLICY IF EXISTS audit_select ON audit_logs")
    op.execute("ALTER TABLE audit_logs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS tenant_of_member ON tenants")
    op.execute("DROP POLICY IF EXISTS tenant_self ON tenants")
    op.execute("ALTER TABLE tenants NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS own_memberships ON memberships")
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP FUNCTION IF EXISTS app_user_id()")
    op.execute("DROP FUNCTION IF EXISTS app_tenant_id()")
