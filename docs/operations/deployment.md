# Deployment runbook (ADR 0003)

| Part | Host | How it ships |
|---|---|---|
| Web (Next.js) | Vercel | PR preview: `.github/workflows/preview.yml`. Production: `deploy.yml` / `scripts/deploy.sh` |
| API (FastAPI) | FastAPI Cloud | `uv run fastapi deploy` (entrypoint `app.main:app`, `[tool.fastapi]` in `pyproject.toml`) |
| Agent service | FastAPI Cloud (second app) | not deployed yet: it answers 501 until the tool-call path exists (phase 1) |
| Database | Supabase | migrations by the migrator role, as a deploy step: never inside the API container |

## One-time setup (owner)
1. **Supabase dev / staging / prod projects** and role provisioning: `docs/operations/supabase-setup.md`.
2. **FastAPI Cloud**: `uv run fastapi login`, then `uv run fastapi deploy` once from the repo root to create the app.
   Set the runtime variables as secrets (they take effect on the next deploy):
   `uv run fastapi cloud env set SECRET_KEY <value> --secret`, and the same for `DATABASE_URL` (the `app_user`
   transaction-pooler URL), `GEMINI_API_KEY`, `META_APP_SECRET`, `META_VERIFY_TOKEN`; plain
   `FRONTEND_ORIGIN <web url>` and `APP_ENV production`. Never set `DATABASE_URL_MIGRATIONS` or any admin
   password on the API.
3. **Vercel**: import the repo with root directory `frontend`; set `NEXT_PUBLIC_API_BASE_URL` and `API_INTERNAL_URL`
   (the FastAPI Cloud URL) for Production and Preview.
4. **GitHub secrets** (Settings -> Secrets and variables -> Actions): `DATABASE_URL_MIGRATIONS`,
   `FASTAPI_CLOUD_TOKEN` and `FASTAPI_CLOUD_APP_ID` (app -> Deploy Tokens, or
   `uv run fastapi cloud setup-ci --secrets-only --app-id <id>`), `VERCEL_TOKEN`, `VERCEL_ORG_ID`,
   `VERCEL_PROJECT_ID`. Create a GitHub environment named `production` (add required reviewers if you want a gate).

## Deploying
- Automatic: every merge to `main` runs `deploy.yml` (migrate -> API -> web).
- By hand, one command from a clean checkout: `bash scripts/deploy.sh` (runs `verify.sh --slow` first).
- Rollback: redeploy the previous commit (`git revert` + merge, or re-run the workflow on an older commit).
  Migrations are forward-only in production; ship a corrective migration rather than downgrading.

## Previews
Every pull request from this repository gets a Vercel web preview, posted as a comment. It talks to the shared
staging API (set the Preview variables in Vercel to the staging API). A separate API preview per pull request is
not set up: FastAPI Cloud's documentation does not describe per-branch apps, so verify before promising it.

## Not verified yet (check before relying on it)
FastAPI Cloud regions, free-tier limits, background tasks (the marketing scheduler starts inside the API process),
and outbound connections to the Supabase pooler. Nothing here has been deployed from this repository yet.
