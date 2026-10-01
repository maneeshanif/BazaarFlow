# Library Docs

Project-specific usage patterns for every third-party library in this project. This file covers how *we* use each library in BazaarFlow — rules, patterns and constraints specific to this project. It is not a substitute for the official docs.

---

## Before Using Any Library

1. **Check `AGENTS.md`** at the project root for installed skills.
2. **Fetch current API documentation** (Context7 MCP or the official docs) — library APIs change and training data goes stale. This is required, not optional, for any library question.
3. **Read this file** for project-specific patterns that override general library knowledge.

Order of authority:

```
Current official docs -> Skills via AGENTS.md -> This file (project rules) -> General knowledge
```

---

## Adding a library

When a task adopts a new library, add a section here **in the same PR** using this shape:

```
## <Library> (<package name>, <pinned version>)

Where it is configured: <file>
Project rules:
- <the pattern we always use>
- <the thing we never do, and why>
Gotchas found in this project:
- <symptom> -> <cause> -> <fix>
```

## FastAPI (fastapi[standard] >= 0.115)

Where it is configured: `app/main.py`, `app/api/routers/`
Project rules:
- Controllers stay thin and call `app/services/`; no business logic in routers
- Every route declares its authorization dependency (`require_role` or explicit `public`)
Gotchas found in this project:
- Webhook routes must verify provider signatures before reading the body into a model

## SQLAlchemy 2 async + asyncpg (sqlalchemy >= 2.0, asyncpg >= 0.29)

Where it is configured: `app/core/database.py`
Project rules:
- Sessions are tenant-scoped: open a transaction and run `SELECT set_config('app.tenant_id', :tid, true)` first
- Never create a bare session in a service; use the tenant-scoped dependency or `system_session()`
Gotchas found in this project:
- Behind the Supabase transaction pooler (port 6543), prepared statements fail -> asyncpg statement cache -> set `statement_cache_size=0` and `prepared_statement_cache_size=0` in `connect_args`

## Alembic (alembic >= 1.13, async env)

Where it is configured: `alembic/env.py`, `alembic.ini`
Project rules:
- Migrations run with the `migrator` role over the direct connection (port 5432), never the pooler
- RLS policies and `REVOKE` statements live inside migrations
- `alembic check` must be clean (enforced by the `api-db` lane)

## Supabase (Postgres + Storage only)

Where it is configured: `DATABASE_URL*`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (see PRD §3.8)
Project rules:
- No Supabase Auth, Realtime, Edge Functions or browser client; the API is the only client
- Data API roles (`anon`, `authenticated`) have no grants on business tables
Gotchas found in this project:
- Free projects pause after inactivity -> upgrade the demo project to Pro before launch

## OpenAI Agents SDK (openai-agents >= 0.4.1)

Where it is configured: `app/agents/config.py` (lazy client init, provider-configurable)
Project rules:
- Tools live in `app/agents/tools/` and take no tenant or user arguments; context carries them
- Max 8 tool calls per run; spend cap per tenant (PRD §36.18)
Gotchas found in this project:
- Import fails when `GEMINI_API_KEY` is unset -> client created lazily in `config.py`

## Next.js 16 / React 19 (frontend)

Where it is configured: `frontend/next.config.ts` (standalone output, Sentry wrapper)
Project rules:
- Server Components by default; `"use client"` only where state or browser APIs are needed
- All money and date formatting through one `lib/format` module
Gotchas found in this project:
- Docker image relies on `output: "standalone"`; do not remove it

## WhatsApp via adapters (pywa, Twilio, Meta Cloud API)

Where it is configured: `app/integrations/` (adapter interface) and `app/services/whatsapp.py`
Project rules:
- Services call the adapter interface only; provider choice is per-tenant configuration
- Twilio sandbox is demo-only; production uses Meta Embedded Signup or a BSP (PRD I-001, I-002)

