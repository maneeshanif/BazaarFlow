#!/usr/bin/env bash
# Proves the project starts from a clean clone: no leftover venv, no node_modules, nothing from your working tree
# except what is committed. Clones HEAD into a temp folder, installs from the lockfiles, and checks that
#   - the API imports and answers /health
#   - the agent service imports and answers /health
#   - the web app type-checks
# Usage: bash scripts/check_clean_clone.sh        (commit first: it tests what git has, not your edits)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone --quiet --local "$ROOT" "$TMP/clone"
cd "$TMP/clone"

echo "→ API and agent service (uv sync --frozen)"
uv sync --frozen --quiet
APP_ENV=test uv run python - <<'PY'
from fastapi.testclient import TestClient

from agent_service.main import create_app
from agent_service.settings import AgentServiceSettings
from app.main import app

with TestClient(app) as client:
    assert client.get("/health").status_code == 200, "API /health"
print("api /health ok")
with TestClient(create_app(AgentServiceSettings(APP_ENV="test"))) as client:
    assert client.get("/health").json()["service"] == "agent-service", "agent /health"
print("agent-service /health ok")
PY

echo "→ web (npm ci, typecheck)"
cd frontend
npm ci --no-audit --no-fund --silent
npx tsc --noEmit
echo "✓ clean clone starts"
