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

# The agent service may import nothing from the API package at all: not `app.x`, not `from app import y`, not `app`.
# (Anything in `app` can pull in the whole backend, database layer included.) Database drivers are forbidden too.
FORBIDDEN_ROOTS = (
    "app",
    "sqlalchemy",
    "asyncpg",
    "psycopg",
    "psycopg2",
    "alembic",
    "aiosqlite",
    "databases",
    "sqlmodel",
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
        str(path.relative_to(ROOT)): [m for m in _imports(path) if m.split(".")[0] in FORBIDDEN_ROOTS]
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


ALLOWED_COPY_SOURCES = {"pyproject.toml", "uv.lock", "README.md", "agent_service/"}


def test_the_agent_image_copies_only_allow_listed_sources() -> None:
    """An allow-list: `COPY app/ ./app/` or `COPY . .` (the easy mistakes) must fail, not slip past a deny-list."""
    dockerfile = (ROOT / "agent.Dockerfile").read_text(encoding="utf-8")
    sources: set[str] = set()
    for line in dockerfile.splitlines():
        parts = line.split()
        if parts and parts[0].upper() == "COPY" and not any(p.startswith("--from") for p in parts):
            args = [p for p in parts[1:] if not p.startswith("--")]
            sources.update(args[:-1])  # the last argument is the destination
    assert sources, "the agent image must copy its service code"
    assert sources <= ALLOWED_COPY_SOURCES, f"agent.Dockerfile copies {sorted(sources - ALLOWED_COPY_SOURCES)}"
    assert "agent_service/" in sources


def test_the_image_installs_the_locked_dependencies_but_never_copies_the_api_source() -> None:
    """Database drivers exist on disk (the lockfile is shared with the API), which is exactly why the import test
    and the startup guard both exist."""
    dockerfile = (ROOT / "agent.Dockerfile").read_text(encoding="utf-8")
    assert "uv sync --frozen" in dockerfile
    assert "COPY app/" not in dockerfile and "COPY . " not in dockerfile
