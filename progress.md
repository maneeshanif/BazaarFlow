<!-- progress.md — the loop's memory between runs -->

## Done

- 2026-08-17: **Backend architecture audit** — full side-by-side comparison of old flat structure vs new MVC boilerplate written to `docs/audit_1.md`
- 2026-08-17: **Root restructure** — eliminated `backend/` wrapper; backend now lives at root level (`app/`, `alembic/`, `pyproject.toml`)
- 2026-08-17: **MVC folder structure** — created `app/` following `fastapi-starter-boilerplate` pattern with `api/controllers/`, `api/routers/`, `core/`, `models/`, `schemas/`, `agents/`, `services/`, `repositories/`, `integrations/`, `utils/`, `mcp_server/`
- 2026-08-17: **Flat controllers** — renamed `endpoints/{feature}/feature.py` → `controllers/feature_controller.py` (no sub-folders)
- 2026-08-17: **Route parity verified** — all 43 old routes ported to new controllers + 2 new auth routes (45 total); full comparison table in `docs/audit_1.md`
- 2026-08-17: **SQLAlchemy 2.0 ORM models** — 9 models created (User, Vendor, Customer, Message, Order, InventoryItem, MarketingPost, ScheduledCampaign, SupportTicket, FacebookAccount) with UUID PK + timestamp mixins
- 2026-08-17: **Pydantic v2 schemas** — 8 schema files (create + out shapes for every domain)
- 2026-08-17: **Centralised settings** — `app/core/settings.py` (Pydantic BaseSettings); removed all scattered `os.getenv()` calls from agents and services
- 2026-08-17: **Async database layer** — `app/core/database.py` with SQLAlchemy async engine; Supabase PostgreSQL primary + SQLite fallback for local dev
- 2026-08-17: **Alembic async migrations** — `alembic/env.py` wired to async engine; autogenerate-ready
- 2026-08-17: **uv package manager** — root `pyproject.toml` replaces old `requirements.txt`; all deps (SQLAlchemy, asyncpg, aiosqlite, pydantic-settings, alembic, passlib, python-jose) declared
- 2026-08-17: **All services migrated** — `backend/services/` → `app/services/` (chat, finance, inventory, marketing, sales, vapi_support, whatsapp, marketing_scheduler)
- 2026-08-17: **All agents migrated** — `backend/my_agents/` → `app/agents/` (sales, finance, inventory, marketing agents + 4 tool files)
- 2026-08-17: **Repositories layer** — `backend/lib/` → `app/repositories/` (json_store, repository, marketing_repository, marketing_scheduled_repository, user_repository)
- 2026-08-17: **Integrations layer** — `backend/facebook_manager.py`, `fb.py`, `fb_config.py`, `fb_model.py` → `app/integrations/`
- 2026-08-17: **Import paths fixed** — zero relative imports (`..`) remaining; all use absolute `app.*` paths
- 2026-08-17: **Docker setup** — `frontend/Dockerfile`, `backend/Dockerfile`, `docker-compose.yml`; `frontend/next.config.ts` updated with `output: "standalone"`
- 2026-08-17: **Tests migrated** — all 22 test files from `backend/tests/` → `tests/unit/`
- 2026-08-17: **Docs** — `docs/audit_1.md` with old vs new structure comparison, route parity table (45 routes), Docker config

## In progress

- **Services → DB migration**: controllers and services still use JSON file store (`repositories/json_store.py`); need to swap each service method to use SQLAlchemy async session via `get_db()` dependency
- **Auth implementation**: `auth_controller.py` stubs exist; JWT login/register logic not yet wired (needs passlib + python-jose)
- **Alembic first migration**: models are defined but `alembic revision --autogenerate` not yet run against Supabase

## Open / needs a human

- **Supabase credentials**: `DATABASE_URL` in `.env` needs real Supabase connection string before running migrations — copy from Supabase dashboard → Settings → Database
- **Meta / WhatsApp credentials**: `META_VERIFY_TOKEN`, `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN` needed in `.env` before webhook goes live
- **VAPI credentials**: `VAPI_API_KEY` + `VAPI_WEBHOOK_SECRET` + `NEXT_PUBLIC_VAPI_PUBLIC_KEY` needed in `.env` for voice support
- **Pexels API key**: `PEXELS_API_KEY` needed in `.env` for AI-generated marketing post images
- **`backend/` folder deletion**: old backend kept intact as safety net; safe to `Remove-Item -Recurse backend/` once smoke test on new `app/` passes
