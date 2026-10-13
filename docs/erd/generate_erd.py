#!/usr/bin/env python3
"""
Regenerates every docs/erd/*.md diagram from the database schema. The migrations
are the source of truth; a diagram can never describe a schema that does not exist.

Two sources, same output:

  python3 docs/erd/generate_erd.py                 introspects the LIVE database (needs it running and migrated)
  uv run python docs/erd/generate_erd.py --from-models
                                                   reads the SQLAlchemy models. `alembic check` (part of
                                                   scripts/verify.sh) fails when the models and the migrations
                                                   differ, so on a green build this is the same schema.

Config: docs/erd/erd.config.json
  {
    "psql": ["docker", "compose", "exec", "-T", "db", "psql", "-U", "app", "-d", "app"],   (optional)
    "cwd": "infra",                                                                          (optional)
    "diagrams": [
      { "name": "Orders", "output": "orders.md", "template": "orders.template.md",
        "tables": { "Orders": ["orders", "order_items"] },
        "hide_fk_to": ["tenants"],      (optional: relationship lines to these tables are left out; the FK
                                         marker on the column stays)
        "columns": false }              (optional: false draws entities only, for an overview)
    ]
  }
"cwd" is relative to the repo root. If "psql" is omitted, `psql "$DATABASE_URL"` is used.

Each template holds the hand-written prose plus a {{DIAGRAM}} placeholder.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ERD_DIR = Path(__file__).resolve().parent
REPO_ROOT = ERD_DIR.parents[1]
CONFIG = json.loads((ERD_DIR / "erd.config.json").read_text(encoding="utf-8"))

TYPE_MAP = {
    "character varying": "varchar",
    "timestamp with time zone": "timestamptz",
    "timestamp without time zone": "timestamp",
    "time without time zone": "time",
}


def mermaid_type(raw: str) -> str:
    """A type name Mermaid accepts: no spaces, commas or parentheses (varchar(255) -> varchar_255)."""
    text = TYPE_MAP.get(raw.lower(), raw.lower())
    text = re.sub(r"\s*\(\s*([^)]*)\)", lambda m: "_" + re.sub(r"[\s,]+", "_", m.group(1).strip()), text)
    return re.sub(r"[^a-z0-9_]+", "_", text).strip("_")


# -- source 1: the live database ----------------------------------------------------------------------------------


def psql_base() -> list[str]:
    if CONFIG.get("psql"):
        return list(CONFIG["psql"])
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit('Set DATABASE_URL or configure "psql" in erd.config.json (or use --from-models).')
    return ["psql", url]


def run_sql(sql: str) -> list[list[str]]:
    cwd = REPO_ROOT / CONFIG["cwd"] if CONFIG.get("cwd") else REPO_ROOT
    try:
        result = subprocess.run(
            [*psql_base(), "-t", "-A", "-F|", "-c", sql],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Could not query the database - is it running and migrated?\n{exc.stderr}")
    return [line.split("|") for line in result.stdout.splitlines() if line.strip()]


def in_list(tables: list[str]) -> str:
    return ",".join("'" + t.replace("'", "''") + "'" for t in tables)


def db_columns(tables: list[str]) -> list[list[str]]:
    return run_sql(f"""
        SELECT c.table_name, c.column_name, c.data_type,
               CASE WHEN pk.column_name IS NOT NULL THEN 'Y' ELSE '' END
        FROM information_schema.columns c
        LEFT JOIN (
          SELECT ku.table_name, ku.column_name
          FROM information_schema.table_constraints tc
          JOIN information_schema.key_column_usage ku
            ON tc.constraint_name = ku.constraint_name AND tc.table_schema = ku.table_schema
          WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public'
        ) pk ON pk.table_name = c.table_name AND pk.column_name = c.column_name
        WHERE c.table_schema = 'public' AND c.table_name IN ({in_list(tables)})
        ORDER BY c.table_name, c.ordinal_position;""")


def db_foreign_keys(tables: list[str]) -> list[list[str]]:
    return run_sql(f"""
        SELECT tc.table_name, kcu.column_name, ccu.table_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
          AND tc.table_name IN ({in_list(tables)})
        ORDER BY tc.table_name, kcu.column_name;""")


# -- source 2: the models -----------------------------------------------------------------------------------------


def load_metadata():  # type: ignore[no-untyped-def]
    sys.path.insert(0, str(REPO_ROOT))
    import app.models  # noqa: F401  (registers every table on Base.metadata)
    from app.core.database import Base

    return Base.metadata


def model_columns(tables: list[str]) -> list[list[str]]:
    from sqlalchemy.dialects import postgresql

    meta = load_metadata()
    rows: list[list[str]] = []
    for name in tables:
        if name not in meta.tables:
            sys.exit(f"erd.config.json names a table that no model defines: {name}")
        table = meta.tables[name]
        for column in table.columns:
            dtype = str(column.type.compile(dialect=postgresql.dialect()))
            rows.append([name, column.name, dtype, "Y" if column.primary_key else ""])
    return rows


def model_foreign_keys(tables: list[str]) -> list[list[str]]:
    meta = load_metadata()
    rows: list[list[str]] = []
    for name in tables:
        for column in meta.tables[name].columns:
            for fk in column.foreign_keys:
                rows.append([name, column.name, fk.column.table.name])
    return sorted(rows)


# -- rendering ----------------------------------------------------------------------------------------------------


def build(
    groups: dict[str, list[str]],
    columns: list[list[str]],
    fks: list[list[str]],
    hide_fk_to: set[str] | None = None,
    show_columns: bool = True,
) -> str:
    hide = hide_fk_to or set()
    all_tables = [t for g in groups.values() for t in g]
    in_diagram = set(all_tables)
    fk_cols = {(t, c) for t, c, _ in fks}
    by_table: dict[str, list[str]] = {t: [] for t in all_tables}
    # primary key first, then the shop key, then the table's own columns, then the bookkeeping timestamps
    bookkeeping = {"created_at": 1, "updated_at": 2, "deleted_at": 3}

    def rank(row: list[str]) -> int:
        _table, column, _dtype, is_pk = row
        if is_pk == "Y":
            return 0
        if column == "tenant_id":
            return 1
        return 100 + bookkeeping.get(column, 0)

    for _, (table, column, dtype, is_pk) in sorted(enumerate(columns), key=lambda item: (item[1][0], rank(item[1]), item[0])):
        marker = " PK" if is_pk == "Y" else (" FK" if (table, column) in fk_cols else "")
        by_table[table].append(f"        {mermaid_type(dtype)} {column}{marker}")
    lines = ["erDiagram"]
    for group, tables in groups.items():
        lines.append(f"    %% {group}")
        for table in tables:
            if show_columns:
                lines.append(f"    {table} {{")
                lines.extend(by_table[table])
                lines.append("    }")
            else:
                lines.append(f"    {table}")
    lines.append("")
    seen: set[tuple[str, str, str]] = set()
    for from_table, from_column, to_table in fks:
        if to_table in hide or to_table not in in_diagram:
            continue  # a table that is not on this diagram would appear as an empty box
        if (to_table, from_table, from_column) in seen:
            continue
        seen.add((to_table, from_table, from_column))
        lines.append(f'    {to_table} ||--o{{ {from_table} : "{from_column}"')
    return "\n".join(lines)


def render_all(from_models: bool) -> dict[Path, str]:
    """Every output file and what it should contain. Used by main() and by the drift test."""
    fetch_columns = model_columns if from_models else db_columns
    fetch_fks = model_foreign_keys if from_models else db_foreign_keys
    out: dict[Path, str] = {}
    for d in CONFIG["diagrams"]:
        tables = [t for g in d["tables"].values() for t in g]
        rendered = build(
            d["tables"],
            fetch_columns(tables),
            fetch_fks(tables),
            set(d.get("hide_fk_to", [])),
            d.get("columns", True),
        )
        template = (ERD_DIR / d["template"]).read_text(encoding="utf-8")
        out[ERD_DIR / d["output"]] = template.replace("{{DIAGRAM}}", rendered)
    return out


def main() -> None:
    for path, text in render_all("--from-models" in sys.argv[1:]).items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
