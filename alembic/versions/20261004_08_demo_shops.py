"""temporary demo shops and a per-shop AI allowance (Phase 1C, task 47)

Revision ID: 20261004_08
Revises: 20261003_07
Create Date: 2026-10-04

* ``tenants.demo_expires_at``: set only for a visitor's demo shop; ``app.cli.purge_demos`` deletes shops past it.
* ``tenants.agent_cap_usd``: an optional monthly AI allowance for one shop (a demo shop gets a few cents);
  null means the platform default (``AGENT_MONTHLY_SPEND_CAP_USD``).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261004_08"
down_revision: str | None = "20261003_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.add_column("tenants", sa.Column("demo_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenants", sa.Column("agent_cap_usd", sa.Numeric(8, 2), nullable=True))
    op.create_index("ix_tenants_demo_expires_at", "tenants", ["demo_expires_at"])


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_index("ix_tenants_demo_expires_at", table_name="tenants")
    op.drop_column("tenants", "agent_cap_usd")
    op.drop_column("tenants", "demo_expires_at")
