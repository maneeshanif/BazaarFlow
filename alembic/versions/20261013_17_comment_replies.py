"""Facebook comment replies (deferred from Phase 3, PRD W-004 step 4)

Revision ID: 20261013_17
Revises: 20261013_16
Create Date: 2026-10-13

``comment_replies``: one row per Facebook comment on a published post, with the proposed reply and its status.
``marketing_posts.comments_checked_at`` lets the scheduler look at each post's comments only every few minutes.
The new table gets ENABLE + FORCE row level security and the standard ``tenant_isolation`` policy.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261013_17"
down_revision: str | None = "20261013_16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.add_column("marketing_posts", sa.Column("comments_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "comment_replies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("fb_post_id", sa.String(length=255), nullable=False),
        sa.Column("fb_comment_id", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=True),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("reply_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=10), server_default=sa.text("'proposed'"), nullable=False),
        sa.Column("action_id", sa.Uuid(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("fb_reply_id", sa.String(length=255), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["marketing_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "fb_comment_id", name="uq_comment_replies_tenant_comment"),
        sa.CheckConstraint("status in ('proposed', 'approved', 'posted', 'skipped', 'failed')", name="ck_comment_replies_status"),
    )
    op.create_index("ix_comment_replies_tenant_id", "comment_replies", ["tenant_id"])
    op.create_index("ix_comment_replies_tenant_status", "comment_replies", ["tenant_id", "status"])
    op.execute("ALTER TABLE comment_replies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE comment_replies FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON comment_replies "
        "USING (tenant_id = app_tenant_id()) WITH CHECK (tenant_id = app_tenant_id())"
    )
    # the scheduler's scan finds the shops with an approved reply waiting (ids only, like marketing_posts)
    op.execute(
        "CREATE POLICY system_discovery ON comment_replies FOR SELECT "
        "USING (coalesce(current_setting('app.system_job', true), '') = 'true')"
    )
    op.execute(
        """
        DO $$
        DECLARE r text;
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
            REVOKE DELETE, TRUNCATE ON comment_replies FROM app_user;
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
    op.drop_table("comment_replies")
    op.drop_column("marketing_posts", "comments_checked_at")
