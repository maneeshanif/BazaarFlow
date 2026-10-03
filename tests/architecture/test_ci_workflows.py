"""Task 02 acceptance: CI is wired to verify.sh, and the secret and dependency scans exist.

* every lane in scripts/verify.sh has a workflow that runs ``bash scripts/verify.sh --lane <lane>``
* the secret scan (gitleaks) and workflow lint (actionlint) run in CI
* the dependency scans are verify.sh steps (so CI and local runs cannot drift) in the slow tier
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
VERIFY = (ROOT / "scripts" / "verify.sh").read_text(encoding="utf-8")

LANES = sorted({name.replace("_", "-") for name in re.findall(r"^lane_([a-z_]+)\(\)", VERIFY, flags=re.M)})


def _run_commands(workflow: Path) -> list[str]:
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    commands: list[str] = []
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            if "run" in step:
                commands.append(step["run"])
    return commands


def test_verify_sh_defines_the_expected_lanes() -> None:
    assert LANES == ["api", "api-db", "infra", "web"]


@pytest.mark.parametrize("lane", LANES)
def test_every_lane_has_a_workflow_that_calls_verify_sh(lane: str) -> None:
    workflow = WORKFLOWS / f"{lane}.yml"
    assert workflow.is_file(), f"no workflow for lane {lane}"
    assert any(f"bash scripts/verify.sh --lane {lane}" in cmd for cmd in _run_commands(workflow))


def test_the_workflows_run_the_slow_tier_in_ci() -> None:
    """verify.sh defaults to the slow tier when CI=true, which GitHub Actions sets."""
    assert 'CI:-}" = "true"' in VERIFY.replace(" ", "") or '"${CI:-}" = "true"' in VERIFY


def test_secret_scan_and_workflow_lint_run_in_ci() -> None:
    commands = "\n".join(_run_commands(WORKFLOWS / "security.yml"))
    assert "gitleaks detect" in commands
    assert "actionlint" in commands


def test_python_dependency_scan_is_a_slow_verify_step() -> None:
    assert re.search(r'slow_step\s+"api: dependency audit"[^\n]*pip-audit', VERIFY), "api lane has no pip-audit step"


def test_node_dependency_scan_is_a_slow_verify_step() -> None:
    """The gate wraps `npm audit` with a reviewed, expiring allow-list (frontend/scripts/check-audit.mjs)."""
    assert re.search(r'slow_step\s+"web: dependency audit[^"]*"[^\n]*check:audit', VERIFY), "web lane has no audit gate"
    gate = (ROOT / "frontend" / "scripts" / "check-audit.mjs").read_text(encoding="utf-8")
    assert "npm audit --json" in gate


def test_the_migration_check_can_never_target_a_persistent_database() -> None:
    """Incident 2026-10-03: `verify.sh --slow` ran `alembic downgrade base` against the real Supabase project, because a
    DATABASE_URL_MIGRATIONS in .env wins over the DATABASE_URL the lane sets. The step must pin both variables to the
    throwaway database, refuse a non-local one, and stop at the first failing command (set -e is ignored in conditionals)."""
    body = VERIFY[VERIFY.index("api_db_migrations() {") : VERIFY.index("lane_api_db() {")]
    assert 'export DATABASE_URL="$url" DATABASE_URL_MIGRATIONS="$url"' in body
    assert "refusing to run migrations" in body and "localhost|127" in body
    for command in ("upgrade head", "check", "downgrade base"):
        assert re.search(rf"alembic {command} \|\| return 1", body), f"alembic {command} must stop the step when it fails"
    assert body.index("refusing to run migrations") < body.index("uv run alembic downgrade base")
