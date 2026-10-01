---
project: "BazaarFlow"
slug: "bazaarflow"
version: "0.1.2"
status: draft
profile: production
date: "2026-10-01"
owners: ["Anees (maneeshanif)"]
stack:
  frontend: "Next.js 16 + React 19 + Tailwind + shadcn/ui"
  backend: "FastAPI (Python 3.12+) + SQLAlchemy 2 async"
  database: "PostgreSQL (Supabase), SQLite for local tests only"
  migrations: "Alembic (async)"
  api_contract: "openapi"
  agents: "OpenAI Agents SDK (Gemini-compatible model config)"
  infra: "Docker Compose, GitHub Actions"
features:
  - tenancy
  - audit
  - money
  - ui
  - ai-agents
  - api-contract
  - database
layout:
  api: .
  web: frontend
phases: 5
packs: [web-app, backend-api, integrations, agents, voice-agents]
---

# BazaarFlow — Product Requirements & Technical Specification

> Reverse-engineered from the existing codebase (see `reverse-findings.md`) and confirmed with the owner in discovery. Statements marked *(observed)* came from code; statements marked *(confirmed)* came from the owner.

## 0. Document Control

### 0.1 Purpose and audience
This PRD is the source of truth for scope, architecture and acceptance of BazaarFlow. Readers: the owner/developer, AI coding agents (via `AGENTS.md` and `context/`), and any future contributor. Changes to scope go through §25.

### 0.2 Revision history
| Version | Date | Author | Summary of change | Sections touched |
| --- | --- | --- | --- | --- |
| 0.1.0 | 2026-10-01 | Anees + Claude | Initial PRD: reverse mode from existing v1 codebase plus discovery answers | all |
| 0.1.1 | 2026-10-01 | Anees + Claude | Added positioning, channel-adapter rule, voice-note orders, automation recipes, 2-day launch plan | 1, 3.7, 10, 22, 26 |
| 0.1.2 | 2026-10-01 | Anees + Claude | Added §3.8 Supabase platform design (connections, roles, RLS/Data API lockdown, Storage, backups), constraints 12-13, decisions, risks RK-07 to RK-09 | 3, 22, App. A-C |

### 0.3 Assumptions ledger
| ID | Assumption | Basis | Owner to confirm |
| --- | --- | --- | --- |
| A-001 | "Launch" within 2 days means a public, free demo on a production-grade foundation (multi-tenant schema, auth, roles, audit), not paying customers. | Owner chose profile *production* and *free demo now, pricing later*; two-day deadline stated. | Owner |
| A-002 | Row-level tenancy (shared schema, `tenant_id` on every business table) is sufficient for the first 1,000 tenants. | Standard SaaS pattern; Supabase Postgres supports it. | Owner |
| A-003 | The FastAPI backend remains the only service that touches the database; Supabase Auth is not used. Tenant isolation is enforced by Postgres RLS using a per-request session variable, with the API role lacking `BYPASSRLS`. | Existing JWT/bcrypt auth in `app/core/security.py` *(observed)*. | Owner |
| A-004 | WhatsApp channel for the demo is the Twilio WhatsApp sandbox; production uses Meta Embedded Signup via a Tech Provider or a BSP. | Discovery discussion. | Owner |
| A-005 | VAPI remains the voice provider for launch; LiveKit/Pipecat deferred. | Time constraint; webhook already exists *(observed)*. | Owner |
| A-006 | Primary market is small retailers in Pakistan; timezone `Asia/Karachi`, currency PKR, Urdu/RTL planned but not launch-blocking. | Owner *(confirmed)*; timezone in code *(observed)*. | Owner |
| A-007 | The old `backend/` folder is legacy, untracked, and out of scope; the endpoint counts in the findings file double-count it. | `progress.md` *(observed)*. | Owner |
| A-008 | Team is the owner working with AI coding agents. | Owner *(confirmed)*. | Owner |

### 0.4 Open questions
| ID | Question | Blocks (section/phase) | Owner | Status |
| --- | --- | --- | --- | --- |
| Q-001 | Which Pakistani data-protection and tax rules (FBR POS integration, PECA, draft Personal Data Protection law) apply at paid launch? | §34, phase 4 | Owner | open |
| Q-002 | Meta Tech Provider application: who holds the verified Meta Business account, and what is the lead time? | I-002, phase 2 | Owner | open |
| Q-003 | Which LLM provider and model is the production default (Gemini vs OpenAI), and what per-tenant monthly AI spend cap applies? | §36.18, phase 1 | Owner | open |
| Q-004 | Is Urdu (RTL) UI required at launch or phase 3? | §16, phase 3 | Owner | open |
| Q-005 | Do retailers need GST/sales-tax invoices with FBR codes at launch? | §34, phase 4 | Owner | open |
| Q-006 | Pricing plans and limits (messages, AI calls, voice minutes) once the demo ends. | §26, phase 4 | Owner | open |

### 0.5 Glossary
| Term | Meaning in this product |
| --- | --- |
| Tenant | One retail business (a shop or chain) using BazaarFlow; the isolation boundary for all data. |
| Membership | A user's role inside one tenant; a user may belong to several tenants. |
| Owner / Manager / Staff | Tenant-scoped roles defined in §14.2. |
| Platform admin | BazaarFlow operator role, cross-tenant, audited. |
| Agent | An LLM-driven worker with a fixed tool set (sales, inventory, finance, marketing, support, orchestrator). |
| Approval | A human confirmation required before an agent action with side effects executes. |
| Channel | A messaging surface: WhatsApp, Facebook, Instagram, voice, web chat. |
| Udhaar | Customer credit ledger: goods sold now, paid later. |
| BSP | Business Solution Provider for the WhatsApp Business Platform (e.g. Twilio, 360dialog). |

---

## 1. Executive Summary
BazaarFlow is an AI back-office for small retailers. A shopkeeper runs inventory, sales, vendor and customer finance, social media marketing and customer support by chatting (text or voice) with specialized agents over WhatsApp and a web dashboard, instead of filling forms in an ERP. It automates daily retail tasks: recording sales, tracking stock, scheduling Facebook campaigns and replying to comments, answering customer messages, and handling support calls through a voice agent.

The v1 application (built eight months ago) proves the core loop: FastAPI services, four OpenAI-Agents-SDK agents, Facebook scheduler, WhatsApp webhook and a VAPI support line *(observed)*. It is single-tenant, stores part of its data in JSON files, reads credentials from global environment variables, and has a generic UI. This PRD defines the v2 product: multi-tenant on Supabase Postgres, role-based, audited, with per-tenant integrations, a Twilio-sandbox WhatsApp demo path, an approval-driven agent layer and a redesigned application shell.

Delivery profile is **production** (real tenants must be isolated and auditable), with launch scoped as a free public demo. **Positioning:** BazaarFlow is a conversational AI back-office for small retailers. It covers the ERP essentials (inventory, sales, customer credit, vendors, basic finance) but is not a full ERP: no general ledger, payroll or multi-warehouse. The shopkeeper operates it by chat and voice instead of forms. What makes it different from general personal agents (OpenClaw, Hermes) is that it is vertical: retail data model, retail agents, guided connection of WhatsApp/Facebook for non-technical owners, and an approval center that makes AI actions safe.

## 2. Product Objectives
- Isolate every tenant's data so that no API call, agent tool or webhook can read or write another tenant's rows.
- Let an owner onboard a shop (profile, products, WhatsApp and Facebook connection) in under 15 minutes without developer knowledge.
- Let a shopkeeper record a sale, check stock and see profit by chat message in under 10 seconds p95.
- Maintain inventory with stock movements so every quantity change is traceable to a sale, purchase or adjustment.
- Track customer credit (udhaar) and vendor payables with a ledger that reconciles to orders and payments.
- Schedule and publish Facebook posts and campaigns, and reply to comments, with owner approval where configured.
- Answer inbound WhatsApp customer messages with an agent that can quote stock and take orders, with human takeover per conversation.
- Answer inbound support calls through a voice agent and store transcripts and outcomes.
- Require approval for every agent action that changes money, stock or external publishing above tenant-set limits.
- Record an audit entry for every state-changing action by a user or agent.
- Provide a daily briefing to the owner on WhatsApp.
- Ship an application shell, dashboard, inbox and approvals feed that rates at least 8/10 in owner review (current v1 UI self-rated 4/10).

### 2.1 Success metrics
| Metric | Baseline | Target | How measured |
| --- | --- | --- | --- |
| Cross-tenant leak tests passing | none exist | 100% of endpoints and agent tools covered | Architecture tests in CI (§19) |
| Onboarding time (signup to first WhatsApp reply) | not measurable | ≤ 15 min median in demo sessions | Timed UAT with 5 retailers |
| Chat command latency (sale recorded) | unmeasured | p95 ≤ 10 s end to end | Request logs + synthetic test |
| Agent actions with audit row | unknown | 100% | Audit coverage test |
| Demo conversions (demo tenants created) | 0 | 20 tenants in first 2 weeks | `tenants` table count |
| UI owner rating | 4/10 | ≥ 8/10 | Owner review against §32 |
| Crash-free requests | unknown | ≥ 99% | Sentry + request logs |

### 2.2 Out of scope
- Paid billing, plans, invoicing of tenants (phase 4, after demo feedback).
- Building a custom voice stack (LiveKit/Pipecat); VAPI is used.
- A full accounting/GL, payroll, multi-warehouse and purchase-approval ERP modules.
- Native mobile apps (responsive web only).
- Marketplace connectors (Daraz, Shopify) before phase 4.
- Visual workflow builder (React Flow) before phase 4; launch ships pre-built automation recipes.
- Fine-tuning or hosting our own models.

## 3. Technology & Architecture

### 3.1 Stack decision record
| Layer | Required technology / standard | Why this choice | Considered and rejected |
| --- | --- | --- | --- |
| UI | Next.js 16 (App Router), React 19, Tailwind, shadcn/ui | Already in repo *(observed)*; fast to compose a dashboard shell | Vite SPA (no SSR needed but loses existing work) |
| Backend | FastAPI, Python 3.12+ | Existing 45-route MVC app *(observed)*; async fits webhooks and streaming | Django (rewrite cost), Node (rewrite cost) |
| Business logic | `app/services/` called by controllers and agent tools | One path for UI, webhooks and agents | Logic inside controllers |
| ORM / data access | SQLAlchemy 2 async via `app/crud/` and repositories | Present and typed *(observed)* | Raw SQL, Supabase client from the browser |
| Database | PostgreSQL on Supabase; SQLite only for unit tests | Owner decision; managed, RLS, backups | Neon (rejected by owner), self-hosted Postgres |
| Migrations | Alembic async | Present *(observed)* | Supabase dashboard edits |
| API | REST, OpenAPI, versioned `/api/v1` | Router aggregation exists *(observed)* | GraphQL |
| Authentication | FastAPI-issued JWT (bcrypt) with `tenant_id` and `role` claims | Existing *(observed)*; no vendor coupling | Supabase Auth, Clerk |
| Authorization | Role dependency per route + Postgres RLS on `tenant_id` | Defense in depth | App-level filtering only |
| Background jobs | APScheduler with SQLAlchemy job store, in the API container, for phase 1; ARQ/Celery deferred | Scheduler exists *(observed)*; no Redis yet | Celery + Redis now |
| Cache / queue | None (Postgres only) | Not needed at demo scale | Redis |
| Search | Postgres `ILIKE` / `pg_trgm` | Catalog is small | Elasticsearch |
| File storage | Supabase Storage (product and post media) | Same vendor, signed URLs | S3/R2 (alternative later) |
| AI / agents | OpenAI Agents SDK; model provider configurable (Gemini default in v1) | Present *(observed)* | LangGraph, custom loop |
| Observability | Sentry (web + API), structured JSON logs, request IDs | Sentry wiring started *(observed)* | Datadog |
| CI/CD | GitHub Actions running `scripts/verify.sh` | Generated by bootstrap | Manual |
| Hosting / deployment | Docker Compose locally; one container host for API (e.g. Fly.io/Railway), Vercel for web | Low cost, fast | Kubernetes |
| Containers | `backend.Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` | Present *(observed)* | n/a |
| Testing | pytest (+ httpx), Vitest/Playwright for web | pytest present, 55 test files *(observed)* | n/a |

### 3.2 Considered and deferred
| Technology | Why not now | Trigger to adopt |
| --- | --- | --- |
| Redis | No cache or queue need at demo scale | p95 API latency > 500 ms from repeated reads, or > 50 background jobs/min |
| Celery / ARQ workers | APScheduler in-process is enough | Scheduled jobs > 1,000/day or a job blocks a request worker |
| LiveKit / Pipecat | VAPI covers one voice agent per tenant | VAPI cost per call exceeds the pipeline's hosting cost for 3 consecutive months, or custom audio pipeline required |
| React Flow automation builder | Recipes cover launch needs | 10 tenants request custom automations not covered by recipes |
| Elasticsearch / vector DB | Catalog under 10k SKUs per tenant | Search p95 > 300 ms or semantic product match required |
| Kubernetes / microservices | Single deployable is simpler | More than one team or independent scaling needs |
| Supabase Realtime | SSE already exists *(observed)* | Inbox needs multi-user live presence |
| Stripe / local payment gateway billing | Free demo | Phase 4 pricing decision (Q-006) |

### 3.3 Architecture overview
```
Owner/Staff browser --> Next.js web --HTTPS/JWT--> FastAPI API (sole owner of business logic)
Customer WhatsApp --> Twilio/Meta --> /webhook ------^        |
Customer phone ----> VAPI --> /vapi/webhook ----------^       v
Facebook Graph <---- scheduler/integration layer <-- services --> Supabase Postgres (RLS)
                         ^                               ^
                         +-- Agents (call services via tools; no DB credentials, no raw SQL)
Supabase Storage <-- signed URLs from the API
```
Deployment units: web, API (includes scheduler), Supabase (database + storage). Agents run inside the API process as tool-calling clients of the service layer.

### 3.4 Repository layout
```
BazaarFlow/
├── app/                    # FastAPI backend (MVC)
│   ├── api/controllers/    # per-domain controllers
│   ├── api/routers/        # main_router.py, v1/
│   ├── agents/ + tools/    # sales, finance, inventory, marketing (+ orchestrator, support)
│   ├── services/           # business logic
│   ├── crud/ repositories/ # data access
│   ├── models/ schemas/    # SQLAlchemy + Pydantic v2
│   ├── integrations/       # facebook, whatsapp/twilio, vapi (channel adapters)
│   ├── core/               # settings, security, database, tenancy
│   ├── middleware/ prompts/ mcp_server/ cli/ utils/
├── alembic/                # migrations
├── frontend/               # Next.js app
├── tests/                  # unit/ + integration/ + architecture/
├── docs/                   # prd/, adr/, audit_1.md
├── context/                # generated by bootstrap
└── docker-compose.yml, backend.Dockerfile, pyproject.toml
```

### 3.5 Multi-tenancy and scoping
Model: shared database, shared schema, `tenant_id UUID NOT NULL` on every business table, foreign-keyed to `tenants`. A `memberships(user_id, tenant_id, role)` table gives users one role per tenant.
- The JWT carries `sub`, `tenant_id`, `role`. A `get_current_tenant` dependency resolves it; switching tenant issues a new token.
- Every request opens a transaction and runs `SELECT set_config('app.tenant_id', :tid, true)`. RLS policies on every business table require `tenant_id = current_setting('app.tenant_id')::uuid`. The API connects with a role lacking `BYPASSRLS`.
- CRUD functions accept a tenant-scoped session; none accept a bare session. A deliberate cross-tenant operation (platform admin, scheduler sweep) uses a named `system_session()` helper that writes an audit row and is flagged in code review.
- Webhooks resolve the tenant from the channel identity (`tenant_integrations.external_id`: WhatsApp phone number ID, Facebook page ID, VAPI assistant ID) before any other processing.
- Agent runs receive a tenant context object; tools read the tenant from it, never from model-supplied arguments.

### 3.6 Environments and deployment models
Local (Docker Compose + SQLite or local Postgres), CI (ephemeral Postgres), staging (Supabase branch/project), production (Supabase project). Configuration via Pydantic `Settings` from environment variables; `.env.example` lists keys with empty values; secrets live in the host's secret store. Per-tenant credentials are stored encrypted in `tenant_integrations` (envelope encryption with an app key), never in env vars or logs.

### 3.7 Architectural constraints (non-negotiable)
1. Every business table has `tenant_id` and an RLS policy; a test fails if a table lacks either.
2. The API is the only owner of business logic and data access; the browser never talks to the database and agents never hold database credentials.
3. Every route has an explicit authorization decision (`require_role(...)` or `public`); a test enumerates routes and fails on undecided ones.
4. Agent tools take tenant and user from the server-side context, never from model output.
5. Agent actions that write money, stock or publish externally are gated by approval rules and write `agent_actions` rows.
6. Schema changes ship only as Alembic migrations in the same PR; CI fails on model/migration drift.
7. No secrets in source control; integration tokens are encrypted at rest and masked in logs.
8. Money uses `NUMERIC(14,2)` in PKR minor-unit-safe decimals; no floats.
9. All external calls (Meta, Twilio, VAPI, LLM) go through adapters with timeouts, retries and idempotency keys.
10. The UI uses design tokens and registry components only; no hard-coded colors.
11. Messaging channels sit behind one adapter interface (`connect`, `send`, `receive`, `verify_webhook`) with Twilio, Meta Cloud API, Facebook and VAPI as implementations; agents and services never import a provider SDK directly, so providers can be swapped without touching business logic.
12. Supabase Data API and the `anon`/`authenticated` roles have no access to business tables; business tables use `ENABLE` + `FORCE` row-level security; the API runtime role is `NOBYPASSRLS`.
13. Storage buckets are private; object paths start with `tenant_id`; access is by signed URL issued by the API.

### 3.8 Supabase platform design
Supabase provides managed Postgres, Storage and backups. BazaarFlow does **not** use Supabase Auth, Realtime, Edge Functions or the browser client library; the FastAPI API is the only Supabase client.

**Projects and regions.** Three separate projects: `bazaarflow-dev`, `bazaarflow-staging`, `bazaarflow-prod`. Region is the closest available to Pakistan (Singapore or Mumbai), chosen once because it cannot be changed later. Free tier may be used for dev and the demo; it pauses after inactivity, so the demo project is upgraded to Pro before the LinkedIn launch (RK-07).

**Connections.**
| Use | Connection | Notes |
| --- | --- | --- |
| API runtime | Pooler, transaction mode (port 6543) | SQLAlchemy asyncpg with `statement_cache_size=0` and `prepared_statement_cache_size=0` (transaction pooling does not support prepared statements); small pool, `pool_pre_ping=True` |
| Alembic migrations | Direct connection (port 5432) as the `migrator` role | DDL and RLS policies need a session connection |
| Read-only reports | Pooler as `report_ro` role | Backs the existing `database_ro` engine *(observed)* |
| Local tests | SQLite in-memory or a local Postgres container | RLS tests must run on Postgres, not SQLite |

**Database roles.**
| Role | Purpose | Rights |
| --- | --- | --- |
| `migrator` | Alembic only; owns tables | DDL; used from CI/dev machine, never at runtime |
| `app_user` | API runtime | DML on business tables; `NOBYPASSRLS`; no DDL |
| `report_ro` | Reporting | `SELECT` only, RLS applies |
| `service_role` / `anon` / `authenticated` (Supabase defaults) | Supabase Data API | **No grants** on business tables (see lockdown) |

**Data API lockdown.** Supabase exposes tables through PostgREST using the `anon` key. Every business table shall have `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`, and the migration shall `REVOKE ALL` on all tables, sequences and functions in `public` from `anon` and `authenticated`. The Data API is disabled in project settings where possible. The `anon` and `service_role` keys are not used by the web app and are never placed in the browser bundle, in `NEXT_PUBLIC_*` variables, or in agent/developer environments (production `service_role` lives only in the API host's secret store, and only if Storage admin calls need it).

**Tenant isolation SQL pattern (in migrations).**
```sql
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE products FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON products
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
-- per request, inside the transaction:
SELECT set_config('app.tenant_id', :tenant_id, true);   -- transaction-local, safe with pooling
```
Role-sensitive writes (e.g. delete, reverse) add a second policy keyed on `current_setting('app.role', true)`. If `app.tenant_id` is unset, policies match no rows (fail closed). Platform-admin and scheduler sweeps use a dedicated `system_session()` that sets `app.tenant_id` per tenant in a loop, not a bypass role.

**Storage.** Private buckets only: `product-images`, `post-media`, `voice-recordings`, `exports`. Object path is `{tenant_id}/{entity}/{uuid}.{ext}`; the API validates type (jpg, png, webp, mp3, csv, pdf) and size (images ≤ 5 MB, audio ≤ 25 MB), uploads on the user's behalf, and returns short-lived signed URLs (≤ 1 h). Storage policies deny direct client access; the API enforces tenant prefix. Orphaned objects are removed by a weekly job.

**Extensions.** `pgcrypto` (UUIDs, token encryption helpers), `pg_trgm` (product search), `pg_stat_statements` (query review). `pgvector` is deferred until semantic product matching is needed (§3.2).

**Backups and recovery.** Daily backups at launch; Point-in-Time Recovery enabled on Pro before paid tenants arrive (§18). Monthly restore test into a scratch project. Schema is reproducible from Alembic alone; the demo seed can rebuild a dev project in under 5 minutes.

**Branching and migrations.** Schema changes are tried on a staging project (or Supabase branch when available) before production; migrations are applied from CI with the `migrator` role, never from the Supabase dashboard SQL editor in production (drift is blocked by `alembic check`).

**Monitoring.** Supabase advisors (security and performance) are reviewed before each release; slow queries from `pg_stat_statements` are reviewed monthly; connection count and disk usage alerts are set at 80%.

**Environment variables (names only).** `DATABASE_URL` (pooler, `app_user`), `DATABASE_URL_MIGRATIONS` (direct, `migrator`), `DATABASE_URL_RO` (`report_ro`), `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (API host only, Storage admin), `INTEGRATION_ENCRYPTION_KEY`.

**Development tooling.** Supabase MCP or dashboard access is allowed for the dev project only; AI agents never receive staging or production credentials (§15).

## 4. Application Navigation / Main Menu
Left sidebar (collapsible), top bar with command palette (Ctrl+K), notifications bell (approvals), tenant switcher, user menu. Bottom tab bar on phones (Home, Inbox, Sales, Stock, More).

| Group | Items | Owner | Manager | Staff | Platform admin |
| --- | --- | --- | --- | --- | --- |
| Overview | Home dashboard, Agent activity, Approvals | yes | yes | Home only | tenants list |
| Inbox | Conversations (WhatsApp, Facebook, web), Support calls | yes | yes | yes | no |
| Sales | Sales chat, New sale, Orders, Customers (udhaar) | yes | yes | New sale, Orders | no |
| Inventory | Products, Stock movements, Vendors | yes | yes | view stock | no |
| Finance | Finance overview, Ledger, Reports | yes | view | hidden | no |
| Marketing | Studio, Schedule, Activity, Insights, Credentials | yes | yes | hidden | no |
| Voice | Call log, Voice agent settings | yes | view | hidden | no |
| Automations | Recipes, Run history | yes | yes | hidden | no |
| Settings | Shop profile, Team, Integrations, Billing (later) | yes | Team view | hidden | all tenants |

Unauthorized items are hidden, never merely disabled; the API still returns 403.

## 5. Form & Screen Specification

### 5.1 Mandated form layout
Every screen follows: **Header** (title + status chip + primary action) → **Filters / master fields** → **Detail grid or content** → **Totals / summary** → **Action bar** → **Audit & status panel** (who changed what, last agent action). Mobile collapses filters into a sheet and the action bar into a sticky bottom bar.

### 5.2 Form register
| ID | Form / screen | Module | Type | Roles | Priority | Phase |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Sign in | Auth | master | public | P0 | 1 |
| F-002 | Create account and shop | Auth | master | public | P0 | 1 |
| F-003 | Onboarding wizard | Onboarding | transaction | owner | P0 | 2 |
| F-004 | Home dashboard | Overview | report | owner, manager, staff | P0 | 1 |
| F-005 | Unified inbox | Inbox | transaction | owner, manager, staff | P0 | 2 |
| F-006 | Sales chat (agent) | Sales | transaction | owner, manager, staff | P0 | 1 |
| F-007 | New sale | Sales | transaction | owner, manager, staff | P0 | 1 |
| F-008 | Orders list and detail | Sales | list | owner, manager, staff | P0 | 1 |
| F-009 | Customers and udhaar ledger | Sales | master | owner, manager | P0 | 1 |
| F-010 | Products and stock | Inventory | master | owner, manager (staff view) | P0 | 1 |
| F-011 | Stock movements | Inventory | list | owner, manager | P1 | 2 |
| F-012 | Vendors and payables | Inventory | master | owner, manager | P1 | 2 |
| F-013 | Finance overview and ledger | Finance | report | owner (manager view) | P1 | 2 |
| F-014 | Marketing studio | Marketing | transaction | owner, manager | P0 | 1 |
| F-015 | Marketing schedule | Marketing | settings | owner, manager | P1 | 2 |
| F-016 | Marketing activity | Marketing | list | owner, manager | P1 | 2 |
| F-017 | Marketing insights | Marketing | report | owner, manager | P2 | 3 |
| F-018 | Integrations (WhatsApp, Facebook, VAPI) | Settings | settings | owner | P0 | 2 |
| F-019 | Team and roles | Settings | master | owner | P0 | 1 |
| F-020 | Shop profile and settings | Settings | settings | owner | P1 | 2 |
| F-021 | Approvals center | Overview | transaction | owner, manager | P0 | 1 |
| F-022 | Agent activity log | Overview | list | owner, manager | P0 | 1 |
| F-023 | Voice calls and agent settings | Voice | list/settings | owner (manager view) | P1 | 3 |
| F-024 | Automation recipes | Automations | settings | owner, manager | P1 | 3 |
| F-025 | Platform admin: tenants | Platform | master | platform admin | P1 | 2 |
| F-026 | Public landing page | Public | page | public | P0 | 1 |
| F-027 | Public live demo | Public | page | public | P1 | 1 |
| F-028 | System logs | Platform | list | platform admin | P2 | 3 |

### 5.3 Field-level specifications

#### F-001 Sign in
| Field | Type | Required | Validation / rule | Notes |
| --- | --- | --- | --- | --- |
| email | email | yes | RFC format, ≤ 254 chars | case-insensitive |
| password | password | yes | ≥ 8 chars | never logged; 5 failures → 15 min lockout |
| tenant | select | when user has > 1 membership | must be a tenant of the user | sets `tenant_id` in token |

#### F-002 Create account and shop
| Field | Type | Required | Validation / rule | Notes |
| --- | --- | --- | --- | --- |
| full_name | text | yes | 2-80 chars | |
| email | email | yes | unique | |
| password | password | yes | ≥ 8 chars, not in common-password list | bcrypt |
| shop_name | text | yes | 2-80 chars | creates `tenants.name` and slug |
| phone | phone | yes | E.164, default +92 | used for owner briefings |
| city | text | no | ≤ 60 chars | |
| accept_terms | checkbox | yes | must be true | |

#### F-007 New sale
| Field | Type | Required | Validation / rule | Notes |
| --- | --- | --- | --- | --- |
| customer_id | lookup | no | belongs to tenant; empty = walk-in | create inline |
| items[].product_id | lookup | yes | ≥ 1 line; product active | |
| items[].qty | integer | yes | > 0; ≤ available stock unless override | override needs manager |
| items[].unit_price | money | yes | ≥ 0; defaults to product price | |
| discount | money | no | 0 ≤ discount ≤ subtotal | |
| payment_method | select | yes | cash, card, bank, easypaisa/jazzcash, udhaar | udhaar requires customer_id |
| amount_paid | money | yes | 0 ≤ amount ≤ total; remainder posts to udhaar | |
| note | text | no | ≤ 500 chars | |
| channel | select | system | pos, chat, whatsapp, voice | set by source |

#### F-010 Products and stock
| Field | Type | Required | Validation / rule | Notes |
| --- | --- | --- | --- | --- |
| sku | text | yes | unique per tenant, ≤ 40 chars | |
| name | text | yes | 2-120 chars | |
| category | text | no | ≤ 60 chars | |
| price | money | yes | ≥ 0 | |
| cost | money | no | ≥ 0 | needed for profit reports |
| qty_on_hand | integer | yes | ≥ 0 (changes only via stock movement after creation) | |
| reorder_level | integer | no | ≥ 0 | triggers low-stock alert |
| vendor_id | lookup | no | belongs to tenant | |
| image | file | no | jpg/png/webp ≤ 5 MB | Supabase Storage |
| active | boolean | yes | default true | |

#### F-018 Integrations
| Field | Type | Required | Validation / rule | Notes |
| --- | --- | --- | --- | --- |
| provider | select | yes | whatsapp_twilio, whatsapp_meta, facebook, instagram, vapi | |
| connect_method | action | yes | embedded signup / OAuth button, or manual token | manual token hidden behind "Advanced" |
| credentials | secret | conditional | stored encrypted; displayed masked; write-only | never returned by the API |
| external_id | text | system | phone number ID / page ID / assistant ID | unique across tenants (webhook routing) |
| status | enum | system | connected, pending, error, revoked | with last error message |

### 5.4 Other forms
Fields for P1 and P2 forms are specified when their phase starts, by the `architect` skill, and recorded here before implementation (change control §25).

## 6. Key Screen — Detailed Requirements
**F-006 Sales chat and F-005 Inbox carry the product.**
- Layout (desktop): three panes — conversation list, thread, context panel (customer, recent orders, udhaar balance, suggested actions). Phone: list → thread as separate screens.
- Thread messages stream over SSE; first token ≤ 2 s p95; full agent turn ≤ 10 s p95.
- Each AI-handled thread shows an **AI / Human** toggle; switching to Human stops agent replies for that conversation immediately.
- Agent proposals with side effects render as an inline **approval card** (what, amount, Approve / Edit / Reject) that also appears in F-021.
- Error states: provider down (banner with retry), message failed (per-message retry), agent timeout (fallback text and human-needed flag).
- Keyboard: Enter send, Shift+Enter newline, Ctrl+K palette, J/K move between conversations.
- Touch: swipe a conversation to assign or mark resolved; minimum 44 px targets.

## 7. Dashboards
| ID | Dashboard | Role | KPIs (each drills down to records) | Refresh | Phase |
| --- | --- | --- | --- | --- | --- |
| D-001 | Owner home | owner, manager | Today's sales, Profit today, Orders today, Low-stock items, Unpaid udhaar, Approvals waiting, AI briefing | 60 s | 1 |
| D-002 | Finance | owner | Revenue trend, Gross margin, Receivables aging, Vendor payables, Cash vs udhaar split | 5 min | 2 |
| D-003 | Agent command center | owner, manager | Agent runs today, Approval rate, Failed runs, AI spend vs cap, Time saved estimate | 60 s | 2 |
| D-004 | Platform overview | platform admin | Tenants, Active tenants (7 d), Messages/day, AI spend, Error rate | 5 min | 2 |

## 8. Dashboard UI Standard
KPI card = label, value (tabular numerals), delta vs previous period with direction icon, sparkline, click target to the underlying list pre-filtered. Allowed charts: line/area (trends), bar (comparisons), donut ≤ 5 slices (split). Global filters: date range (today, 7 d, 30 d, custom). All numbers scoped by `tenant_id` and role (staff never see profit). States: skeleton while loading, empty state with a primary action, error card with retry, unauthorized card with the required role. Currency formatted by one module (`formatMoney`) as `Rs 12,500`.

## 9. Reports
| ID | Report | Module | Filters | Export | Roles |
| --- | --- | --- | --- | --- | --- |
| R-001 | Daily sales summary | Sales | date, channel, staff | CSV, PDF | owner, manager |
| R-002 | Stock valuation | Inventory | category, vendor | CSV | owner, manager |
| R-003 | Low-stock list | Inventory | category, vendor | CSV | owner, manager |
| R-004 | Udhaar aging | Finance | customer, bucket | CSV, PDF | owner, manager |
| R-005 | Vendor payables | Finance | vendor, due date | CSV | owner |
| R-006 | Campaign performance | Marketing | campaign, date | CSV | owner, manager |
| R-007 | Agent audit export | Overview | agent, date, status | CSV | owner |

## 10. Core Business Workflows

### W-001 Tenant onboarding
1. User submits F-002; API creates user, tenant, owner membership, default settings (one DB transaction) and an audit row.
2. Wizard F-003 steps: shop details → connect WhatsApp → connect Facebook → add products (CSV or manual) → test message.
3. Each step stores progress on `tenants.onboarding_state`; skipping is allowed except shop details.
- **State machine:** `created -> shop_set -> whatsapp_connected -> products_added -> live`
- **Failure paths:** integration errors show the provider message and a "use the sandbox instead" fallback; CSV rows with errors are listed, valid rows import.

### W-002 Record a sale by chat
1. Staff sends "sold 5 shirts to Ali, 3000 paid".
2. Sales agent resolves product and customer via tools; if ambiguous it asks one clarifying question.
3. Agent drafts an order. Under the tenant's auto-approve limit it posts; otherwise it creates an approval.
4. Posting runs one transaction: order + items, stock movements, payment, ledger entry (udhaar remainder), audit rows.
- **State machine:** `draft -> pending_approval -> posted -> reversed` (reversal creates compensating rows, never deletes)
- **Failure paths:** insufficient stock → agent offers partial or backorder; duplicate message (same idempotency key) → returns the existing order.

### W-003 Inbound customer message (WhatsApp)
1. Webhook verifies signature, resolves tenant from the receiving number, stores the message.
2. If conversation is in AI mode, the customer-facing agent answers using read-only inventory/price tools and can create an order draft.
3. Orders created by customers go to approval; owner is notified; customer gets a confirmation after approval.
4. Human takeover stops the agent; a handoff note is added.
- **State machine:** `open -> ai_handling -> needs_human -> resolved`
- **Failure paths:** provider send fails → retry with backoff 3 times, then mark `send_failed` and surface in inbox.

### W-004 Scheduled marketing campaign
1. Owner defines a campaign (goal, posts per day, window, tone) in F-014/F-015.
2. Marketing agent generates posts (text + image); previews appear; approval mode per tenant (auto or manual).
3. Scheduler publishes at the scheduled time via the Facebook adapter; failures retry and are logged in F-016.
4. Comments are fetched; the agent proposes replies (auto-reply or approval).
- **State machine:** `scheduled -> generating -> pending_approval -> queued -> published | failed | cancelled`
- **Failure paths:** token expired → integration status `error`, owner notified, jobs paused.

### W-005 Approval
1. Agent action with side effects is stored in `agent_actions` as `pending` with a human-readable summary and payload hash.
2. Owner/Manager sees it in F-021 and the bell; Approve executes exactly the stored payload; Edit re-validates; Reject records the reason.
3. Pending approvals expire after 24 h (configurable).
- **State machine:** `pending -> approved -> executed | failed`, `pending -> rejected | expired`
- **Failure paths:** payload no longer valid (stock changed) → `failed` with explanation and a re-draft option.

### W-006 Low-stock reorder
1. Nightly job finds items where `qty_on_hand ≤ reorder_level`.
2. Inventory agent drafts a vendor message with suggested quantity.
3. Owner approves; message sent via WhatsApp; a draft purchase order is stored.
- **State machine:** `detected -> drafted -> approved -> sent`
- **Failure paths:** vendor has no phone → task stays `drafted` with a warning.

### W-007 Support voice call
1. VAPI webhook delivers call events; tenant resolved from the assistant ID.
2. Voice agent answers using read-only tools (stock, prices, order status) and may create a support ticket.
3. Transcript, duration and outcome are stored in `voice_calls`; escalations notify the owner.
- **State machine:** `ringing -> in_progress -> completed | escalated | failed`
- **Failure paths:** webhook signature invalid → 401 and logged; duplicate event → ignored by event ID.

### W-008 Automation recipes (launch set)
Pre-built, toggleable recipes stored as `automations` rows (`trigger`, `conditions_json`, `actions_json`) so a later React Flow builder only edits the same JSON. Launch set:
1. Low stock → draft vendor message (W-006)
2. New order → WhatsApp confirmation to the customer
3. Daily 09:00 business brief to the owner (§36.17)
4. Weekly post built from slow-moving stock (W-004)
5. Overdue udhaar (> 14 days) → polite payment reminder draft for approval
6. Unanswered customer message > 15 min → alert the owner
- **State machine:** recipe `disabled -> enabled`; each run `queued -> running -> succeeded | failed`
- **Failure paths:** a failing action disables the run, records the error in `automation_runs` and notifies the owner after 3 consecutive failures.

## 11. Offline & Synchronization
Not applicable — the product is online-only at launch. Phone users on weak connections get optimistic UI with retry for chat sends and a visible "reconnecting" banner. Offline sale capture is reconsidered when 3 tenants report connectivity loss as a blocker (deferred, trigger in §3.2 spirit).

## 12. Database / Data Model

### 12.1 Domains and representative tables
| Domain | Representative tables |
| --- | --- |
| Organization | tenants, memberships, tenant_settings, tenant_integrations |
| Security | users, roles (enum), sessions/refresh_tokens, audit_logs |
| Catalog and stock | products, inventory_items, stock_movements, vendors |
| Sales | customers, orders, order_items, payments |
| Finance | ledger_entries, purchase_orders, expenses |
| Conversations | conversations, messages, support_tickets, voice_calls |
| Marketing | facebook_accounts, marketing_posts, scheduled_campaigns, comment_replies |
| Automation and AI | automations, automation_runs, agent_actions, agent_runs |

### 12.2 Conventions
`lower_snake_case`, plural table names; UUID primary keys (`gen_random_uuid()`); `created_at`, `updated_at` timestamptz in UTC (display in `Asia/Karachi`); soft delete via `deleted_at` on catalog and party tables; money `NUMERIC(14,2)`; optimistic concurrency with `version` on orders and inventory_items; every business table has `tenant_id` + composite indexes starting with `tenant_id`; unique constraints are per tenant (`UNIQUE (tenant_id, sku)`).

### 12.3 Entity detail
- **tenants**(id, name, slug UNIQUE, plan, status, onboarding_state, timezone, currency, created_at)
- **users**(id, email UNIQUE, full_name, password_hash, is_platform_admin, last_login_at)
- **memberships**(id, tenant_id, user_id, role CHECK in owner|manager|staff, UNIQUE(tenant_id,user_id))
- **tenant_integrations**(id, tenant_id, provider, external_id UNIQUE per provider, credentials_enc, status, last_error)
- **products**(id, tenant_id, sku, name, category, price, cost, vendor_id, image_url, active); **inventory_items**(product_id, tenant_id, qty_on_hand, reorder_level, version)
- **stock_movements**(id, tenant_id, product_id, delta, reason, ref_type, ref_id, actor_type user|agent, actor_id)
- **orders**(id, tenant_id, customer_id, status, subtotal, discount, total, channel, idempotency_key, created_by); **order_items**(order_id, product_id, qty, unit_price)
- **payments**(id, tenant_id, order_id, amount, method, status); **ledger_entries**(id, tenant_id, party_type customer|vendor, party_id, amount, direction, ref_type, ref_id)
- **conversations**(id, tenant_id, channel, customer_id, mode ai|human, status, assigned_to); **messages**(id, conversation_id, direction, body, handled_by, provider_message_id UNIQUE)
- **agent_actions**(id, tenant_id, agent, tool, summary, payload_json, payload_hash, status, requested_by, approved_by, executed_at); **agent_runs**(id, tenant_id, agent, input, tokens, cost, outcome)
- **audit_logs**(id, tenant_id NULL for platform actions, actor_type, actor_id, action, entity, entity_id, before_json, after_json, request_id, at)

The ERD is generated from the live schema by the bootstrap-provided tooling and stored in `docs/erd/`.

### 12.4 Migration policy
Each schema change ships as an Alembic migration in the same PR; merged migrations are immutable; CI runs `alembic upgrade head` on an empty Postgres and fails if `alembic check` reports model drift. RLS policies are created inside migrations. The tenancy migration (phase 0/1) backfills existing JSON/SQLite data into one `demo` tenant.

### 12.5 Data retention, seed data, sample data
Messages and voice transcripts retained 12 months by default (tenant-configurable later); audit logs retained 24 months; soft-deleted rows purged after 90 days. `app/cli/seed.py` creates a demo tenant with products, customers, orders and a sample conversation; seed never runs in production unless `--allow-prod`.

## 13. API Requirements

### 13.1 Conventions
Base path `/api/v1`; REST nouns; list endpoints take `limit`, `cursor`, `sort`, `q`; mutation endpoints that can be retried accept `Idempotency-Key`; errors follow RFC 7807 (`type`, `title`, `status`, `detail`, `request_id`); every response carries `X-Request-ID`; rate limits per tenant and per IP (existing middleware *(observed)*); OpenAPI is the contract and the web client types are generated from it.

### 13.2 Endpoint register
| Area | Endpoint | Methods | Permission | Notes |
| --- | --- | --- | --- | --- |
| Auth | `/api/v1/auth/register`, `/login`, `/refresh`, `/me`, `/switch-tenant` | POST, GET | public / authenticated | token carries tenant and role |
| Tenants | `/api/v1/tenants/current`, `/settings` | GET, PATCH | owner | |
| Team | `/api/v1/team`, `/team/{id}` | GET, POST, PATCH, DELETE | owner | invite by email/phone |
| Inventory | `/api/v1/inventory`, `/inventory/{sku}`, `/inventory/{sku}/add-stock` | GET, POST, PUT, PATCH, DELETE | owner, manager (staff GET) | existing routes *(observed)* |
| Vendors | `/api/v1/vendors`, `/vendors/{id}/customers`, `/vendors/{id}/settings` | GET, POST, PUT | owner, manager | v1 vendor concept maps to tenant settings |
| Customers | `/api/v1/customers`, `/customers/{id}/messages` | GET, POST | owner, manager, staff | |
| Sales | `/api/v1/sales`, `/orders`, `/orders/{id}/reverse` | GET, POST | owner, manager, staff | reverse = manager |
| Chat (agents) | `/api/v1/chat/sales`, `/chat/inventory`, `/chat/finance` | POST (SSE) | role-scoped | streaming |
| Approvals | `/api/v1/approvals`, `/approvals/{id}/approve`, `/reject` | GET, POST | owner, manager | |
| Marketing | `/api/v1/marketing/accounts`, `/campaign`, `/scheduled`, `/posts`, `/comments`, `/insights` | GET, POST, PUT, PATCH, DELETE | owner, manager | maps 30+ existing routes *(observed)* |
| Integrations | `/api/v1/integrations`, `/integrations/{provider}/connect`, `/callback` | GET, POST, DELETE | owner | OAuth/embedded signup callbacks |
| Webhooks | `/webhook/whatsapp`, `/webhook/twilio`, `/vapi/webhook` | GET, POST | signature-verified | tenant resolved from channel id |
| Automations | `/api/v1/automations`, `/automations/{id}/toggle`, `/runs` | GET, POST, PATCH | owner, manager | |
| Reports | `/api/v1/reports/{id}` | GET | per report | CSV/PDF |
| Platform | `/api/v1/platform/tenants`, `/impersonate` | GET, POST | platform admin | impersonation audited |
| Ops | `/health`, `/health/chat`, `/logs` | GET | public / platform admin | existing *(observed)* |

### 13.3 Integrations (external)
| ID | System | Direction | Protocol | Auth | Failure handling | Phase |
| --- | --- | --- | --- | --- | --- | --- |
| I-001 | Twilio WhatsApp (sandbox, later production sender) | both | REST + webhook | account SID/token, signature check | retry 3× with backoff, then `send_failed` | 2 |
| I-002 | Meta WhatsApp Cloud API (Embedded Signup) | both | REST + webhook | per-tenant token, app secret signature | token refresh; status `error` on revocation | 3 |
| I-003 | Facebook/Instagram Graph API | both | REST | per-tenant page token | pause jobs, notify owner on expiry | 2 |
| I-004 | VAPI voice | both | REST + webhook | API key, webhook secret | ignore duplicate events; alert on repeated 5xx | 3 |
| I-005 | LLM provider (Gemini or OpenAI) | out | REST | server API key | timeout 30 s, one retry, graceful agent message | 1 |
| I-006 | Pexels images | out | REST | API key | fall back to text-only post | 2 |
| I-007 | Supabase Storage | out | REST | service key | signed URLs; retry uploads | 1 |

## 14. Security & Audit
- HTTPS in all non-development environments; HSTS on the web app.
- Role-based authorization enforced by the API; the UI hiding an action is convenience, not security.
- No credentials in source control; `.env.example` holds keys with empty values. A secret scan runs in CI.
- Passwords hashed with bcrypt; login rate limit and lockout; JWT access tokens ≤ 30 min with refresh rotation.
- Validation on all input through Pydantic v2; ORM or parameterized queries only; no string-built SQL.
- Sensitive data (tokens, phone numbers, message bodies) masked in logs; integration credentials encrypted at rest.
- Webhooks verify provider signatures before any processing.

### 14.1 Audited actions
Login, failed login, tenant switch; tenant, team and role changes; integration connect/disconnect; product create/update/delete and every stock movement; order post and reversal; payment and ledger entries; approval approve/reject/expire; every agent action with side effects (tool, payload hash, result); campaign create/publish/delete; platform-admin impersonation and any `system_session()` cross-tenant operation. Each row records actor (user or agent), tenant, entity, before/after, request ID and timestamp.

### 14.2 Roles and permission matrix
| Role | Modules / screens | Actions (view, create, edit, delete, approve, export, post, reverse) |
| --- | --- | --- |
| platform_admin | Platform tenants, logs, impersonation | view all tenants (read), suspend tenant, impersonate (audited); no business-data edits without impersonation |
| owner | all tenant modules, Settings, Integrations, Team | all actions including billing, integrations, delete, reverse, approve, export |
| manager | Inventory, Sales, Customers, Marketing, Inbox, Approvals, Automations | view, create, edit, approve, post, reverse, export; no integrations, team or tenant settings; Finance view-only |
| staff | Home (limited), Inbox, New sale, Orders, view stock | view, create sales and customers, post sales; no delete, reverse, approve, export, finance, marketing or settings |

Agents act with the permission set of the requesting user and never exceed it; scheduled agents act with a dedicated `system` actor restricted to the tenant's automation settings.

### 14.3 Data protection and privacy
Classification: *restricted* (integration tokens, password hashes), *confidential* (customer phone numbers, messages, finances), *internal* (catalog). TLS in transit; Supabase encryption at rest; tokens additionally envelope-encrypted by the app. Retention per §12.5. Tenant data export and deletion on request (owner-initiated) completes within 30 days. LLM calls send only the data needed for the task and never other tenants' data. Backups are encrypted (Supabase).

### 14.4 Threat notes
| Threat | Control |
| --- | --- |
| Cross-tenant data access | RLS + tenant-scoped sessions + route/agent isolation tests in CI |
| Prompt injection via customer messages | Customer-facing agent has read-only tools plus draft-only order creation; side effects need approval; tool args validated by schema |
| Stolen integration tokens | Encrypted at rest, write-only API, masked logs, rotate on disconnect |
| Webhook spoofing | Signature verification, replay window, event ID dedupe |
| Runaway AI cost or loops | Per-tenant spend cap, max tool calls per run, rate limits |

## 15. AI-Assisted Development Protocol
| Step | Developer / agent requirement |
| --- | --- |
| 1. Requirement | A small, testable story with acceptance criteria, citing PRD sections |
| 2. Context | Supply structure, conventions, constraints (`context/` folder and `AGENTS.md`) |
| 3. Design | Agree database/API/UI design before large generation (`/architect`) |
| 4. Generate | Scaffolding, implementation, refactoring, tests |
| 5. Review | A human reviews all generated code, queries, security, error handling (`/review`) |
| 6. Test | Acceptance tests written first and passing; `scripts/verify.sh` green |
| 7. PR | Requirement, test evidence, migration notes |
| 8. Merge | Only approved, passing PRs reach protected branches |

The owner remains accountable for architecture, security, correctness and maintainability. AI tooling is never given production database credentials, and the production `service_role` key is never placed in agent or developer environments.

## 16. UI/UX Standards
Provisional visual identity (§33), final information architecture. Layout: sidebar + top bar shell, 12-column content grid, max content width 1280 px. Density: comfortable on phone, compact option for tables. Typography: one UI sans family plus tabular numerals for money; scale 12/14/16/20/24/32. Colour: design tokens only (neutral surface scale, one accent, semantic success/warning/danger), light and dark themes. Forms: label above field, inline validation on blur, actionable messages. Data grids: sticky header, column visibility, CSV export, row actions menu. Feedback: toasts for success, inline for errors, skeletons for loading. Accessibility: WCAG 2.2 AA (contrast, focus visible, labels, reduced motion). Breakpoints: 360, 768, 1024, 1440. Keyboard support on all primary flows. Four states everywhere: loading, empty, error, unauthorized. All formatting through one `format` module (money in PKR, dates in `Asia/Karachi`). Urdu/RTL support is planned (Q-004): layouts use logical CSS properties from day one.

## 17. Performance Requirements
| Area | Target / requirement | How verified |
| --- | --- | --- |
| Standard interaction | p95 API response ≤ 300 ms for CRUD | Load test on staging, request-log metrics |
| Search | Product search p95 ≤ 300 ms at 10k SKUs per tenant | Seeded benchmark |
| Transaction posting | Sale post p95 ≤ 500 ms (excluding AI) | Integration timing test |
| AI turn | First token ≤ 2 s p95, full turn ≤ 10 s p95 | Synthetic chat test |
| Reports | Heavy reports ≤ 5 s for 90 days of data and run on a read-only session | Benchmark with `database_ro` *(observed)* |
| Concurrency | 50 concurrent users per instance without errors | Locust/k6 smoke |
| Database | Every query on business tables uses a `tenant_id`-prefixed index | Architecture test + EXPLAIN review |
| Web | LCP ≤ 2.5 s on a mid-range phone over 4G for the dashboard | Lighthouse in CI |

## 18. Backup & Disaster Recovery
RPO 24 h and RTO 4 h at launch (Supabase daily backups; point-in-time recovery enabled when the paid tier is adopted, target RPO 15 min). Backups encrypted, retained 7 days at launch. A restore into a scratch project is tested monthly and the result logged. Application is stateless so redeploy from the last image is the failover; secrets recoverable from the host secret store. On call: the owner.

## 19. Testing & Acceptance
| Test level | Scope | Tooling |
| --- | --- | --- |
| Unit | Domain rules, pricing, stock and ledger calculations | pytest |
| Architecture | Every table has `tenant_id` + RLS; every route has an authorization decision; layer imports; tools never accept tenant arguments | pytest (introspection of models/routes) |
| Integration | API + Postgres + auth + RLS + audit on a real database | pytest + httpx + ephemeral Postgres |
| Component / UI | Forms, validation, permissions, responsive behaviour | Vitest + Testing Library |
| E2E | Onboarding, record sale, approval flow, inbound WhatsApp (mock provider) | Playwright |
| Offline | Not applicable (§11) | — |
| Performance | Hot paths against §17 | k6 |
| Security | Dependency scan, secret scan, cross-tenant and role tests | pip-audit/npm audit, gitleaks, pytest |
| AI | Tool authorization, isolation, injection robustness, schema validity | pytest with recorded model fixtures |

Existing: 55 pytest files and 5 integration tests passing *(observed)*; the architecture and RLS suites are new and block merge.

## 20. Acceptance Criteria for Forms
Each form: follows §5.1 layout; fields match §5.3 exactly; inline validation with actionable messages; hidden for unauthorized roles and rejected by the API; shows audit/status panel where state-changing; has loading, empty, error and unauthorized states; fully keyboard-operable; usable at 360 px width; money and dates formatted by the shared module.

## 21. Acceptance Criteria for Dashboards
Every KPI drills down to its records; totals reconcile to source tables in an automated test; data is scoped by tenant and role; first meaningful paint within §17 targets; empty tenant shows a guided empty state, not zeros.

## 22. Phased Delivery Plan
| Phase | Scope | Exit criteria (a test a person can run) |
| --- | --- | --- |
| 0 | Foundation: spec harness, CI (`verify.sh`), Supabase projects and roles (§3.8), Data API lockdown, Alembic baseline, tenancy tables, RLS, JWT claims, role dependencies, architecture tests, secret hygiene (remove committed DSN script) | CI green; two seeded tenants cannot read each other's rows through any API route (test passes); login returns tenant and role |
| 1 | Public demo launch: services moved from JSON to DB, inventory/sales/customers/udhaar with stock movements, sales chat agent, approvals center, agent activity log, home dashboard, app shell, landing page, demo seed | A new visitor signs up, adds a product, records a sale by chat, sees stock and dashboard update, approves a pending action; all within 15 minutes |
| 2 | Channels and onboarding: Twilio sandbox WhatsApp, unified inbox with AI/Human toggle, onboarding wizard, per-tenant encrypted integrations, Facebook connect + scheduler on DB, finance overview, vendors, daily briefing, platform admin | A tenant connects WhatsApp sandbox and Facebook in the wizard; a customer message gets an AI reply; an owner takes over; a scheduled post publishes |
| 3 | Voice, automation recipes, marketing insights, Meta Embedded Signup, Urdu/RTL, reorder workflow | A VAPI call is answered and logged; an owner enables the low-stock recipe and receives a drafted vendor message; embedded signup connects a number without developer tools |
| 4 | Commercial: pricing and billing, compliance items (Q-001, Q-005), React Flow builder (if trigger met), marketplace connectors | Chosen plan can be purchased and enforced; compliance checklist signed off |

### 22.1 Launch-week plan (2 days)
- **Day 1** — Phase 0 complete (Supabase schema, `tenant_id` + RLS, JWT claims, role dependencies, architecture tests); move JSON stores to DB; per-tenant integration storage; Twilio sandbox adapter. *Done when:* the Phase 0 exit test passes and a sale is recorded through the API against Postgres for a demo tenant.
- **Day 2** — App shell, home dashboard, sales chat, approvals center, landing page, demo seed; record a 60-90 second demo video; publish the LinkedIn launch post. *Done when:* the Phase 1 exit test passes on the deployed demo and the video and post are published.

If Day 1 slips, cut in this order: Twilio adapter (use web chat only), landing page polish, dashboard sparklines. Never cut RLS or the architecture tests.

## 23. Required Deliverables
- Complete source code and repository history
- Alembic migrations and generated ERD in `docs/erd/`
- OpenAPI documentation and generated web client
- All forms and dashboards listed in §5 and §7 for the phase delivered
- Unit, integration, architecture, E2E and AI tests
- Deployment scripts and environment configuration guide
- Backup/restore guide
- Owner manual and "connect WhatsApp/Facebook" step-by-step guide pages
- Tenant onboarding and data-export guide

## 24. Definition of Done
- Requirement implemented and demonstrated
- Database migration (with RLS) included
- API and UI completed
- Validation and authorization implemented
- Audit requirements implemented
- Automated tests added and passing; `scripts/verify.sh` passes
- No critical/high unresolved defects
- Code reviewed by a human developer, including AI-generated code
- Documentation updated
- UAT passed

## 25. Change Control
Any feature, form, report, integration or workflow not in this PRD is handled by a change request recording: scope, business reason, effort, impact on schedule and cost, affected sections, decision, approver. Approved changes are recorded in §0.2; stack or architecture changes also produce an ADR in `docs/adr/`.

### 25.1 Change request log
| CR | Date | Requester | Summary | Sections | Decision | Approver |
| --- | --- | --- | --- | --- | --- | --- |
| — | — | — | none yet | — | — | — |

## 26. Initial Feature Priority
| Priority | Meaning | Items |
| --- | --- | --- |
| P0 — Mandatory MVP | Cannot ship without | Tenancy + RLS, auth + roles, DB-backed inventory/sales/customers, sales chat agent, approvals, audit, app shell + dashboard, onboarding, landing page |
| P1 — Commercial release | Needed to charge money | Twilio/Meta WhatsApp inbox, Facebook scheduler on DB, finance overview, vendors, integrations UI, daily briefing, platform admin |
| P2 — Expansion | Growth features | Marketing insights, voice agent settings, automation recipes, reports export, Urdu/RTL, voice-note orders (speech-to-text on WhatsApp audio), photo-to-product add (image → draft product), walkthrough videos for connecting WhatsApp/Facebook |
| P3 — Differentiation | Moat | React Flow builder, MCP server for tenant data, Instagram, marketplace connectors, anomaly detection |

## 27. Final Product Structure
| Module | Screens | Tables | APIs |
| --- | --- | --- | --- |
| Auth & Tenancy | F-001, F-002, F-003, F-019, F-020, F-025 | users, tenants, memberships, tenant_settings | `/auth`, `/tenants`, `/team`, `/platform` |
| Inventory | F-010, F-011, F-012 | products, inventory_items, stock_movements, vendors | `/inventory`, `/vendors` |
| Sales | F-006, F-007, F-008, F-009 | customers, orders, order_items, payments | `/sales`, `/orders`, `/customers`, `/chat` |
| Finance | F-013 | ledger_entries, purchase_orders, expenses | `/reports`, `/ledger` |
| Marketing | F-014, F-015, F-016, F-017 | facebook_accounts, marketing_posts, scheduled_campaigns, comment_replies | `/marketing` |
| Inbox & Voice | F-005, F-023 | conversations, messages, support_tickets, voice_calls | `/webhook/*`, `/vapi/webhook`, `/conversations` |
| AI Control | F-021, F-022, F-024 | agent_actions, agent_runs, automations, automation_runs | `/approvals`, `/automations` |
| Integrations | F-018 | tenant_integrations | `/integrations` |
| Overview & Public | F-004, F-026, F-027, F-028 | audit_logs | `/health`, `/logs` |

## 28. Approval
| Role | Name | Decision | Date |
| --- | --- | --- | --- |
| Product owner | Anees | pending | |
| Technical lead | Anees | pending | |

## 29. Visual UI / UX Wireframes — Dashboards

### 29.1 Owner home (D-001)
```
+------------------------------------------------------------------------+
| ☰ BazaarFlow   [Ctrl+K Search…]            🔔 3   Shop: Ali Mart ▾  AK |
+---------+--------------------------------------------------------------+
| Home    | Good morning, Ali.            [New sale] [Add stock] [Post]  |
| Inbox   +--------------+--------------+--------------+----------------+
| Sales   | Today's sales| Profit today | Orders today | Low-stock items|
| Stock   | Rs 42,500 ▲8%| Rs 9,800 ▲3% | 31  ▼2%      | 6              |
| Finance +--------------+--------------+--------------+----------------+
| Marketing| Sales, last 7 days (area chart)  | Approvals waiting (3)    |
| Voice   |                                   | • Reorder 40 × Rice  [✓][✗]|
| Automate|                                   | • Post: Eid offer    [✓][✗]|
| Settings+-----------------------------------+--------------------------+
|         | AI briefing: "6 items low; Ahmed owes Rs 12,000 (14 d)…"     |
+---------+--------------------------------------------------------------+
```

### 29.2 Agent command center (D-003)
```
+------------------------------------------------------------------------+
| Agent runs today | Approval rate | Failed runs | AI spend / cap        |
| 128              | 92%           | 2           | $0.84 / $5.00         |
+------------------------------------------------------------------------+
| Activity timeline (agent, tool, result, [Undo])   | Failures needing you|
+------------------------------------------------------------------------+
```

## 30. Visual Form Wireframes

### 30.1 New sale (F-007)
```
+------------------------------------------------------------------------+
| New sale                                                   [Draft]     |
+------------------------------------------------------------------------+
| customer_id [ Walk-in ▾ + ]        payment_method [ Cash ▾ ]           |
+------------------------------------------------------------------------+
| items: product_id        qty    unit_price     line total              |
|        [ Shirt – M ▾ ]   [ 5 ]  [ 600.00 ]     3,000.00     [🗑]        |
|        [ + add item ]                                                 |
+------------------------------------------------------------------------+
| discount [ 0 ]   amount_paid [ 3,000 ]   Total Rs 3,000  Due Rs 0     |
+------------------------------------------------------------------------+
| [Save draft] [Post sale] [Cancel]                                      |
+------------------------------------------------------------------------+
| Audit / status: created by Staff · stock will drop by 5 on post        |
+------------------------------------------------------------------------+
```

### 30.2 Sales chat (F-006)
```
+-------------------+-------------------------------+--------------------+
| Conversations     | Thread (AI ◉ / Human ○)       | Context            |
| • Ali  ▪ new      | You: sold 5 shirts to Ali     | Ali · udhaar Rs 0  |
| • Sara            | AI: Draft order Rs 3,000 →    | Last orders …      |
|                   |  [Approve][Edit][Reject]      | Suggested: add     |
|                   | [Type a message…]      [Send] | payment            |
+-------------------+-------------------------------+--------------------+
```

### 30.3 Integrations (F-018)
```
+------------------------------------------------------------------------+
| Integrations                                                           |
+------------------------------------------------------------------------+
| WhatsApp   ● connected  +92 3xx xxx   [Reconnect] [Disconnect]         |
| Facebook   ○ not connected            [Connect with Facebook]          |
| Voice      ○ not connected            [Set up voice agent]             |
|  ▸ Advanced: enter token manually (credentials are stored encrypted)   |
+------------------------------------------------------------------------+
| Audit / status: last sync 2 min ago · last error: none                 |
+------------------------------------------------------------------------+
```

### 30.4 Approvals center (F-021)
```
+------------------------------------------------------------------------+
| Approvals (3 pending)                                   [filter: all ▾] |
+------------------------------------------------------------------------+
| Reorder 40 × Rice from Karim Traders  · Inventory agent · 10:42        |
|   payload preview …                       [Approve] [Edit] [Reject]    |
+------------------------------------------------------------------------+
| Audit / status: approvals expire after 24 h                            |
+------------------------------------------------------------------------+
```

## 31. Visual Design Rules for Implementation
Tokens only (no hard-coded colours); 4 px spacing scale; reuse components registered in `context/ui-registry.md` before creating new ones (run `imprint` after each new component); icons from one set at one stroke width; motion limited to meaningful transitions under 200 ms honouring `prefers-reduced-motion`; money right-aligned with tabular numerals; no decorative gradients or stock-template layouts; one primary action per screen.

## 32. UI Acceptance Checklist
- [ ] Layout matches §5.1
- [ ] Every field is in §5.3 (no invented fields)
- [ ] Inline validation, actionable error messages
- [ ] Unauthorized actions hidden; API still enforces
- [ ] Loading, empty, error, unauthorized states present
- [ ] Keyboard navigation complete
- [ ] Responsive at 360 px and desktop
- [ ] Audit/status panel present where required
- [ ] Money/date formatting via the shared module

## 33. Note on Final UI Design
The visual identity is provisional: only token values (colour, type, radius) may change later; the information architecture, navigation (§4) and workflows are final. The `uiux` skill produces the design system and per-page documents before the frontend rebuild.

## 34. Mandatory Compliance / Regulatory Integration Requirement
Not applicable at the demo launch — no payments are taken and no tax documents are issued by the product. Pakistani data-protection, FBR/POS invoicing and platform-policy requirements are open questions (Q-001, Q-005) and become **P0 for phase 4** if the product issues invoices or processes payments. WhatsApp and Meta platform policies (opt-in, templates, 24 h window) apply from phase 2 and are tracked in the integration checklist.

### 34.1 Integration Scope
Not applicable — deferred to phase 4 pending Q-001 and Q-005.
### 34.2 Transaction Flow
Not applicable — see 34.1.
### 34.3 Integration Statuses
Not applicable — see 34.1.
### 34.4 Integration Form
Not applicable — see 34.1.
### 34.5 Failure Handling
Not applicable — see 34.1.
### 34.6 Reporting & Reconciliation
Not applicable — see 34.1.
### 34.7 Security Requirements
Not applicable — see 34.1.
### 34.8 Acceptance Criteria
Not applicable — see 34.1.

## 35. Mandatory P0 Compliance Requirement
No compliance item blocks the phase 1 demo. Items that block a paid launch: confirmation of applicable Pakistani privacy/tax rules (Q-001, Q-005) and Meta business verification for production WhatsApp (Q-002); both are scheduled in phase 4 and phase 3 respectively.

## 36. Mandatory Agentic AI Architecture

### 36.1 Agentic AI Product Vision
Jobs to be done: record and query business data in plain language, keep stock healthy, chase customer credit, produce marketing content, answer customers and callers. Beneficiaries: shopkeepers with no ERP training. "Good" means correct data changes, every action explainable and reversible, and the owner stays in control through approvals.

### 36.2 Agentic AI Architecture
User/customer message → orchestrator agent → specialist agent → approved tool → service layer (tenant-scoped session) → validated command/query → Postgres (RLS). The AI layer is a client of the service layer; webhooks and scheduler invoke the same path with a `system` or `customer` actor.

### 36.3 AI Must Not Have Direct Database Authority
The AI layer shall not hold database credentials or run arbitrary SQL. All reads and writes pass through approved tools that enforce tenant, role and approval rules; stock and money commands execute inside business transactions that write audit rows; every answer that cites numbers is traceable to the tool calls that produced them.

### 36.4 AI Tool / Function Layer
| Tool | Purpose | Read/Write | Required permission | Approval level |
| --- | --- | --- | --- | --- |
| `find_product` / `get_stock` | Look up catalog and quantity | Read | staff | none |
| `find_customer` / `get_balance` | Customer and udhaar lookup | Read | staff | none |
| `draft_order` | Prepare a sale | Draft | staff | none (draft only) |
| `post_order` | Post a sale and stock movement | Write | staff | auto under limit, else approval |
| `adjust_stock` | Correct quantity | Write | manager | approval |
| `record_payment` | Customer payment or udhaar settlement | Write | staff | auto under limit, else approval |
| `get_sales_summary` / `get_profit` | Reporting | Read | manager (profit) | none |
| `draft_vendor_message` / `send_message` | Vendor or customer WhatsApp | Write | manager | approval for vendors, rules for customers |
| `generate_post` / `publish_post` | Marketing content | Draft / Write | manager | per tenant mode |
| `create_support_ticket` | Voice/chat escalation | Write | customer actor | none |

### 36.5 Specialized Agents
| Agent | Responsibility | Tools it may call | Autonomy level |
| --- | --- | --- | --- |
| Orchestrator | Route intent to a specialist, ask clarifying questions | handoffs only | L2 |
| Sales | Orders, customers, udhaar | find_*, draft_order, post_order, record_payment, get_sales_summary | L3 |
| Inventory | Stock, reorder, vendors | find_product, get_stock, adjust_stock, draft_vendor_message | L3 |
| Finance | Profit, receivables, payables explanations | get_sales_summary, get_profit, get_balance | L1-L2 |
| Marketing | Posts, campaigns, comment replies | generate_post, publish_post | L3 (auto-publish optional per tenant) |
| Customer support | Inbound WhatsApp and voice | find_product, get_stock, draft_order, create_support_ticket | L2-L3, read-mostly |

### 36.6 AI Autonomy Levels
L1 explain · L2 recommend · L3 draft (approval required) · L4 act within limits · L5 fully autonomous. Launch ceiling is L3 for all agents, with L4 only for sales posting under a tenant-configured amount. Promotion of an agent/tool to a higher level requires 30 days of runs with approval rate ≥ 95% and zero reversals attributed to the agent.

### 36.7 AI Approval Center
F-021 lists pending, executed and rejected agent actions with summary, payload preview, requester, age, and Approve / Edit / Reject. Approve executes the stored payload hash only. Notifications go to the bell and, optionally, the owner's WhatsApp.

### 36.8 AI Command Center Dashboard
D-003 (§7): runs, approval rate, failures, AI spend vs cap, estimated time saved.

### 36.9 AI Agent Activity / Audit Form
F-022 lists every `agent_runs` row: who asked, agent, tools called with inputs/outputs (masked), approvals, tokens and cost, outcome, linked audit rows.

### 36.10 Agent Requirements — Sales
Parse quantities, product and customer references in English, Urdu and Roman Urdu; ask one clarifying question when ambiguity affects money; never post when stock is insufficient without an explicit override; always show a draft summary before posting.
### 36.11 Agent Requirements — Inventory
Detect low stock nightly; propose reorder quantities from recent sales velocity; never change quantity without a `stock_movements` row.
### 36.12 Agent Requirements — Finance
Explain profit, receivables and payables from tool data only; refuse to estimate when data is missing and say what is missing.
### 36.13 Agent Requirements — Marketing
Generate posts in the tenant's tone and language; respect the posting window and posts-per-day; attach Pexels or uploaded media; hold for approval unless the tenant enabled auto-publish; propose comment replies and never reply to abusive comments automatically.
### 36.14 Agent Requirements — Customer support
Answer only from tenant data; never reveal other customers' data; hand off to a human on request, anger, refund or unclear intent; voice replies ≤ 30 words per turn.
### 36.15 Agent Requirements — Compliance
Not applicable at launch (see §34); reserved for phase 4.

### 36.16 Anomaly Detection Agent
Phase 4 (P3): flags unusual stock adjustments, large udhaar, sudden sales drops; read-only, produces recommendations only.

### 36.17 Daily Autonomous Business Brief
A scheduled job per tenant (default 09:00 `Asia/Karachi`) composes sales, profit, low stock, overdue udhaar and pending approvals from tool data and sends it on WhatsApp and the dashboard. Phase 2.

### 36.18 Agent Guardrails
Per-tenant monthly AI spend cap (Q-003) with a soft warning at 80% and a hard stop at 100%; max 8 tool calls per run; rate limit per user; blocked actions: deleting products or customers, changing roles, connecting integrations, changing prices in bulk; customer-originated text is treated as untrusted data, never as instructions; PII not sent to the model unless required by the task; human in the loop for every write above limits.

### 36.19 AI Security & Privacy
No cross-tenant context in prompts; per-tenant memory stored with `tenant_id` and RLS; prompts and outputs logged with masked PII; model provider receives no credentials; provider chosen with data-retention opt-out where available.

### 36.20 AI Testing Requirements
Tests for: tool authorization by role; tenant isolation (agent for tenant A cannot reach tenant B ids); action safety (no write without approval above limits); prompt-injection corpus in customer messages; output schema validation; transaction integrity (rollback on failure); audit row presence for every write.

### 36.21 AI-Assisted Development of the AI Layer
Prompts live in `app/prompts/` as versioned markdown; changes ship with updated evaluation fixtures; model calls in tests are replayed from recorded fixtures.

### 36.22 Recommended AI Technology Integration
OpenAI Agents SDK for agent loops and handoffs; model provider configurable (Gemini via OpenAI-compatible endpoint, or OpenAI) behind `app/agents/config.py` with lazy initialization *(observed)*; MCP server (`app/mcp_server/`) exposing read-only tenant tools to external assistants in phase 4; Sentry and structured logs for observability; evaluation fixtures for regression.

### 36.23 AI Phase Roadmap
Phase 1: sales/inventory/finance agents on the DB with approvals. Phase 2: customer-facing WhatsApp agent, marketing agent on DB, daily brief. Phase 3: voice agent per tenant, automation recipes. Phase 4: anomaly detection, MCP server, builder.

### 36.24 Agentic AI Acceptance Criteria
All §36.20 tests pass in CI; 100% of agent writes have audit rows; no agent can execute a blocked action; approvals execute exactly the stored payload hash; AI spend cap stops runs in a test; a cross-tenant agent probe returns nothing.

## 37. Updated Master Priority
1. Tenancy, RLS, auth/roles, audit (phase 0)
2. DB-backed inventory/sales/customers with approvals and the sales agent (phase 1)
3. App shell, dashboard, onboarding, landing page (phase 1-2)
4. WhatsApp (Twilio sandbox) inbox and customer agent, Facebook scheduler on DB, per-tenant integrations (phase 2)
5. Voice, recipes, insights, Embedded Signup, Urdu (phase 3)
6. Billing, compliance, builder, connectors (phase 4)

## 38. Final Architectural Principle
The API is the only owner of business logic and data; every client — browser, webhook, scheduler and AI agent — is a tenant-scoped client of it, and no client can act on another tenant's data or change money, stock or public content without an auditable, permitted path.

---

## Appendix A — Decision log
| Date | Decision | Reason | Alternatives considered |
| --- | --- | --- | --- |
| 2026-10-01 | Supabase Postgres as the database | Owner decision; managed backups, storage, RLS | Neon, self-hosted |
| 2026-10-01 | Keep FastAPI-issued JWT; RLS via per-request `app.tenant_id` | Existing auth; backend is the only DB client | Supabase Auth with `auth.jwt()` policies |
| 2026-10-01 | Use Supabase only as Postgres + Storage + backups; no Supabase Auth/Realtime/Edge Functions | Backend already owns auth; fewer moving parts for a two-day launch | Full Supabase BaaS with client SDK |
| 2026-10-01 | Transaction-mode pooler for runtime, direct connection for Alembic | Pooler scales connections; DDL needs sessions | Direct everywhere |
| 2026-10-01 | Row-level multi-tenancy | Simplest at this scale | Schema-per-tenant, DB-per-tenant |
| 2026-10-01 | Twilio sandbox for demo WhatsApp; Meta Embedded Signup for production onboarding | Free to test; removes developer steps for owners | Composio MCP (does not solve onboarding), direct Meta only |
| 2026-10-01 | VAPI now, LiveKit/Pipecat deferred | Two-day launch | Own voice pipeline |
| 2026-10-01 | Pre-built automation recipes now, React Flow later | Time; recipes share the schema the builder will edit | Builder at launch |
| 2026-10-01 | Four roles: platform_admin, owner, manager, staff | Matches retail hierarchy | Granular permission sets |

## Appendix B — Risks
| ID | Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- |
| RK-01 | Two-day launch is too short for production-profile multi-tenancy plus UI rebuild | High | High | Phase 0-1 scoped to the demo exit test; UI shell before polish; cut P1 items first | Owner |
| RK-02 | Tenant data leak through a missed filter | Medium | Critical | RLS + architecture tests + no-BYPASSRLS role | Owner |
| RK-03 | Meta/WhatsApp approval delays block production channels | High | Medium | Twilio sandbox for demo; start Tech Provider application early (Q-002) | Owner |
| RK-04 | LLM cost overruns | Medium | Medium | Spend caps, tool-call limits, cheaper default model | Owner |
| RK-05 | Legacy JSON data and `backend/` folder cause confusion | Medium | Low | One-time backfill to demo tenant; remove `backend/` after smoke test | Owner |
| RK-07 | Supabase free project pauses or hits limits during the public demo | High | High | Upgrade demo project to Pro before launch; health check + uptime alert | Owner |
| RK-08 | Data API exposes tables via `anon` key if a table lacks RLS/revokes | Medium | Critical | Revoke grants in baseline migration; architecture test asserts RLS + no anon grants; review Supabase security advisor | Owner |
| RK-09 | asyncpg prepared-statement errors behind the transaction pooler | Medium | Medium | Disable statement caches in engine config; integration test against pooler URL | Owner |
| RK-06 | Committed secrets (Sentry DSN in a verify script) | Medium | Medium | Delete the script; add secret scan in CI | Owner |

## Appendix C — Cost and infrastructure profile
| Service | Tier / plan | Limit that matters | Est. monthly cost |
| --- | --- | --- | --- |
| Supabase (dev/staging/prod projects) | Free for dev; Pro for prod/demo | Free pauses after inactivity and has small DB/storage quotas; Pro adds PITR and no pausing | $0 dev, ~$25 per paid project (verify current pricing) |
| API hosting | Fly.io/Railway small instance | RAM for scheduler + agents | ~$5-10 |
| Web hosting | Vercel hobby | Bandwidth | $0 |
| Twilio WhatsApp | Sandbox for demo | Sandbox only messages joined numbers | $0 (production per-message fees apply; verify current pricing) |
| VAPI | Pay per minute | Minutes per demo call | usage-based (verify current pricing) |
| LLM | Gemini/OpenAI | Tokens per tenant | capped per tenant (Q-003) |
| Sentry | Free developer tier | Event quota | $0 |
