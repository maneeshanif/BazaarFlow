#!/usr/bin/env bash
# Production deploy in one command:   bash scripts/deploy.sh
#
# Refuses to ship a dirty tree or code that has not passed the checks, then: migrations (migrator role) ->
# API on FastAPI Cloud -> web on Vercel. CI does the same on every merge to main (.github/workflows/deploy.yml);
# this is the by-hand version. Needs, in your environment (never in the repo):
#   DATABASE_URL_MIGRATIONS   the migrator connection (session pooler, port 5432)
#   FASTAPI_CLOUD_TOKEN, FASTAPI_CLOUD_APP_ID   or a prior `fastapi login` + linked app
#   VERCEL_TOKEN (+ VERCEL_ORG_ID, VERCEL_PROJECT_ID)   or a prior `vercel login` + linked project
set -euo pipefail
cd "$(dirname "$0")/.."

[ -z "$(git status --porcelain)" ] || { echo "✗ working tree is not clean: commit or stash first"; exit 1; }
: "${DATABASE_URL_MIGRATIONS:?DATABASE_URL_MIGRATIONS is not set (the migrator connection string)}"

echo "→ checks"
bash scripts/verify.sh --slow

echo "→ database migrations"
uv run alembic upgrade head

echo "→ API (FastAPI Cloud)"
uv run fastapi deploy

echo "→ web (Vercel)"
( cd frontend && npx --yes vercel@latest deploy --prod ${VERCEL_TOKEN:+--token="$VERCEL_TOKEN"} )

echo "✓ deployed"
