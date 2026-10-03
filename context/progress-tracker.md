# Progress Tracker

Update this file after every completed task. Anyone reading it should immediately know what is done, what is in progress, and what is next.

---

## Current Status

**Phase:** Phase 1A, shop basics on the database (Phase 0 closed 2026-10-03)
**Last completed:** 45
**In progress:** Phase 1A on branch `feat/phase-1-mvp`, strictly in the order listed
**Next:** Batch 1B gate, then 1C task 50
**Blockers:** the owner has not yet said "let's build it"; 26 needs vendor sandbox accounts; DEMO_USER_PASSWORD must be set in `.env` (owner)

### Phase 0 status

**Phase 0 is closed: 26 tasks done.** 02, 12, 21, 26 and 29 moved into Phase 1 (1C and 1B) on 2026-10-03; leaked keys are rotated and `next` is 16.3.8.

---

## Phase 0 — Foundation: spec harness, CI (`verify.sh`), Supabase projects and roles (§3.8), Data API lockdown, Alembic baseline, tenancy tables, RLS, JWT claims, role dependencies, architecture tests, secret hygiene (remove committed DSN script)

- [x] 00 Architecture Decision Record + sign-off
- [x] 01 Repo scaffold
- [x] 03 Database foundation
- [x] 04 Authentication & authorization
- [x] 05 Tenancy enforcement
- [x] 06 Audit infrastructure
- [x] 07 UI foundation
- [x] 08 Vertical slice
- [x] 09 Supabase projects (dev/staging/prod), database roles migrator/app_…
- [x] 10 Tenancy schema and RLS baseline migration
- [x] 11 Architecture tests in CI
- [x] 13 Channel adapter interface (connect, send, receive, verify_webhook)…
- [x] 14 Agent tool layer inside the API process: tools call services with…
- [x] 15 Rewrite the 19 quarantined tests (pytest markers legacy_port and l…
- [x] 16 Burn down the mypy legacy override list in pyproject.toml module b…
- [x] 17 Fix the double-prefixed v1 routes (/api/v1/api/...) and consolidat…
- [x] 18 Scaffold the web app with the chosen framework, strict TypeScript,…
- [x] 19 Design tokens and layout shell [web-app pack]
- [x] 20 Authentication and role guard [web-app pack]
- [x] 22 Scaffold the API with lint, format, typecheck and a health endpoin…
- [x] 23 Database foundation and first migration [backend-api pack]
- [x] 24 Authentication and authorisation skeleton [backend-api pack]
- [x] 25 OpenAPI contract and generated client with a drift check [backend-…
- [x] 27 Integration skill: install an upstream one or generate a project-l…
- [x] 28 Agent service skeleton, separate from the API, with no database cr…
- [x] 30 Evaluation harness with a first golden set [agents pack]

## Phase 1 — Public demo launch: services moved from JSON to DB, inventory/sales/customers/udhaar with stock movements, sales chat agent, approvals center, agent activity log, home dashboard, app shell, landing page, demo seed

### Phase 1A — Shop basics on the database

- [x] 56 Tenant or branch scoping (if the PRD has it) [backend-api pack]
- [x] 55 First vertical slice: one resource with create, read, update, dele…
- [x] 41 Products and stock
- [x] 51 First vertical slice through the UI, API and database [web-app pac…
- [x] 52 Form pattern: validation, error display, double-submit protection…
- [x] 34 Sign in
- [x] 35 Create account and shop
- [x] 40 Customers and udhaar ledger
- [x] 38 New sale
- [x] 39 Orders list and detail
- [x] 43 Team and roles

### Phase 1B — AI on the database

- [x] 49 Integration: LLM provider (Gemini or OpenAI)
- [x] 29 Tool catalogue with schemas, permissions and a test per tool [agen…
- [x] 44 Approvals center
- [x] 63 First agent flow end to end with human approval on side effects [a…
- [x] 37 Sales chat (agent)
- [x] 64 Run caps, spend cap and kill switch [agents pack]
- [x] 65 Tracing with redaction [agents pack]
- [x] 45 Agent activity log

### Phase 1C — Dashboard and launch

- [ ] 50 Integration: Supabase Storage
- [ ] 42 Marketing studio
- [ ] 36 Home dashboard
- [ ] 48 Owner home dashboard
- [ ] 46 Public landing page
- [ ] 47 Public live demo
- [ ] 57 Structured logging, request ids and error reporting [backend-api p…
- [ ] 58 Backups and one timed restore [backend-api pack]
- [ ] 53 Accessibility and performance gates [web-app pack]
- [ ] 54 End-to-end smoke test of the critical flow [web-app pack]
- [ ] 02 CI/CD + verification
- [ ] 12 Secret hygiene
- [ ] 21 Deploy a preview environment on a free tier [web-app pack]
- [ ] 26 Vendor accounts, sandbox access and credentials in the secret mana…

## Phase 2 — Channels and onboarding: Twilio sandbox WhatsApp, unified inbox with AI/Human toggle, onboarding wizard, per-tenant encrypted integrations, Facebook connect + scheduler on DB, finance overview, vendors, daily briefing, platform admin

- [ ] 70 Onboarding wizard
- [ ] 71 Unified inbox
- [ ] 72 Stock movements
- [ ] 73 Vendors and payables
- [ ] 74 Finance overview and ledger
- [ ] 75 Marketing schedule
- [ ] 76 Marketing activity
- [ ] 77 Integrations (WhatsApp, Facebook, VAPI)
- [ ] 78 Shop profile and settings
- [ ] 79 Platform admin: tenants
- [ ] 80 Finance dashboard
- [ ] 81 Agent command center dashboard
- [ ] 82 Platform overview dashboard
- [ ] 83 Integration: Twilio WhatsApp (sandbox, later production sender)
- [ ] 84 Integration: Facebook/Instagram Graph API
- [ ] 85 Integration: Pexels images

Deferred from Phase 1 (integration pack):
- [ ] 59 Authentication to the vendor (OAuth or key) with token refresh [in…
- [ ] 60 One end-to-end integration flow against the sandbox [integrations…
- [ ] 61 Webhook endpoint with signature verification and idempotency [inte…
- [ ] 62 Failure handling and alerting [integrations pack]

## Phase 3 — Voice, automation recipes, marketing insights, Meta Embedded Signup, Urdu/RTL, reorder workflow

- [ ] 86 Marketing insights
- [ ] 87 Voice calls and agent settings
- [ ] 88 Automation recipes
- [ ] 89 System logs
- [ ] 90 Integration: Meta WhatsApp Cloud API (Embedded Signup)
- [ ] 91 Integration: VAPI voice

Deferred from Phase 1 (voice pack):
- [ ] 66 One complete call flow with confirmation of captured data [voice-a…
- [ ] 67 Barge-in, silence and noise handling [voice-agents pack]
- [ ] 68 Human handoff and keypad fallback [voice-agents pack]
- [ ] 69 Consent notice, redaction and retention [voice-agents pack]

## Phase 4 — Commercial: pricing and billing, compliance items (Q-001, Q-005), React Flow builder (if trigger met), marketplace connectors

- [ ] 92 (no forms, dashboards or integrations are assigned to this phase i…

## Needs a human

Older items (ADR sign-off, `.env.example`, key rotation, `next` bump, pushing the branch) are resolved; see `context/progress-log.md`.

| Task | Question |
| --- | --- |
| 02 | Check the GitHub Actions run for the pushed commit and confirm it is green (no `gh` CLI here) |
| 21 | Vercel secrets, needed after batch 1C |
| 26 | Twilio sandbox account (paused) |

Open questions Q-001 to Q-006 are in PRD §0.4; resolve each before the task that depends on it.
