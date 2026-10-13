"""draft purchase orders (deferred from Phase 3, PRD W-006 step 3)

Revision ID: 20261013_16
Revises: 20261007_15
Create Date: 2026-10-13

``purchase_orders`` (one row per vendor reorder: status, estimated total, the approval that sends the message) and
``purchase_order_items`` (one row per product: name snapshot, quantity, unit cost when known). Both get ENABLE + FORCE
row level security and the standard ``tenant_isolation`` policy. Nothing here touches stock or the ledger.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261013_16"
down_revision: str | None = "20261007_15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("purchase_orders", "purchase_order_items")


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="drafted", nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("action_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status in ('drafted', 'approved', 'sent', 'cancelled')", name="ck_purchase_orders_status"),
        sa.CheckConstraint("total >= 0", name="ck_purchase_orders_total_not_negative"),
    )
    op.create_index("ix_purchase_orders_tenant_id", "purchase_orders", ["tenant_id"])
    op.create_index("ix_purchase_orders_tenant_status", "purchase_orders", ["tenant_id", "status"])
    op.create_index("ix_purchase_orders_tenant_action", "purchase_orders", ["tenant_id", "action_id"])
    op.create_table(
        "purchase_order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("qty > 0", name="ck_purchase_order_items_qty_positive"),
    )
    op.create_index("ix_purchase_order_items_tenant_id", "purchase_order_items", ["tenant_id"])
    op.create_index("ix_purchase_order_items_tenant_order", "purchase_order_items", ["tenant_id", "purchase_order_id"])
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (tenant_id = app_tenant_id()) WITH CHECK (tenant_id = app_tenant_id())"
        )
    op.execute(
        """
        DO $$
        DECLARE r text;
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
            REVOKE DELETE, TRUNCATE ON purchase_orders, purchase_order_items FROM app_user;
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
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
