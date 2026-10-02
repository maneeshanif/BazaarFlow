"""Task 03 acceptance: the data model follows PRD §12.2 (checked against the SQLAlchemy metadata).

PRD §12.2: lower_snake_case plural tables; UUID primary keys; created_at/updated_at timestamptz; soft delete
(deleted_at) on catalog and party tables; money NUMERIC(14,2); optimistic concurrency (version) on orders and
inventory_items; every business table has tenant_id plus indexes starting with tenant_id; unique constraints are
per tenant.
"""

from __future__ import annotations

import re

from sqlalchemy import DateTime, Float, Index, Numeric, UniqueConstraint, Uuid
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import Table

from app.core.database import Base
from app.models import *  # noqa: F403 - register every model on Base.metadata

TABLES: dict[str, Table] = dict(Base.metadata.tables)


def _is_tz(column_type: object) -> bool:
    return isinstance(column_type, DateTime) and bool(column_type.timezone)

# Not tenant-owned by design (reason is the contract; see tests/pg/test_schema_rules.py).
GLOBAL = {"users", "tenants", "refresh_tokens", "login_attempts"}
# Append-only tables have no updated_at.
APPEND_ONLY = {"audit_logs", "login_attempts"}
SOFT_DELETE = {"customers", "vendors", "inventory_items"}
VERSIONED = {"orders", "inventory_items"}
MONEY_WORDS = ("price", "cost", "amount", "balance", "total", "budget")
# Unique constraints that are global on purpose.
GLOBAL_UNIQUE = {
    ("tenants", ("slug",)),
    ("users", ("email",)),
    ("refresh_tokens", ("token_hash",)),
    ("tenant_integrations", ("provider", "external_id")),  # webhook routing must resolve across tenants
    ("facebook_accounts", ("page_id",)),  # one Facebook page connects to one tenant
}


def _tenant_tables() -> list[Table]:
    return [t for name, t in TABLES.items() if name not in GLOBAL]


def test_names_are_lower_snake_case_and_tables_are_plural() -> None:
    bad_tables = [n for n in TABLES if not re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)*s", n)]
    assert not bad_tables, f"tables must be lower_snake_case plurals: {bad_tables}"
    bad_cols = [f"{n}.{c.name}" for n, t in TABLES.items() for c in t.c if not re.fullmatch(r"[a-z][a-z0-9_]*", c.name)]
    assert not bad_cols, f"columns must be lower_snake_case: {bad_cols}"


def test_every_primary_key_is_a_single_uuid_column_named_id() -> None:
    bad = [
        n for n, t in TABLES.items() if [c.name for c in t.primary_key.columns] != ["id"] or not isinstance(t.c.id.type, Uuid)
    ]
    assert not bad, f"primary keys must be a UUID column named id: {bad}"


def test_timestamps_are_timezone_aware() -> None:
    bad = []
    for n, t in TABLES.items():
        wanted = ["created_at"] if n in APPEND_ONLY else ["created_at", "updated_at"]
        for col in wanted:
            if col not in t.c or not _is_tz(t.c[col].type):
                bad.append(f"{n}.{col}")
    assert not bad, f"missing or naive timestamps: {bad}"


def test_money_is_numeric_14_2_and_never_float() -> None:
    bad = []
    for n, t in TABLES.items():
        for c in t.c:
            if isinstance(c.type, Float):
                bad.append(f"{n}.{c.name} is a float")
            if any(w in c.name for w in MONEY_WORDS) and not (
                isinstance(c.type, Numeric) and (c.type.precision, c.type.scale) == (14, 2)
            ):
                bad.append(f"{n}.{c.name} is {c.type!r}, expected NUMERIC(14,2)")
    assert not bad, "money columns: " + "; ".join(bad)


def test_catalog_and_party_tables_are_soft_deleted() -> None:
    bad = [
        n
        for n in SOFT_DELETE
        if "deleted_at" not in TABLES[n].c
        or not _is_tz(TABLES[n].c.deleted_at.type)
        or TABLES[n].c.deleted_at.nullable is not True
    ]
    assert not bad, f"soft delete (nullable timestamptz deleted_at) missing on: {sorted(bad)}"


def test_orders_and_inventory_use_optimistic_concurrency() -> None:
    configure_mappers()
    bad = []
    for n in VERSIONED:
        table = TABLES[n]
        mapper = next(m for m in Base.registry.mappers if m.local_table is table)
        if "version" not in table.c or mapper.version_id_col is None or mapper.version_id_col.name != "version":
            bad.append(n)
    assert not bad, f"version column / version_id_col missing on: {sorted(bad)}"


def test_every_tenant_table_has_an_index_that_starts_with_tenant_id() -> None:
    bad = []
    for t in _tenant_tables():
        firsts = [list(i.columns)[0].name for i in t.indexes if len(i.columns)]
        firsts += [list(c.columns)[0].name for c in t.constraints if isinstance(c, UniqueConstraint) and len(c.columns)]
        if "tenant_id" not in firsts:
            bad.append(t.name)
    assert not bad, f"no index starting with tenant_id on: {bad}"


def test_unique_constraints_on_tenant_tables_are_per_tenant() -> None:
    bad = []
    for t in _tenant_tables():
        uniques: list[tuple[str, ...]] = [tuple(c.name for c in u.columns) for u in t.constraints if isinstance(u, UniqueConstraint)]
        uniques += [tuple(c.name for c in i.columns) for i in t.indexes if isinstance(i, Index) and i.unique]
        uniques += [(c.name,) for c in t.c if c.unique and not c.primary_key]
        for cols in uniques:
            if "tenant_id" not in cols and (t.name, cols) not in GLOBAL_UNIQUE:
                bad.append(f"{t.name}{cols}")
    assert not bad, f"unique constraints that are not per tenant (and not on the allowlist): {bad}"
