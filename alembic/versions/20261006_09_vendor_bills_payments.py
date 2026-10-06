"""vendors and payables: purchase bills and vendor payments (Phase 2, task 73)

Revision ID: 20261006_09
Revises: 20261004_08
Create Date: 2026-10-06

* ``vendor_bills``: what a vendor billed the shop (amount, optional due date and reference).
* ``vendor_payments``: what the shop paid a vendor.
* What the shop owes a vendor is the sum of its ``ledger_entries`` (``party_type='vendor'``: debit = a bill,
  credit = a payment), the same append-only ledger the customer udhaar uses. ``vendors.balance`` is no longer written.
* Both tables get ENABLE + FORCE row level security and the standard ``tenant_isolation`` policy.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261006_09"
down_revision: str | None = "20261004_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = ("vendor_bills", "vendor_payments")


def _common() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
    ]


def _tail() -> list[sa.SchemaItem]:
    return [
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    ]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.create_table(
        "vendor_bills",
        *_common(),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("reference", sa.String(length=60), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        *_tail(),
        sa.CheckConstraint("amount > 0", name="ck_vendor_bills_amount_positive"),
    )
    op.create_index("ix_vendor_bills_tenant_id", "vendor_bills", ["tenant_id"])
    op.create_index("ix_vendor_bills_tenant_vendor", "vendor_bills", ["tenant_id", "vendor_id"])
    op.create_table(
        "vendor_payments",
        *_common(),
        sa.Column("method", sa.String(length=10), nullable=False),
        *_tail(),
        sa.CheckConstraint("amount > 0", name="ck_vendor_payments_amount_positive"),
        sa.CheckConstraint("method in ('cash', 'card', 'bank', 'wallet')", name="ck_vendor_payments_method"),
    )
    op.create_index("ix_vendor_payments_tenant_id", "vendor_payments", ["tenant_id"])
    op.create_index("ix_vendor_payments_tenant_vendor", "vendor_payments", ["tenant_id", "vendor_id"])
    for table in NEW_TABLES:
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
            REVOKE UPDATE, DELETE, TRUNCATE ON vendor_bills, vendor_payments FROM app_user;
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
    op.drop_table("vendor_payments")
    op.drop_table("vendor_bills")
