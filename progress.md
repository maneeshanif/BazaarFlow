<!-- progress.md â€” the loop's memory between runs -->

## Done

- 2026-08-24: Fixed all 69-module import chain — resolved 7 issues:
  - Fixed `from __future__` ordering in marketing_service, marketing_agent, marketing_tool, repository, whatsapp, finance/inventory/sales/marketing agents
  - `app/repositories/__init__.py` now re-exports all public API (delete_facebook_account, etc.)
  - `app/integrations/facebook_manager.py` relative imports fixed (.config.fb_config → .fb_config)
  - `app/agents/config.py` lazy-init prevents import failure when GEMINI_API_KEY is unset
  - Added `tzdata==2026.3` to `pyproject.toml` for `ZoneInfo('Asia/Karachi')` on Windows
  - Integration tests: 5/5 passing on Python 3.14.3
- 2026-08-24: **Old backend untracked** — Untracked and ignored `backend/` folder to keep it local-only (removed from git repository tracking on `feat/mvc-architecture` branch).
- 2026-08-17: **Backend architecture audit** â€” full side-by-side comparison of old flat structure vs new MVC boilerplate written to `docs/audit_1.md`
- 2026-08-17: **Root restructure** â€” eliminated `backend/` wrapper; backend now lives at root level (`app/`, `alembic/`, `pyproject.toml`)
- 2026-08-17: **MVC folder structure** â€” created `app/` following `fastapi-starter-boilerplate` pattern with `api/controllers/`, `api/routers/`, `core/`, `models/`, `schemas/`, `agents/`, `services/`, `repositories/`, `integrations/`, `utils/`, `mcp_server/`
- 2026-08-17: **Flat controllers** â€” renamed `endpoints/{feature}/feature.py` -> `controllers/feature_controller.py` (no sub-folders)
- 2026-08-17: **Route parity verified** â€” all 43 old routes ported to new controllers + 2 new auth routes (45 total); full comparison table in `docs/audit_1.md`
- 2026-08-17: **SQLAlchemy 2.0 ORM models** â€” 9 models created (User, Vendor, Customer, Message, Order, InventoryItem, MarketingPost, ScheduledCampaign, SupportTicket, FacebookAccount) with UUID PK + timestamp mixins
- 2026-08-17: **Pydantic v2 schemas** â€” 8 schema files (create + out shapes for every domain)
- 2026-08-17: **Centralised settings** â€” `app/core/settings.py` (Pydantic BaseSettings); removed all scattered `os.getenv()` calls from agents and services
- 2026-08-17: **Async database layer** â€” `app/core/database.py` with SQLAlchemy async engine; Supabase PostgreSQL primary + SQLite fallback for local dev
- 2026-08-17: **Alembic async migrations** â€” `alembic/env.py` wired to async engine; autogenerate-ready
- 2026-08-17: **uv package manager** â€” root `pyproject.toml` replaces old `requirements.txt`; all deps declared
- 2026-08-17: **All services migrated** â€” `backend/services/` -> `app/services/` (chat, finance, inventory, marketing, sales, vapi_support, whatsapp, marketing_scheduler)
- 2026-08-17: **All agents migrated** â€” `backend/my_agents/` -> `app/agents/` (sales, finance, inventory, marketing agents + 4 tool files)
- 2026-08-17: **Repositories layer** â€” `backend/lib/` -> `app/repositories/`
- 2026-08-17: **Integrations layer** â€” `backend/facebook_manager.py`, `fb.py`, `fb_config.py`, `fb_model.py` -> `app/integrations/`
- 2026-08-17: **Import paths fixed** â€” zero relative imports (`..`) remaining; all use absolute `app.*` paths
- 2026-08-17: **Docker setup** â€” `frontend/Dockerfile`, `backend/Dockerfile`, `docker-compose.yml`; `frontend/next.config.ts` updated with `output: "standalone"`
- 2026-08-17: **Tests migrated** â€” all 22 test files from `backend/tests/` -> `tests/unit/`
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

- 2026-10-04: **Phase 1 code complete** (batches A, B, C; tasks 34-58, 63-65 done). Committed `75ab8c1` (secret-key test ignores `ALLOW_INSECURE_DEV_SECRET` from the environment); `verify.sh --lane api` passed (322 tests, mypy and ruff clean; Docker was off, so Postgres/RLS tests were skipped).
- 2026-10-04: **Task 12 checked, NOT complete.** Done: no default `SECRET_KEY` fallback (tests guard it) and gitleaks runs in `.github/workflows/security.yml`. Open: `.env.example` is unchanged since the original commit and lacks 24 variables that `docs/operations/env.example.proposed` has (AGENT_*, AGENTS_ENABLED, DEMO_*, LLM_*, OPENAI_*, SIGNUP_MAX_PER_HOUR, STORAGE_*, SUPABASE_URL, SUPABASE_SERVICE_KEY). Fix: `cp docs/operations/env.example.proposed .env.example`.
- 2026-10-04: **Phase status (as of 2026-10-04, superseded by the entries below):** Phase 0 and Phase 1 code closed; Phase 2 not started (tasks 70-85 and deferred 59-62 all open); Phases 3 and 4 not started. Phase 1 carry-overs still open: 02, 12, 21, 26.
- 2026-10-06 to 2026-10-07: **Phase 2 and Phase 3 code built** on `feat/phase-1-mvp`: stock movements, vendors and payables, finance overview, platform admin, integrations (Twilio WhatsApp, Facebook, Pexels), unified inbox, marketing scheduler, onboarding wizard, system logs, marketing insights, automation recipes, VAPI voice agent. Still open: 31 (live VAPI call) and 90 (Meta Embedded Signup) need vendor accounts.
- 2026-10-13: **Deferred workflow steps built** (design brief `docs/superpowers/specs/2026-10-13-deferred-features-design.md`):
  - Recipes retry a transient failure (3 tries), then fall back to filing the messages as approvals, then the existing banner (`2c96261`).
  - Draft purchase orders beside the low-stock reorder message, `/api/v1/purchase-orders` and a screen (`9deff72`).
  - Customer order drafts: the WhatsApp agent's `request_order` files an approval; approving posts the sale on credit and confirms to the customer (`de7af61`).
  - Facebook comment replies: read, propose, approve, post, `/api/v1/marketing/comments` and a screen (`7d4908f`).
  - Urdu/RTL for the core screens, plus the Purchase orders and Comments screens (`0424e2e`).
  - Verified: new Postgres tests, related regression suites, 315 UI tests, token check, typecheck, lint and a production build all pass. **The full `verify.sh --slow --all` gate has NOT completed**: Docker Desktop stopped partway through (fast tier passed: 385 tests, audit clean). Run it once Docker is back.
- 2026-10-13: **Defaults chosen while the owner was away** (change on request): Gemini Flash with a 5 USD per shop per month AI cap; Urdu limited to core screens; platform-admin impersonation not built; legacy JSON routes kept mounted. Urdu strings need a native reader's review. No live Twilio, Facebook, Pexels or Gemini call has been made.

## In progress

- **Services -> DB CRUD wiring**: replacing remaining JSON file store operations in service layers with async SQLAlchemy session calls via `app/crud/`

## Open / needs a human

- **Supabase credentials**: `DATABASE_URL` in `.env` needs real Supabase connection string before running migrations in production
- **Meta / WhatsApp credentials**: `META_VERIFY_TOKEN`, `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN` needed in `.env` before webhook goes live
- **VAPI credentials**: `VAPI_API_KEY` + `VAPI_WEBHOOK_SECRET` + `NEXT_PUBLIC_VAPI_PUBLIC_KEY` needed in `.env` for voice support
- **Pexels API key**: `PEXELS_API_KEY` needed in `.env` for AI-generated marketing post images
- **`backend/` folder status**: old backend has been untracked and ignored (local-only backup); safe to remove permanently once full production smoke testing is complete