"""system logs: let a platform operator read the audit trail across shops (Phase 3, task 89)

Revision ID: 20261007_13
Revises: 20261006_12
Create Date: 2026-10-07

One SELECT policy on ``audit_logs`` keyed on ``app_is_platform()`` (set only by ``platform_session``). The audit trail stays
append-only and an operator can read it, never change it.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261007_13"
down_revision: str | None = "20261006_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE POLICY platform_select ON audit_logs FOR SELECT USING (app_is_platform())")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP POLICY IF EXISTS platform_select ON audit_logs")
