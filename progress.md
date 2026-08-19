<!-- progress.md — the loop's memory between runs -->

## Done

- 2026-08-17: **Backend architecture audit** — full side-by-side comparison of old flat structure vs new MVC boilerplate written to `docs/audit_1.md`
- 2026-08-17: **Root restructure** — eliminated `backend/` wrapper; backend now lives at root level (`app/`, `alembic/`, `pyproject.toml`)
- 2026-08-17: **MVC folder structure** — created `app/` following `fastapi-starter-boilerplate` pattern with `api/controllers/`, `api/routers/`, `core/`, `models/`, `schemas/`, `agents/`, `services/`, `repositories/`, `integrations/`, `utils/`, `mcp_server/`
- 2026-08-17: **Flat controllers** — renamed `endpoints/{feature}/feature.py` -> `controllers/feature_controller.py` (no sub-folders)
- 2026-08-17: **Route parity verified** — all 43 old routes ported to new controllers + 2 new auth routes (45 total); full comparison table in `docs/audit_1.md`
- 2026-08-17: **SQLAlchemy 2.0 ORM models** — 9 models created (User, Vendor, Customer, Message, Order, InventoryItem, MarketingPost, ScheduledCampaign, SupportTicket, FacebookAccount) with UUID PK + timestamp mixins
- 2026-08-17: **Pydantic v2 schemas** — 8 schema files (create + out shapes for every domain)
- 2026-08-17: **Centralised settings** — `app/core/settings.py` (Pydantic BaseSettings); removed all scattered `os.getenv()` calls from agents and services
- 2026-08-17: **Async database layer** — `app/core/database.py` with SQLAlchemy async engine; Supabase PostgreSQL primary + SQLite fallback for local dev
- 2026-08-17: **Alembic async migrations** — `alembic/env.py` wired to async engine; autogenerate-ready
- 2026-08-17: **uv package manager** — root `pyproject.toml` replaces old `requirements.txt`; all deps declared
- 2026-08-17: **All services migrated** — `backend/services/` -> `app/services/` (chat, finance, inventory, marketing, sales, vapi_support, whatsapp, marketing_scheduler)
- 2026-08-17: **All agents migrated** — `backend/my_agents/` -> `app/agents/` (sales, finance, inventory, marketing agents + 4 tool files)
- 2026-08-17: **Repositories layer** — `backend/lib/` -> `app/repositories/`
- 2026-08-17: **Integrations layer** — `backend/facebook_manager.py`, `fb.py`, `fb_config.py`, `fb_model.py` -> `app/integrations/`
- 2026-08-17: **Import paths fixed** — zero relative imports (`..`) remaining; all use absolute `app.*` paths
- 2026-08-17: **Docker setup** — `frontend/Dockerfile`, `backend/Dockerfile`, `docker-compose.yml`; `frontend/next.config.ts` updated with `output: "standalone"`
- 2026-08-17: **Tests migrated** — all 22 test files from `backend/tests/` -> `tests/unit/`
- 2026-08-19: **v3 Production Architecture implemented**:
  - `app/core/security.py` with direct bcrypt password hashing and JWT token creation/verification
  - `app/core/database_ro.py` with read-only async engine for safe analytics/queries
  - `app/schemas/common.py` with `PaginatedResponse`, `ErrorDetail`, `HealthResponse`
  - `app/utils/streaming.py` with SSE streaming helpers for chat endpoints
  - `app/crud/` 8 CRUD files (user, vendor, customer, inventory, order, marketing, support, message)
  - `app/middleware/request_logger.py` and `app/middleware/rate_limiter.py` added to `app/main.py`
  - `app/prompts/` 4 markdown system prompt templates (sales, finance, inventory, marketing) + `load_prompt` utility
  - `app/cli/seed.py` and `app/cli/export.py` management commands tested and verified
  - `app/api/routers/v1/` versioned router aggregation
  - `tests/conftest.py` with isolated in-memory SQLite fixtures + httpx AsyncClient
  - `tests/integration/test_health_and_controllers.py` integration test suite passing (5/5)
  - Full `uv sync` resolution with zero import/build errors

## In progress

- **Services -> DB CRUD wiring**: replacing remaining JSON file store operations in service layers with async SQLAlchemy session calls via `app/crud/`

## Open / needs a human

- **Supabase credentials**: `DATABASE_URL` in `.env` needs real Supabase connection string before running migrations in production
- **Meta / WhatsApp credentials**: `META_VERIFY_TOKEN`, `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN` needed in `.env` before webhook goes live
- **VAPI credentials**: `VAPI_API_KEY` + `VAPI_WEBHOOK_SECRET` + `NEXT_PUBLIC_VAPI_PUBLIC_KEY` needed in `.env` for voice support
- **Pexels API key**: `PEXELS_API_KEY` needed in `.env` for AI-generated marketing post images
- **`backend/` folder deletion**: old backend kept intact as safety net; safe to remove once full production smoke testing is complete