# BazaarFlow Backend — Old vs New: Full Feature Comparison Report

---

## 🗺️ Root Layout Change

The biggest structural change: **all backend files move to the project root** — the `backend/` wrapper folder is eliminated.

```
BEFORE                              AFTER
──────────────────────              ──────────────────────────────
c:/code/BazaarFlow/                 c:/code/BazaarFlow/
├── backend/           ← wrap       ├── app/               ✅ New MVC app package
│   ├── app.py                      │   ├── main.py        ✅ single entrypoint
│   ├── controllers/                │   ├── api/
│   ├── services/                   │   ├── core/
│   ├── ...                         │   ├── models/
│                                   │   ├── schemas/
│                                   │   ├── agents/
│                                   │   ├── integrations/
│                                   │   ├── services/
│                                   │   └── utils/
└── frontend/         ✅ stays      ├── alembic/            ✅ New migrations
                                    ├── alembic.ini
                                    ├── pyproject.toml
                                    ├── .env.example
                                    └── frontend/          ✅ stays untouched
```

---

## 📊 Feature-by-Feature: Old vs New

### 1. App Entrypoint & Configuration

| | OLD | NEW |
|---|---|---|
| **File** | `backend/app.py` | `app/main.py` |
| **Config** | `os.getenv(...)` scattered across 15+ files | `app/core/settings.py` — single Pydantic `BaseSettings` class |
| **Env validation** | Silent `None` if missing | Raises on startup if a required variable is not set |
| **CORS** | Hardcoded `"http://localhost:3000"` string in `app.py` | Read from `settings.FRONTEND_ORIGIN` |
| **Router registration** | 8 `app.include_router(x)` calls in `app.py` | One line: `app.include_router(main_router)` |
| **Dummy file** | `backend/main.py` — `print("Hello from server!")` | **Deleted** |
| **Lifespan** | `httpx.AsyncClient` created in `app.py` | Injected via `core/dependencies.py` `get_http_client` |

---

### 2. Database Layer

| | OLD | NEW |
|---|---|---|
| **Technology** | Local JSON flat files with POSIX locking | PostgreSQL via **Supabase Cloud** + SQLAlchemy 2.0 |
| **Data locations** | Split across `backend/db/`, `backend/data/`, `backend/backend/db/` | Single Supabase database, one connection string |
| **Vendors data** | `backend/db/vendors.json` (571 bytes) | `vendors` table — indexed, relational |
| **Customers data** | `backend/db/customers.json` (1.1KB) | `customers` table with `vendor_id` FK |
| **Messages data** | `backend/db/messages.json` (**147 KB** — will crash under load) | `messages` table — paginatable, indexed by `vendor_id` + `created_at` |
| **Orders data** | `backend/data/sales_orders.json` | `orders` table |
| **Inventory data** | `backend/data/inventory_items.json` | `inventory_items` table with `sku`, `stock_count`, `min_threshold` |
| **Marketing posts** | `backend/db/marketing_posts.json` (**100 KB+** blob) | `marketing_posts` table |
| **Scheduled campaigns** | `backend/db/marketing_scheduled_campaigns.json` | `scheduled_campaigns` table |
| **Support tickets** | `backend/backend/db/support_tickets.json` (wrong nested path) | `support_tickets` table |
| **Facebook accounts** | `backend/db/facebook_accounts.json` | `facebook_accounts` table |
| **Users** | `backend/db/users.json` (single hardcoded dev admin) | `users` table with role enum (`admin`, `vendor`, `staff`, `customer`) |
| **Migrations** | ❌ None — data is lost if files are deleted | ✅ **Alembic** — versioned schema migration history |
| **Fallback for dev** | N/A | Auto-falls back to local `sqlite+aiosqlite:///./dev.db` if `DATABASE_URL` not set |

---

### 3. Controllers Layer

| | OLD (`backend/controllers/`) | NEW (`app/api/endpoints/{feature}/`) |
|---|---|---|
| **Pattern** | Flat folder — all controllers at same level | Feature sub-folders — each domain has its own package |
| **Router definition** | Router + Pydantic request models + business logic all mixed in one file | Router is a thin wrapper — business logic lives in `services/` |
| **`webhook_controller.py`** | 253 lines, includes parsing + DB writes + agent runner call | `api/endpoints/webhook/webhook.py` — parsing only, delegates to `services/` |
| **`marketing_controller.py`** | **18,561 bytes, 473 lines** — massively overloaded | Split: router in `api/routers/marketing_router.py`, logic in `services/marketing_service.py` |
| **`vendors_controller.py`** | 8,854 bytes — mixed Pydantic schemas + routing | Schemas → `schemas/vendor.py`, routing → `api/endpoints/vendors/vendors.py` |
| **`vapi_controller.py`** | Root-level `from ..services.vapi_support_service import dispatch_tool_call` | `api/endpoints/support/support.py` → `services/vapi_service.py` |
| **Auth** | ❌ Does not exist — frontend has fake modal | ✅ `api/endpoints/auth/auth.py` + `auth/functions.py` — JWT login/register |
| **Pydantic models in controllers** | Inline `class AccountCreateRequest(BaseModel)` inside controller files | All in `schemas/` — controllers import from there |

---

### 4. Routers Layer

| | OLD | NEW |
|---|---|---|
| **Approach** | No separate router file — controllers define their own `APIRouter` | `app/api/routers/` folder — one router file per domain |
| **Main aggregation** | `app.py` calls `app.include_router(x)` 8 separate times | `api/routers/main_router.py` — single `router.include_router(x)` chain |
| **Prefix consistency** | Inconsistent: some have `/api` prefix added in `app.py`, some hardcoded inside controller | All prefixes defined in `main_router.py` — one place |

---

### 5. Models & Schemas

| | OLD | NEW |
|---|---|---|
| **`backend/models/`** | Only `fb_model.py` (Pydantic, Facebook-only) and `sales_model.py` | **Eliminated** — replaced by proper separation |
| **ORM models** | ❌ None — no SQLAlchemy models, raw dict reads from JSON | ✅ `app/models/` — full SQLAlchemy 2.0 ORM: `user.py`, `vendor.py`, `customer.py`, `message.py`, `order.py`, `inventory.py`, `marketing.py`, `support.py`, `facebook.py` |
| **Request/Response schemas** | Inline Pydantic classes inside controllers | ✅ `app/schemas/` — dedicated schema per domain |
| **Base model** | None | `app/models/common.py` — `TimestampMixin` with `created_at`, `updated_at` auto fields |
| **UUID primary keys** | String IDs or auto-incremented ints in JSON | UUID v4 primary keys on all tables |

---

### 6. Agents Layer

| | OLD (`backend/my_agents/`) | NEW (`app/agents/`) |
|---|---|---|
| **Folder name** | `my_agents/` — non-standard | `agents/` — clean, standard |
| **LLM client** | `model.py` defines shared client, BUT `finance_agent.py` creates its own duplicate `AsyncOpenAI` instance | `agents/config.py` — single shared client, all agents import from here — **no duplicates** |
| **`runner.py`** | Root level (`backend/runner.py`) — out of place | `agents/runner.py` — correct domain |
| **Tools folder** | `tool/` (singular) | `tools/` (plural — Python standard) |
| **Tool file names** | `finance_tool.py`, `inventory_tool.py` | `finance_tools.py`, `inventory_tools.py` (plural) |
| **`marketing_agent.py`** | Imports model directly, defines output schema inline | Imports from `agents/config.py`, schemas in `schemas/marketing.py` |

---

### 7. Services Layer

| | OLD (`backend/services/`) | NEW (`app/services/`) |
|---|---|---|
| **`marketing_service.py`** | **48,439 bytes, 1,224 lines** — single god file | Split by responsibility: campaign generation, post scheduling, Facebook sync |
| **`whatsapp.py`** | Inside `services/` — client code mixed with service code | Moved to `integrations/meta_whatsapp.py` |
| **DB access in services** | Directly calls `lib/repository.py` JSON store functions | Calls SQLAlchemy repository layer → Supabase |
| **`vapi_support_service.py`** | Defines JSON store, ticket logic, and tool dispatch all in one | `services/vapi_service.py` — business logic only, uses `models/support.py` |
| **`finance_service.py`** | Reads/writes `backend/data/finance_transactions.json` | Reads/writes `orders` table via SQLAlchemy |
| **`inventory_service.py`** | Reads `backend/data/inventory_items.json` | Reads `inventory_items` table |

---

### 8. Integrations Layer (NEW)

| New file | Replaces |
|---|---|
| `app/integrations/meta_whatsapp.py` | `backend/services/whatsapp.py` |
| `app/integrations/meta_facebook.py` | `backend/facebook_manager.py` (root, 40KB monolith) |
| `app/integrations/pexels.py` | Inline `requests.get(pexels_url...)` calls inside `marketing_service.py` |
| `app/integrations/vapi_client.py` | Inline VAPI SDK setup in `vapi_controller.py` |

---

### 9. Core Infrastructure (NEW)

| New file | Replaces / Adds |
|---|---|
| `app/core/settings.py` | 15+ scattered `os.getenv()` calls across the codebase |
| `app/core/database.py` | `backend/lib/json_store.py` + `backend/lib/repository.py` |
| `app/core/dependencies.py` | `app.state.http_client` created ad-hoc in `app.py` |
| `app/core/exceptions.py` | `backend/exceptions.py` (shim) + `backend/src/exceptions.py` + `backend/src/__init__.py` — all merged |

---

### 10. Files Being DELETED (Cleanup)

| File | Reason |
|---|---|
| `backend/main.py` | `print("Hello from server!")` — placeholder, does nothing |
| `backend/exceptions.py` | Shim that just re-exports from `src/exceptions.py` |
| `backend/src/` | Only contains Facebook exceptions — merged into `app/core/exceptions.py` |
| `backend/post_insights.json` | Developer debug test artifact — not application data |
| `backend/backend/` | Accidental nested duplicate folder |
| `backend/config/fb_config.py` | Merged into `app/integrations/meta_facebook.py` + `app/core/settings.py` |
| `backend/lib/` | Replaced by `app/core/database.py` + SQLAlchemy repositories |
| `backend/fb.py` | CLI tool moved to a proper `cli/` directory (optional) |

---

### 11. Tests Layer

| | OLD | NEW |
|---|---|---|
| **Structure** | 21 flat files all in `backend/tests/` | Organized: `tests/unit/` and `tests/integration/` |
| **Scope** | Mix of unit, integration, API, and CLI tests | Clearly separated by type |
| **DB in tests** | Tests use the real JSON files (risky) | Tests use an in-memory SQLite via `pytest` fixtures |

---

## 🔑 Environment Variables — Old vs New `.env.example`

### Old `.env.example`
```env
GEMINI_API_KEY=...
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-2.0-flash
PEXELS_API_KEY=...
```

### New `.env.example`
```env
# ── Application ──────────────────────────────────────────
APP_ENV=development          # development | production
SECRET_KEY=change-me-in-prod
FRONTEND_ORIGIN=http://localhost:3000

# ── Database (Supabase PostgreSQL) ───────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
SUPABASE_URL=https://[REF].supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_key

# ── AI / LLM ─────────────────────────────────────────────
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash

# ── Meta / WhatsApp Cloud API ─────────────────────────────
META_VERIFY_TOKEN=test123
META_GRAPH_VERSION=v17.0
META_GRAPH_BASE=https://graph.facebook.com

# ── Meta / Facebook Graph API ────────────────────────────
FACEBOOK_PAGE_ID=...
FACEBOOK_ACCESS_TOKEN=...

# ── VAPI Voice AI ────────────────────────────────────────
VAPI_API_KEY=...
VAPI_WEBHOOK_SECRET=...
NEXT_PUBLIC_VAPI_PUBLIC_KEY=...
NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID=...

# ── Images ────────────────────────────────────────────────
PEXELS_API_KEY=...

# ── Scheduler ────────────────────────────────────────────
MARKETING_SCHEDULER_ENABLED=true
```

---

## ✅ Summary Scorecard

| Layer | Old Score | New Score | Key Change |
|---|---|---|---|
| Root cleanliness | 🔴 3/10 | ✅ 10/10 | All backend lives inside `app/`, root has only config |
| Database reliability | 🔴 2/10 | ✅ 9/10 | JSON blobs → Supabase PostgreSQL + Alembic |
| Controller structure | 🟡 5/10 | ✅ 9/10 | Flat → Feature-grouped MVC `endpoints/{feature}/` |
| Schema separation | 🔴 3/10 | ✅ 9/10 | Inline Pydantic → dedicated `schemas/` package |
| ORM models | 🔴 0/10 | ✅ 9/10 | No ORM → SQLAlchemy 2.0 mapped models |
| Config management | 🔴 2/10 | ✅ 9/10 | Scattered `os.getenv` → `core/settings.py` |
| Auth system | 🔴 0/10 | ✅ 8/10 | Fake modal → JWT `auth/` endpoint |
| Agent organization | 🟡 5/10 | ✅ 9/10 | `my_agents/` + duplicate clients → clean `agents/` |
| Integration isolation | 🔴 2/10 | ✅ 9/10 | Mixed in services → dedicated `integrations/` |
| Test organization | 🟡 5/10 | ✅ 8/10 | 21 flat files → `unit/` + `integration/` split |

---

## ?? Docker Configuration (Frontend + Backend)

This section defines production-ready Docker images for both services and a `docker-compose.yml` to run the full stack with a single command.

---

### Root Project Structure with Docker Files

```
c:/code/BazaarFlow/
+-- docs/
�   +-- audit_1.md
+-- frontend/
�   +-- Dockerfile              ? Frontend Docker image (Next.js 16 / Node 20)
�   +-- .dockerignore
+-- backend/
�   +-- Dockerfile              ? Backend Docker image (FastAPI / Python 3.12)
�   +-- .dockerignore
+-- docker-compose.yml          ? Starts both services together
+-- .env.example
```

---

### ?? `frontend/Dockerfile`

```dockerfile
# -- Stage 1: Install dependencies ---------------------------------------------
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files first for better layer caching
COPY package.json package-lock.json ./
RUN npm ci --frozen-lockfile

# -- Stage 2: Build the Next.js application ------------------------------------
FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build args injected at build time for NEXT_PUBLIC_ env vars
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ARG NEXT_PUBLIC_VAPI_PUBLIC_KEY=""
ARG NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID=""

ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_VAPI_PUBLIC_KEY=$NEXT_PUBLIC_VAPI_PUBLIC_KEY
ENV NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID=$NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# -- Stage 3: Production runtime -----------------------------------------------
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Only copy the minimal files needed to run
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

> **Note**: Add `output: "standalone"` to `next.config.ts` to enable the standalone build used above.

---

### ?? `frontend/.dockerignore`

```
node_modules
.next
.env*
*.log
.git
.gitignore
README.md
tests/
```

---

### ?? `backend/Dockerfile`

```dockerfile
# -- Stage 1: Build dependencies with uv ---------------------------------------
FROM python:3.12-slim AS builder

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies into /app/.venv (isolated)
RUN uv sync --frozen --no-dev

# -- Stage 2: Production runtime -----------------------------------------------
FROM python:3.12-slim AS runner

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Make sure the venv is used
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy only application source (no dev/test files)
COPY app/ ./app/
COPY mcp_server/ ./mcp_server/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

USER appuser

EXPOSE 8000

# Run Alembic migrations then start Uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
```

> **Note**: Once refactored to the new MVC structure, `app/main.py` is the entrypoint. Adjust `backend/app.py` path accordingly if running from old structure.

---

### ?? `backend/.dockerignore`

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
.env*
.venv
backend/db/*.json
backend/data/*.json
*.log
.git
.gitignore
tests/
docs/
README.md
```

---

### ?? `docker-compose.yml` (Root Level)

```yaml
version: "3.9"

services:

  # -- FastAPI Backend ----------------------------------------------------------
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: bazaarflow_backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - APP_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.0-flash}
      - META_VERIFY_TOKEN=${META_VERIFY_TOKEN}
      - META_GRAPH_VERSION=${META_GRAPH_VERSION:-v17.0}
      - META_GRAPH_BASE=${META_GRAPH_BASE:-https://graph.facebook.com}
      - FACEBOOK_PAGE_ID=${FACEBOOK_PAGE_ID}
      - FACEBOOK_ACCESS_TOKEN=${FACEBOOK_ACCESS_TOKEN}
      - VAPI_API_KEY=${VAPI_API_KEY}
      - VAPI_WEBHOOK_SECRET=${VAPI_WEBHOOK_SECRET}
      - PEXELS_API_KEY=${PEXELS_API_KEY}
      - MARKETING_SCHEDULER_ENABLED=${MARKETING_SCHEDULER_ENABLED:-true}
      - FRONTEND_ORIGIN=http://frontend:3000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - bazaarflow_net

  # -- Next.js Frontend ---------------------------------------------------------
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_BASE_URL: http://localhost:8000
        NEXT_PUBLIC_VAPI_PUBLIC_KEY: ${NEXT_PUBLIC_VAPI_PUBLIC_KEY}
        NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID: ${NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID}
    container_name: bazaarflow_frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
    environment:
      - NODE_ENV=production
    networks:
      - bazaarflow_net

networks:
  bazaarflow_net:
    driver: bridge
```

---

### ?? How to Run

```bash
# 1. Copy env file and fill in your credentials
cp .env.example .env

# 2. Build and start both services
docker compose up --build

# 3. Open in browser
# Frontend ? http://localhost:3000
# Backend API docs ? http://localhost:8000/docs
# Backend health ? http://localhost:8000/health

# 4. Stop all services
docker compose down

# 5. Stop and remove volumes (clean slate)
docker compose down -v
```

---

### ?? Individual Service Commands

```bash
# Rebuild only backend
docker compose build backend && docker compose up backend

# Rebuild only frontend
docker compose build frontend && docker compose up frontend

# View live logs
docker compose logs -f

# View backend logs only
docker compose logs -f backend

# Run Alembic migrations manually inside container
docker compose exec backend alembic upgrade head

# Open backend shell
docker compose exec backend sh
```



---

## ?? Route Parity Verification � Old vs New (43/43 Match)

> All 43 routes from the old `backend/controllers/` are present in the new `app/api/controllers/`.

| Domain | Method | Old Route (full path) | New Route (full path) | Status |
|---|---|---|---|---|
| **VENDORS** | GET | `/api/vendors` | `/api/vendors` | ? |
| | POST | `/api/vendors` | `/api/vendors` | ? |
| | GET | `/api/vendors/{vendor_id}/customers` | `/api/vendors/{vendor_id}/customers` | ? |
| | GET | `/api/vendors/{vendor_id}/customers/{phone}/messages` | `/api/vendors/{vendor_id}/customers/{phone}/messages` | ? |
| | GET | `/api/vendors/{vendor_id}/settings` | `/api/vendors/{vendor_id}/settings` | ? |
| | POST | `/api/vendors/{vendor_id}/settings` | `/api/vendors/{vendor_id}/settings` | ? |
| | POST | `/api/vendors/{vendor_id}/customers/{phone}/messages` | `/api/vendors/{vendor_id}/customers/{phone}/messages` | ? |
| **CHAT** | POST | `/api/chat/sales` | `/api/chat/sales` | ? |
| | POST | `/api/chat/finance` | `/api/chat/finance` | ? |
| | POST | `/api/chat/inventory` | `/api/chat/inventory` | ? |
| | GET | `/api/health/chat` | `/api/health/chat` | ? |
| **SALES** | POST | `/api/sales` | `/api/sales` | ? |
| | GET | `/api/sales` | `/api/sales` | ? |
| **INVENTORY** | GET | `/api/inventory` | `/api/inventory` | ? |
| | GET | `/api/inventory/{sku}` | `/api/inventory/{sku}` | ? |
| | POST | `/api/inventory` | `/api/inventory` | ? |
| | PUT | `/api/inventory/{sku}` | `/api/inventory/{sku}` | ? |
| | PATCH | `/api/inventory/{sku}/add-stock` | `/api/inventory/{sku}/add-stock` | ? |
| | DELETE | `/api/inventory/{sku}` | `/api/inventory/{sku}` | ? |
| **MARKETING** | GET | `/api/marketing/accounts` | `/api/marketing/accounts` | ? |
| | POST | `/api/marketing/accounts` | `/api/marketing/accounts` | ? |
| | DELETE | `/api/marketing/accounts/{id}` | `/api/marketing/accounts/{id}` | ? |
| | PUT | `/api/marketing/accounts/{id}/schedule` | `/api/marketing/accounts/{id}/schedule` | ? |
| | GET | `/api/marketing/accounts/{id}/schedule` | `/api/marketing/accounts/{id}/schedule` | ? |
| | POST | `/api/marketing/accounts/{id}/campaign` | `/api/marketing/accounts/{id}/campaign` | ? |
| | POST | `/api/marketing/accounts/{id}/campaign/scheduled` | `/api/marketing/accounts/{id}/campaign/scheduled` | ? |
| | POST | `/api/marketing/accounts/{id}/scheduled/preview` | `/api/marketing/accounts/{id}/scheduled/preview` | ? |
| | POST | `/api/marketing/accounts/{id}/scheduled` | `/api/marketing/accounts/{id}/scheduled` | ? |
| | GET | `/api/marketing/accounts/{id}/posts` | `/api/marketing/accounts/{id}/posts` | ? |
| | GET | `/api/marketing/accounts/{id}/scheduled/activity` | `/api/marketing/accounts/{id}/scheduled/activity` | ? |
| | POST | `/api/marketing/accounts/{id}/posts/{post_id}/insights` | `/api/marketing/accounts/{id}/posts/{post_id}/insights` | ? |
| | PATCH | `/api/marketing/accounts/{id}/scheduled/posts/{pid}` | `/api/marketing/accounts/{id}/scheduled/posts/{pid}` | ? |
| | PATCH | `/api/marketing/accounts/{id}/scheduled/campaigns/{cid}` | `/api/marketing/accounts/{id}/scheduled/campaigns/{cid}` | ? |
| | DELETE | `/api/marketing/accounts/{id}/scheduled/posts/{pid}` | `/api/marketing/accounts/{id}/scheduled/posts/{pid}` | ? |
| | DELETE | `/api/marketing/accounts/{id}/scheduled/campaigns/{cid}` | `/api/marketing/accounts/{id}/scheduled/campaigns/{cid}` | ? |
| | GET | `/api/marketing/accounts/{id}/posts/{post_id}/comments` | `/api/marketing/accounts/{id}/posts/{post_id}/comments` | ? |
| | DELETE | `/api/marketing/accounts/{id}/posts/{post_id}` | `/api/marketing/accounts/{id}/posts/{post_id}` | ? |
| | POST | `/api/marketing/accounts/{id}/posts/{post_id}/comments/{cid}/reply` | `/api/marketing/accounts/{id}/posts/{post_id}/comments/{cid}/reply` | ? |
| **WEBHOOK** | GET | `/webhook/test` | `/webhook/test` | ? |
| | GET | `/webhook` | `/webhook` | ? |
| | POST | `/webhook` | `/webhook` | ? |
| **SUPPORT** | POST | `/vapi/webhook` | `/vapi/webhook` | ? |
| **LOGS** | GET | `/api/logs` | `/api/logs` | ? |
| **AUTH** (new) | POST | � | `/auth/login` | ?? |
| | POST | � | `/auth/register` | ?? |

**Total old routes: 43 | Total new routes: 45 (43 + 2 new auth routes)**

