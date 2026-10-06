"""voice agent: settings and call records (Phase 3, tasks 32, 69, 87, 91)

Revision ID: 20261007_15
Revises: 20261007_14
Create Date: 2026-10-07

``voice_settings`` (one row per shop) and ``voice_calls`` (one row per call: status, cost, per-turn latency, a redacted
transcript that is removed after the retention period). Both get ENABLE + FORCE row level security and the standard
``tenant_isolation`` policy. A SELECT policy on ``voice_settings`` lets the scheduler's ``system_session`` find the shops
whose transcripts are due for removal. The ``vapi`` provider already exists in the ``tenant_integrations`` check.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261007_15"
down_revision: str | None = "20261007_14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.create_table(
        "voice_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("greeting", sa.String(length=200), nullable=False),
        sa.Column("consent_notice", sa.String(length=300), nullable=False),
        sa.Column("max_call_seconds", sa.Integer(), nullable=False),
        sa.Column("monthly_cap_usd", sa.Numeric(8, 2), nullable=False),
        sa.Column("handoff_phone", sa.String(length=30), nullable=True),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        *_ts(),
        sa.CheckConstraint("max_call_seconds between 60 and 900", name="ck_voice_settings_max_call_seconds"),
        sa.CheckConstraint("retention_days between 1 and 365", name="ck_voice_settings_retention_days"),
        sa.CheckConstraint("monthly_cap_usd >= 0", name="ck_voice_settings_cap"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_voice_settings_tenant"),
    )
    op.create_index("ix_voice_settings_tenant_id", "voice_settings", ["tenant_id"])
    op.create_table(
        "voice_calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider_call_id", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("caller_hint", sa.String(length=12), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("ended_reason", sa.String(length=80), nullable=True),
        sa.Column("spend_micros", sa.BigInteger(), nullable=False),
        sa.Column("turns_json", sa.JSON(), nullable=False),
        sa.Column("escalated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("handoff_note", sa.String(length=500), nullable=True),
        sa.Column("consent_notice", sa.String(length=300), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        *_ts(),
        sa.CheckConstraint("status in ('ringing', 'in_progress', 'completed', 'escalated', 'failed')", name="ck_voice_calls_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider_call_id", name="uq_voice_calls_tenant_provider_call"),
    )
    op.create_index("ix_voice_calls_tenant_id", "voice_calls", ["tenant_id"])
    op.create_index("ix_voice_calls_tenant_started", "voice_calls", ["tenant_id", "started_at"])
    for table in ("voice_settings", "voice_calls"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (tenant_id = app_tenant_id()) WITH CHECK (tenant_id = app_tenant_id())"
        )
    op.execute(
        "CREATE POLICY system_discovery ON voice_settings FOR SELECT "
        "USING (coalesce(current_setting('app.system_job', true), '') = 'true')"
    )
    op.execute(
        """
        DO $$
        DECLARE r text;
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
            REVOKE DELETE, TRUNCATE ON voice_calls FROM app_user;
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
    op.drop_table("voice_calls")
    op.drop_table("voice_settings")
