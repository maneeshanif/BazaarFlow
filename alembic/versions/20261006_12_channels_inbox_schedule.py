"""channels: integrations hardening, inbox, webhook events, marketing schedule (Phase 2, tasks 59-62, 70-71, 75-77)

Revision ID: 20261006_12
Revises: 20261006_11
Create Date: 2026-10-06

* ``tenant_integrations``: one row per shop and provider, constrained provider and status, ``connected_at`` and the token
  ``expires_at``. A SELECT policy lets the webhook route find the integration whose ``external_id`` equals the value it
  sets in ``app.webhook_external_id`` (no tenant is known before the lookup); it opens exactly that one row.
* ``conversations`` (one customer thread per shop, channel and phone) and ``webhook_events`` (replay protection).
* ``messages`` gains the conversation, who sent it and an idempotency key (a retried send never makes a second row).
* ``marketing_posts`` gains the publish time, attempts and last error; ``marketing_schedules`` holds the shop's schedule.
* New tables get ENABLE + FORCE row level security and the standard ``tenant_isolation`` policy.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261006_12"
down_revision: str | None = "20261006_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = ("conversations", "webhook_events", "marketing_schedules")


def _ts() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    # -- tenant_integrations ----------------------------------------------------------------------------
    op.add_column("tenant_integrations", sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenant_integrations", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_tenant_integrations_tenant_provider", "tenant_integrations", ["tenant_id", "provider"])
    op.create_check_constraint(
        "ck_tenant_integrations_provider",
        "tenant_integrations",
        "provider in ('whatsapp_twilio', 'whatsapp_meta', 'facebook', 'instagram', 'vapi')",
    )
    op.create_check_constraint(
        "ck_tenant_integrations_status", "tenant_integrations", "status in ('pending', 'connected', 'error', 'revoked')"
    )
    op.execute(
        "CREATE POLICY webhook_lookup ON tenant_integrations FOR SELECT "
        "USING (external_id = nullif(current_setting('app.webhook_external_id', true), ''))"
    )

    # -- conversations ----------------------------------------------------------------------------------
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("contact_name", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("assigned_to", sa.Uuid(), nullable=True),
        sa.Column("handoff_note", sa.String(length=500), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_message_text", sa.String(length=160), nullable=True),
        *_ts(),
        sa.CheckConstraint("status in ('open', 'ai_handling', 'needs_human', 'resolved')", name="ck_conversations_status"),
        sa.CheckConstraint("mode in ('ai', 'human')", name="ck_conversations_mode"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
    op.create_index("uq_conversations_tenant_channel_phone", "conversations", ["tenant_id", "channel", "phone"], unique=True)
    op.create_index("ix_conversations_tenant_last_message", "conversations", ["tenant_id", "last_message_at"])

    # -- webhook_events ---------------------------------------------------------------------------------
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider", "event_id", name="uq_webhook_events_tenant_provider_event"),
    )
    op.create_index("ix_webhook_events_tenant_id", "webhook_events", ["tenant_id"])

    # -- messages -----------------------------------------------------------------------------------------
    op.add_column("messages", sa.Column("conversation_id", sa.Uuid(), nullable=True))
    op.add_column("messages", sa.Column("sender", sa.String(length=10), nullable=True))
    op.add_column("messages", sa.Column("sent_by", sa.Uuid(), nullable=True))
    op.add_column("messages", sa.Column("idempotency_key", sa.String(length=80), nullable=True))
    op.add_column("messages", sa.Column("error", sa.String(length=200), nullable=True))
    op.create_foreign_key("fk_messages_conversation_id_conversations", "messages", "conversations", ["conversation_id"], ["id"])
    op.create_check_constraint("ck_messages_sender", "messages", "sender is null or sender in ('customer', 'ai', 'staff')")
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index(
        "uq_messages_tenant_idempotency_key",
        "messages",
        ["tenant_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    # -- marketing_posts ----------------------------------------------------------------------------------
    op.add_column("marketing_posts", sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True))
    op.add_column("marketing_posts", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("marketing_posts", sa.Column("attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("marketing_posts", sa.Column("last_error", sa.String(length=500), nullable=True))
    op.add_column("marketing_posts", sa.Column("source", sa.String(length=10), server_default="manual", nullable=False))
    op.create_index("ix_marketing_posts_tenant_status_due", "marketing_posts", ["tenant_id", "status", "scheduled_for"])

    # -- marketing_schedules --------------------------------------------------------------------------------
    op.create_table(
        "marketing_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("goal", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.String(length=300), nullable=True),
        sa.Column("tone", sa.String(length=20), nullable=False),
        sa.Column("language", sa.String(length=12), nullable=False),
        sa.Column("posts_per_day", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.Time(), nullable=False),
        sa.Column("window_end", sa.Time(), nullable=False),
        sa.Column("approval_mode", sa.String(length=10), nullable=False),
        sa.Column("last_generated_on", sa.Date(), nullable=True),
        *_ts(),
        sa.CheckConstraint("posts_per_day between 1 and 5", name="ck_marketing_schedules_posts_per_day"),
        sa.CheckConstraint("approval_mode in ('manual', 'auto')", name="ck_marketing_schedules_approval_mode"),
        sa.CheckConstraint("window_start < window_end", name="ck_marketing_schedules_window"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_marketing_schedules_tenant"),
    )
    op.create_index("ix_marketing_schedules_tenant_id", "marketing_schedules", ["tenant_id"])

    for table in NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (tenant_id = app_tenant_id()) WITH CHECK (tenant_id = app_tenant_id())"
        )
    # a background job finds which shops have work (posts due, a schedule on) before it knows whose it is
    for table in ("marketing_posts", "marketing_schedules"):
        op.execute(
            f"CREATE POLICY system_discovery ON {table} FOR SELECT "
            "USING (coalesce(current_setting('app.system_job', true), '') = 'true')"
        )
    op.execute(
        """
        DO $$
        DECLARE r text;
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
            REVOKE UPDATE, DELETE, TRUNCATE ON webhook_events FROM app_user;
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
    op.execute("DROP POLICY IF EXISTS system_discovery ON marketing_posts")
    op.drop_table("marketing_schedules")
    op.drop_index("ix_marketing_posts_tenant_status_due", table_name="marketing_posts")
    for column in ("source", "last_error", "attempts", "published_at", "scheduled_for"):
        op.drop_column("marketing_posts", column)
    op.drop_index("uq_messages_tenant_idempotency_key", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_constraint("ck_messages_sender", "messages", type_="check")
    op.drop_constraint("fk_messages_conversation_id_conversations", "messages", type_="foreignkey")
    for column in ("error", "idempotency_key", "sent_by", "sender", "conversation_id"):
        op.drop_column("messages", column)
    op.drop_table("webhook_events")
    op.drop_table("conversations")
    op.execute("DROP POLICY IF EXISTS webhook_lookup ON tenant_integrations")
    op.drop_constraint("ck_tenant_integrations_status", "tenant_integrations", type_="check")
    op.drop_constraint("ck_tenant_integrations_provider", "tenant_integrations", type_="check")
    op.drop_constraint("uq_tenant_integrations_tenant_provider", "tenant_integrations", type_="unique")
    op.drop_column("tenant_integrations", "expires_at")
    op.drop_column("tenant_integrations", "connected_at")
