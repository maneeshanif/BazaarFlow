"""Task 21: preview per pull request, one-command production deploy, and migrations that never run inside the API.

Hosting (ADR 0003): web on Vercel, API on FastAPI Cloud. Credentials come only from GitHub secrets.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _load(name: str) -> dict[str, Any]:
    doc = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    doc["on"] = doc.get("on", doc.get(True))  # PyYAML reads the bare key `on` as the boolean True
    return doc  # type: ignore[no-any-return]


def _text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_the_preview_workflow_runs_for_every_pull_request() -> None:
    preview = _load("preview.yml")
    assert "pull_request" in preview["on"]


def test_the_preview_never_runs_with_secrets_for_a_fork() -> None:
    """Fork pull requests must not receive deploy tokens."""
    text = _text("preview.yml")
    assert "github.event.pull_request.head.repo.full_name == github.repository" in text
    assert "pull_request_target" not in text


def test_the_preview_deploys_the_web_app_and_reports_the_url() -> None:
    text = _text("preview.yml")
    assert "vercel" in text.lower() and "VERCEL_TOKEN" in text
    assert "pull-requests: write" in text, "the preview URL is posted on the pull request"


def test_production_deploy_is_triggered_by_main_or_by_hand_only() -> None:
    deploy = _load("deploy.yml")
    triggers = deploy["on"]
    assert set(triggers) <= {"push", "workflow_dispatch"}
    assert triggers["push"]["branches"] == ["main"]


def test_migrations_run_before_the_api_deploys_and_use_the_migrator_credential() -> None:
    text = _text("deploy.yml")
    assert "alembic upgrade head" in text
    assert "secrets.DATABASE_URL_MIGRATIONS" in text
    assert text.index("alembic upgrade head") < text.index("fastapi deploy"), "schema first, then code"


def test_the_deploy_uses_the_documented_fastapi_cloud_token_variables() -> None:
    text = _text("deploy.yml")
    assert "secrets.FASTAPI_CLOUD_TOKEN" in text and "secrets.FASTAPI_CLOUD_APP_ID" in text
    assert "fastapi deploy" in text


def test_the_api_image_does_not_run_migrations_or_hold_the_migrator_credential() -> None:
    """app_user has no DDL rights; the runtime container must not be the place migrations run from."""
    dockerfile = (ROOT / "backend.Dockerfile").read_text(encoding="utf-8")
    cmd = [line for line in dockerfile.splitlines() if line.strip().startswith("CMD")]
    assert cmd and "alembic" not in cmd[-1], "run migrations as a deploy step with the migrator role, not at API start"
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "DATABASE_URL_MIGRATIONS" not in compose.split("agent:")[0].split("backend:")[1].split("frontend:")[0]


def test_no_workflow_contains_a_literal_credential() -> None:
    for workflow in WORKFLOWS.glob("*.yml"):
        body = workflow.read_text(encoding="utf-8")
        assert not re.search(r"(?:sk-|AIza|EAA|xox[bp]-|eyJ)[A-Za-z0-9_-]{16,}", body), workflow.name
        for match in re.finditer(r"\b[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|KEY)[A-Z0-9_]*:\s*(\S+)", body):
            assert match.group(1).startswith(("${{", "$", '"${{', "''", '""')), f"{workflow.name}: {match.group(0)}"


def test_workflows_request_the_least_permissions() -> None:
    for name in ("deploy.yml", "preview.yml"):
        doc = _load(name)
        assert "permissions" in doc or all("permissions" in job for job in doc["jobs"].values()), name


def test_the_one_command_deploy_script_exists_and_checks_before_it_ships() -> None:
    script = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")
    for needed in ("DATABASE_URL_MIGRATIONS", "alembic upgrade head", "fastapi deploy", "vercel"):
        assert needed in script
    assert "git status --porcelain" in script, "refuse to deploy a dirty tree"
    assert "verify.sh" in script, "refuse to deploy what has not passed the checks"
