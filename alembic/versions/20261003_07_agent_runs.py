"""agent runs and the per-shop AI switch (Phase 1B, tasks 63, 64, 65)

Revision ID: 20261003_07
Revises: 20261003_06
Create Date: 2026-10-03

* ``agent_runs``: one append-only row per chat turn an agent handled, with the trace already redacted.
* ``tenants.agents_enabled``: the owner's kill switch, readable and changeable without a deploy.
* The new table gets ENABLE + FORCE row level security and the standard tenant policy, loses UPDATE/DELETE for
  ``app_user`` (a trace is evidence), and is taken back from the Supabase Data API roles.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261003_07"
down_revision: str | None = "20261003_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.add_column("tenants", sa.Column("agents_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False))

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("agent", sa.String(length=40), nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=False),
        sa.Column("trace_json", sa.JSON(), nullable=False),
        sa.Column("action_ids", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.String(length=12), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("spend_micros", sa.BigInteger(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("outcome in ('ok', 'failed', 'step_limit', 'paused', 'spend_limit')", name="ck_agent_runs_outcome"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_runs_tenant_id"), "agent_runs", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_created_at"), "agent_runs", ["created_at"], unique=False)
    op.create_index("ix_agent_runs_tenant_created_at", "agent_runs", ["tenant_id", "created_at"], unique=False)

    op.execute("ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_runs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON agent_runs "
        "USING (tenant_id = app_tenant_id()) WITH CHECK (tenant_id = app_tenant_id())"
    )
    op.execute(
        """
        DO $$
        DECLARE r text;
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
            REVOKE UPDATE, DELETE, TRUNCATE ON agent_runs FROM app_user;
          END IF;
          FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
              EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', r);
            END IF;
          END LOOP;
        END $$
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_table("agent_runs")
    op.drop_column("tenants", "agents_enabled")
