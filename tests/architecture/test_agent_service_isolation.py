"""Task 28: the agent service cannot reach the database, by construction (ADR 0003).

Three independent barriers: its code never imports a database layer, its container gets no database variable,
and its image does not contain the database code.
"""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "agent_service"

FORBIDDEN_MODULES = (
    "sqlalchemy",
    "asyncpg",
    "psycopg",
    "psycopg2",
    "alembic",
    "app.core.database",
    "app.core.database_ro",
    "app.core.tenancy",
    "app.models",
    "app.crud",
    "app.repositories",
    "app.cli",
)
DB_WORDS = ("DATABASE", "POSTGRES", "SUPABASE", "PGPASSWORD", "PGHOST", "DB_URL")


def _imports(path: Path) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def test_the_service_package_exists_and_has_code() -> None:
    assert (SERVICE / "main.py").is_file() and (SERVICE / "settings.py").is_file()


def test_no_agent_service_module_imports_a_database_layer() -> None:
    offenders = {
        str(path.relative_to(ROOT)): [m for m in _imports(path) if m.startswith(FORBIDDEN_MODULES)]
        for path in SERVICE.rglob("*.py")
    }
    offenders = {k: v for k, v in offenders.items() if v}
    assert not offenders, f"the agent service must not import database code: {offenders}"


def test_the_compose_agent_service_gets_no_database_variable() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    agent = compose["services"]["agent"]
    env = agent.get("environment", [])
    names = [e.split("=", 1)[0] for e in env] if isinstance(env, list) else list(env)
    assert not [n for n in names if any(w in n.upper() for w in DB_WORDS)], names
    assert "env_file" not in agent, "an env_file would hand the agent every secret in .env, database URLs included"


def test_the_agent_image_does_not_contain_the_database_code() -> None:
    dockerfile = (ROOT / "agent.Dockerfile").read_text(encoding="utf-8")
    copied = [line for line in dockerfile.splitlines() if line.strip().upper().startswith("COPY ")]
    text = "\n".join(copied)
    assert "agent_service" in text
    for forbidden in ("alembic", "app/models", "app/crud", "app/core", "app/repositories"):
        assert forbidden not in text, f"agent.Dockerfile copies {forbidden}"
