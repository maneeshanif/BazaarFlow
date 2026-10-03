# ADR 0001 — Stack decision

Status: proposed (awaiting owner sign-off, build-plan task 00)
Date: 2026-10-02

## Context
BazaarFlow v1 is a single-tenant FastAPI + Next.js application with JSON-file stores and global credentials. v2 must isolate tenants, use Supabase Postgres, and launch as a public demo within two days (PRD §0.3 A-001). Full detail: `docs/prd/PRD.md` §3.

## Decision
- Frontend: Next.js 16, React 19, Tailwind, shadcn/ui
- Backend: FastAPI, SQLAlchemy 2 async, Alembic (async), Pydantic v2
- Database: PostgreSQL on Supabase (pooler for runtime, direct connection for migrations); SQLite for unit tests only
- Tenancy: shared schema, `tenant_id` on every business table, Postgres RLS driven by `app.tenant_id`
- Auth: FastAPI-issued JWT with `tenant_id` and `role`; Supabase Auth not used
- Agents: OpenAI Agents SDK; inside the API process for now, moving to a separate agent service without database credentials (ADR 0003)
- Channels: Twilio sandbox for demo, Meta Embedded Signup for production, VAPI for voice, all behind an adapter interface
- Hosting: Docker Compose locally; API on FastAPI Cloud, web on Vercel (ADR 0003)

## Alternatives rejected
Neon (owner chose Supabase), Supabase Auth (backend already owns auth), schema-per-tenant (operational cost), Redis/Celery (no measured need), LiveKit/Pipecat (VAPI is enough for launch), Composio MCP for WhatsApp (does not remove Meta onboarding).

## Consequences
RLS and architecture tests are mandatory merge gates. The transaction pooler requires disabling asyncpg prepared-statement caches. The Tailwind 3 -> 4 question (see `context/ui-tokens.md`) must be settled in the UI foundation task.
