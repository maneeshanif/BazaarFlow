"""commerce core: products, stock movements, order lines, payments, udhaar ledger (Phase 1A, tasks 55/56)

Revision ID: 20261003_06
Revises: 20261003_05
Create Date: 2026-10-03

* ``products`` becomes the catalog. Every legacy ``inventory_items`` row is copied into it with the same id
  (so nothing that referenced the old id breaks) and ``inventory_items`` shrinks to the stock level of a product.
* A non-zero legacy ``stock_count`` becomes an ``opening`` row in ``stock_movements``, so the invariant
  "quantity equals the sum of its movements" holds from the first day.
* ``orders`` is reshaped to the PRD model. A legacy order (a free-text WhatsApp order with no product lines) is kept
  as a ``draft`` whose note carries the old product, quantity, customer and address text; nothing is dropped silently.
* New tables get ENABLE + FORCE row level security and the standard ``tenant_isolation`` policy. The append-only
  tables (``stock_movements``, ``ledger_entries``) lose UPDATE/DELETE for ``app_user``.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261003_06"
down_revision: str | None = "20261003_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = ("products", "stock_movements", "order_items", "payments", "ledger_entries")
APPEND_ONLY = ("stock_movements", "ledger_entries")


def _base_columns() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
    ]


def _timestamps() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return  # the data move and row level security are Postgres-only; SQLite unit tests use create_all

    op.create_table(
        "products",
        *_base_columns(),
        sa.Column("sku", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=True),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("vendor_id", sa.Uuid(), nullable=True),
        sa.Column("image_url", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_tenant_id"), "products", ["tenant_id"], unique=False)
    op.create_index(
        "uq_products_tenant_sku",
        "products",
        ["tenant_id", "sku"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Copy the legacy catalog (same ids). A missing sku gets a generated one, a long one is cut to 40 characters.
    op.execute(
        """
        INSERT INTO products (id, tenant_id, sku, name, category, price, cost, active, created_at, updated_at, deleted_at)
        SELECT id, tenant_id,
               coalesce(nullif(left(sku, 40), ''), 'SKU-' || left(replace(id::text, '-', ''), 8)),
               left(name, 120), left(category, 60), coalesce(price, 0), NULL, true, created_at, updated_at, deleted_at
        FROM inventory_items
        """
    )

    op.create_table(
        "stock_movements",
        *_base_columns(),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=20), nullable=False),
        sa.Column("ref_type", sa.String(length=30), nullable=True),
        sa.Column("ref_id", sa.Uuid(), nullable=True),
        sa.Column("actor_type", sa.String(length=10), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("delta <> 0", name="ck_stock_movements_delta_not_zero"),
        sa.CheckConstraint(
            "reason in ('opening', 'sale', 'purchase', 'adjustment', 'return', 'reversal')",
            name="ck_stock_movements_reason",
        ),
        sa.CheckConstraint("actor_type in ('user', 'agent', 'system')", name="ck_stock_movements_actor_type"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stock_movements_tenant_id"), "stock_movements", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_product_id"), "stock_movements", ["product_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_created_at"), "stock_movements", ["created_at"], unique=False)
    op.execute(
        """
        INSERT INTO stock_movements (id, tenant_id, product_id, delta, reason, actor_type, note, created_at)
        SELECT gen_random_uuid(), tenant_id, id, stock_count, 'opening', 'system', 'Migrated opening stock', now()
        FROM inventory_items WHERE stock_count > 0
        """
    )

    # inventory_items: from "the whole catalog row" to "the stock level of one product".
    op.add_column("inventory_items", sa.Column("product_id", sa.Uuid(), nullable=True))
    op.add_column("inventory_items", sa.Column("qty_on_hand", sa.Integer(), server_default="0", nullable=False))
    op.add_column("inventory_items", sa.Column("reorder_level", sa.Integer(), server_default="0", nullable=False))
    op.execute(
        "UPDATE inventory_items SET product_id = id, qty_on_hand = greatest(stock_count, 0), "
        "reorder_level = greatest(min_threshold, 0)"
    )
    op.alter_column("inventory_items", "product_id", nullable=False)
    op.alter_column("inventory_items", "qty_on_hand", server_default=None)
    op.alter_column("inventory_items", "reorder_level", server_default=None)
    op.drop_index("uq_inventory_items_tenant_sku", table_name="inventory_items")
    for column in ("sku", "name", "category", "stock_count", "price", "incoming_units", "min_threshold", "description", "deleted_at"):
        op.drop_column("inventory_items", column)
    op.create_foreign_key(
        "fk_inventory_items_product_id_products", "inventory_items", "products", ["product_id"], ["id"], ondelete="CASCADE"
    )
    op.create_unique_constraint("uq_inventory_items_tenant_product", "inventory_items", ["tenant_id", "product_id"])
    op.create_check_constraint("ck_inventory_items_qty_non_negative", "inventory_items", "qty_on_hand >= 0")

    # orders: legacy free-text rows are kept as drafts with their text in the note.
    op.add_column("orders", sa.Column("status", sa.String(length=12), server_default="draft", nullable=False))
    op.add_column("orders", sa.Column("subtotal", sa.Numeric(14, 2), server_default="0", nullable=False))
    op.add_column("orders", sa.Column("discount", sa.Numeric(14, 2), server_default="0", nullable=False))
    op.add_column("orders", sa.Column("total", sa.Numeric(14, 2), server_default="0", nullable=False))
    op.add_column("orders", sa.Column("channel", sa.String(length=10), server_default="whatsapp", nullable=False))
    op.add_column("orders", sa.Column("idempotency_key", sa.String(length=80), nullable=True))
    op.add_column("orders", sa.Column("created_by", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("note", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE orders SET
          subtotal = coalesce(budget, 0), total = coalesce(budget, 0),
          note = concat_ws(E'\\n',
                   'Imported order: ' || quantity::text || ' x ' || product_name,
                   CASE WHEN customer_name IS NOT NULL THEN 'Customer: ' || customer_name END,
                   CASE WHEN customer_phone IS NOT NULL THEN 'Phone: ' || customer_phone END,
                   CASE WHEN delivery_address IS NOT NULL THEN 'Address: ' || delivery_address END,
                   'Payment status: ' || payment_status,
                   notes)
        """
    )
    for column in ("customer_name", "customer_phone", "product_name", "quantity", "budget", "payment_status", "delivery_address", "notes"):
        op.drop_column("orders", column)
    for column in ("status", "subtotal", "discount", "total", "channel"):
        op.alter_column("orders", column, server_default=None)
    op.create_check_constraint("ck_orders_status", "orders", "status in ('draft', 'posted', 'reversed', 'cancelled')")
    op.create_check_constraint("ck_orders_channel", "orders", "channel in ('pos', 'chat', 'whatsapp', 'voice')")
    op.create_check_constraint("ck_orders_discount_range", "orders", "discount >= 0 and discount <= subtotal")
    op.create_index("uq_orders_tenant_idempotency_key", "orders", ["tenant_id", "idempotency_key"], unique=True)
    op.create_index("ix_orders_tenant_created_at", "orders", ["tenant_id", "created_at"], unique=False)

    op.create_table(
        "order_items",
        *_base_columns(),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(length=120), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("qty > 0", name="ck_order_items_qty_positive"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_tenant_id"), "order_items", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)

    op.create_table(
        "payments",
        *_base_columns(),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("customer_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        sa.CheckConstraint("method in ('cash', 'card', 'bank', 'wallet')", name="ck_payments_method"),
        sa.CheckConstraint("status in ('completed', 'reversed')", name="ck_payments_status"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_tenant_id"), "payments", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_payments_order_id"), "payments", ["order_id"], unique=False)
    op.create_index("ix_payments_tenant_created_at", "payments", ["tenant_id", "created_at"], unique=False)

    op.create_table(
        "ledger_entries",
        *_base_columns(),
        sa.Column("party_type", sa.String(length=10), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("direction", sa.String(length=6), nullable=False),
        sa.Column("ref_type", sa.String(length=30), nullable=True),
        sa.Column("ref_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_ledger_entries_amount_positive"),
        sa.CheckConstraint("party_type in ('customer', 'vendor')", name="ck_ledger_entries_party_type"),
        sa.CheckConstraint("direction in ('debit', 'credit')", name="ck_ledger_entries_direction"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_entries_tenant_id"), "ledger_entries", ["tenant_id"], unique=False)
    op.create_index("ix_ledger_entries_tenant_party", "ledger_entries", ["tenant_id", "party_type", "party_id"], unique=False)

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
            REVOKE UPDATE, DELETE, TRUNCATE ON stock_movements, ledger_entries FROM app_user;
          END IF;
          -- Hosted Postgres (Supabase) grants every new table to the Data API roles by default; take it back.
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
    op.drop_table("ledger_entries")
    op.drop_table("payments")
    op.drop_table("order_items")

    op.drop_index("ix_orders_tenant_created_at", table_name="orders")
    op.drop_index("uq_orders_tenant_idempotency_key", table_name="orders")
    for name in ("ck_orders_discount_range", "ck_orders_channel", "ck_orders_status"):
        op.drop_constraint(name, "orders", type_="check")
    # Lossy by design: a legacy order keeps its note as ``notes``; the product text is not recoverable per column.
    for column, ddl in (
        ("customer_name", sa.String(length=255)),
        ("customer_phone", sa.String(length=30)),
        ("delivery_address", sa.Text()),
        ("notes", sa.Text()),
    ):
        op.add_column("orders", sa.Column(column, ddl, nullable=True))
    op.add_column("orders", sa.Column("product_name", sa.String(length=255), server_default="(migrated)", nullable=False))
    op.add_column("orders", sa.Column("quantity", sa.Integer(), server_default="1", nullable=False))
    op.add_column("orders", sa.Column("budget", sa.Numeric(14, 2), nullable=True))
    op.add_column("orders", sa.Column("payment_status", sa.String(length=50), server_default="pending", nullable=False))
    op.execute("UPDATE orders SET notes = note, budget = total")
    for column in ("note", "created_by", "idempotency_key", "channel", "total", "discount", "subtotal", "status"):
        op.drop_column("orders", column)
    for column in ("product_name", "quantity", "payment_status"):
        op.alter_column("orders", column, server_default=None)

    op.drop_constraint("ck_inventory_items_qty_non_negative", "inventory_items", type_="check")
    op.drop_constraint("uq_inventory_items_tenant_product", "inventory_items", type_="unique")
    op.drop_constraint("fk_inventory_items_product_id_products", "inventory_items", type_="foreignkey")
    op.add_column("inventory_items", sa.Column("sku", sa.String(length=100), nullable=True))
    op.add_column("inventory_items", sa.Column("name", sa.String(length=255), server_default="(migrated)", nullable=False))
    op.add_column("inventory_items", sa.Column("category", sa.String(length=100), nullable=True))
    op.add_column("inventory_items", sa.Column("stock_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("inventory_items", sa.Column("price", sa.Numeric(14, 2), nullable=True))
    op.add_column("inventory_items", sa.Column("incoming_units", sa.Integer(), server_default="0", nullable=False))
    op.add_column("inventory_items", sa.Column("min_threshold", sa.Integer(), server_default="0", nullable=False))
    op.add_column("inventory_items", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("inventory_items", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE inventory_items i SET sku = p.sku, name = p.name, category = p.category, price = p.price, "
        "deleted_at = p.deleted_at, stock_count = i.qty_on_hand, min_threshold = i.reorder_level "
        "FROM products p WHERE p.id = i.product_id"
    )
    for column in ("name", "stock_count", "incoming_units", "min_threshold"):
        op.alter_column("inventory_items", column, server_default=None)
    op.create_index(
        "uq_inventory_items_tenant_sku",
        "inventory_items",
        ["tenant_id", "sku"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    for column in ("product_id", "qty_on_hand", "reorder_level"):
        op.drop_column("inventory_items", column)

    op.drop_table("stock_movements")
    op.drop_table("products")
