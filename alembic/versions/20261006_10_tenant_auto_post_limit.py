"""per-shop auto-post limit (Phase 2, task 78)

Revision ID: 20261006_10
Revises: 20261006_09
Create Date: 2026-10-06

``tenants.auto_post_limit``: the largest sale (in PKR) the sales agent may post without asking the owner. Null means the
platform default (``AGENT_AUTO_POST_LIMIT``, PKR 0: every AI write waits for approval). Only the owner can change it
(F-020), and the change is audited.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261006_10"
down_revision: str | None = "20261006_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.add_column("tenants", sa.Column("auto_post_limit", sa.Numeric(14, 2), nullable=True))
    op.create_check_constraint("ck_tenants_auto_post_limit_non_negative", "tenants", "auto_post_limit >= 0")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_constraint("ck_tenants_auto_post_limit_non_negative", "tenants", type_="check")
    op.drop_column("tenants", "auto_post_limit")
