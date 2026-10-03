"""Task 01 acceptance: every folder and file in PRD §3.4 exists, and each part has a smoke test.

The tree below is copied from PRD §3.4. If the PRD layout changes, this list changes with it.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

PRD_LAYOUT = [
    "app/api/controllers",
    "app/api/routers",
    "app/api/routers/v1",
    "app/agents",
    "app/agents/tools",
    "app/services",
    "app/crud",
    "app/repositories",
    "app/models",
    "app/schemas",
    "app/integrations",
    "app/core",
    "app/middleware",
    "app/prompts",
    "app/mcp_server",
    "app/cli",
    "app/utils",
    "agent_service",
    "alembic",
    "frontend",
    "tests/unit",
    "tests/integration",
    "tests/architecture",
    "docs/prd",
    "docs/adr",
    "context",
    "docker-compose.yml",
    "backend.Dockerfile",
    "agent.Dockerfile",
    "pyproject.toml",
]


@pytest.mark.parametrize("path", PRD_LAYOUT)
def test_prd_layout_path_exists(path: str) -> None:
    assert (ROOT / path).exists(), f"PRD §3.4 lists {path} but it does not exist"


def test_main_router_exists_in_the_routers_folder() -> None:
    assert (ROOT / "app/api/routers/main_router.py").is_file()


def test_the_api_part_imports() -> None:
    """Smoke test for the API part: the application object builds and serves /health."""
    main = importlib.import_module("app.main")
    paths = main.app.openapi()["paths"]
    assert "/health" in paths


def test_the_web_part_has_a_buildable_package() -> None:
    """Smoke test for the web part. The actual build runs in `verify.sh --slow --lane web`."""
    package = ROOT / "frontend" / "package.json"
    assert package.is_file()
    assert (ROOT / "frontend" / "package-lock.json").is_file(), "lockfile is required for `npm ci`"
    assert (ROOT / "frontend" / "tsconfig.json").is_file()
