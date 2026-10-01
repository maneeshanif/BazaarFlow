# Progress Tracker

Update this file after every completed task. Anyone reading it should immediately know what is done, what is in progress, and what is next.

---

## Current Status

**Phase:** Phase 0 — Foundation: spec harness, CI (`verify.sh`), Supabase projects and roles (§3.8), Data API lockdown, Alembic baseline, tenancy tables, RLS, JWT claims, role dependencies, architecture tests, secret hygiene (remove committed DSN script)
**Last completed:** — (nothing has passed the full task process yet; see the Phase 0 audit in progress-log.md)
**In progress:** Phase 0, working strictly in task order: 00, 01, 02, ...
**Next:** 00 ADR sign-off (needs the owner), then 01
**Blockers:** 00 needs the owner's sign-off; 09 needs Supabase credentials; 26 needs vendor sandbox accounts

---

## Phase 0 — Foundation: spec harness, CI (`verify.sh`), Supabase projects and roles (§3.8), Data API lockdown, Alembic baseline, tenancy tables, RLS, JWT claims, role dependencies, architecture tests, secret hygiene (remove committed DSN script)

- [ ] 00 Architecture Decision Record + sign-off
- [ ] 01 Repo scaffold
- [ ] 02 CI/CD + verification
- [ ] 03 Database foundation
- [ ] 04 Authentication & authorization
- [ ] 05 Tenancy enforcement
- [ ] 06 Audit infrastructure
- [ ] 07 UI foundation
- [ ] 08 Vertical slice
- [ ] 09 Supabase projects (dev/staging/prod), database roles migrator/app_…
- [ ] 10 Tenancy schema and RLS baseline migration
- [ ] 11 Architecture tests in CI
- [ ] 12 Secret hygiene
- [ ] 13 Channel adapter interface (connect, send, receive, verify_webhook)…
- [ ] 14 Agent tool layer inside the API process: tools call services with…
- [ ] 15 Rewrite the 19 quarantined tests (pytest markers legacy_port and l…
- [ ] 16 Burn down the mypy legacy override list in pyproject.toml module b…
- [ ] 17 Fix the double-prefixed v1 routes (/api/v1/api/...) and consolidat…
- [ ] 18 Scaffold the web app with the chosen framework, strict TypeScript,…
- [ ] 19 Design tokens and layout shell [web-app pack]
- [ ] 20 Authentication and role guard [web-app pack]
- [ ] 21 Deploy a preview environment on a free tier [web-app pack]
- [ ] 22 Scaffold the API with lint, format, typecheck and a health endpoin…
- [ ] 23 Database foundation and first migration [backend-api pack]
- [ ] 24 Authentication and authorisation skeleton [backend-api pack]
- [ ] 25 OpenAPI contract and generated client with a drift check [backend-…
- [ ] 26 Vendor accounts, sandbox access and credentials in the secret mana…
- [ ] 27 Integration skill: install an upstream one or generate a project-l…
- [ ] 28 Agent service skeleton, separate from the API, with no database cr…
- [ ] 29 Tool catalogue with schemas, permissions and a test per tool [agen…
- [ ] 30 Evaluation harness with a first golden set [agents pack]
- [ ] 31 Channel setup (number or WebRTC room) and a hello-world call [voic…
- [ ] 32 Latency and cost instrumentation per turn [voice-agents pack]
- [ ] 33 Evaluation set of recorded calls [voice-agents pack]

## Phase 1 — Public demo launch: services moved from JSON to DB, inventory/sales/customers/udhaar with stock movements, sales chat agent, approvals center, agent activity log, home dashboard, app shell, landing page, demo seed

- [ ] 34 Sign in
- [ ] 35 Create account and shop
- [ ] 36 Home dashboard
- [ ] 37 Sales chat (agent)
- [ ] 38 New sale
- [ ] 39 Orders list and detail
- [ ] 40 Customers and udhaar ledger
- [ ] 41 Products and stock
- [ ] 42 Marketing studio
- [ ] 43 Team and roles
- [ ] 44 Approvals center
- [ ] 45 Agent activity log
- [ ] 46 Public landing page
- [ ] 47 Public live demo
- [ ] 48 Owner home dashboard
- [ ] 49 Integration: LLM provider (Gemini or OpenAI)
- [ ] 50 Integration: Supabase Storage
- [ ] 51 First vertical slice through the UI, API and database [web-app pac…
- [ ] 52 Form pattern: validation, error display, double-submit protection…
- [ ] 53 Accessibility and performance gates [web-app pack]
- [ ] 54 End-to-end smoke test of the critical flow [web-app pack]
- [ ] 55 First vertical slice: one resource with create, read, update, dele…
- [ ] 56 Tenant or branch scoping (if the PRD has it) [backend-api pack]
- [ ] 57 Structured logging, request ids and error reporting [backend-api p…
- [ ] 58 Backups and one timed restore [backend-api pack]
- [ ] 59 Authentication to the vendor (OAuth or key) with token refresh [in…
- [ ] 60 One end-to-end integration flow against the sandbox [integrations…
- [ ] 61 Webhook endpoint with signature verification and idempotency [inte…
- [ ] 62 Failure handling and alerting [integrations pack]
- [ ] 63 First agent flow end to end with human approval on side effects [a…
- [ ] 64 Run caps, spend cap and kill switch [agents pack]
- [ ] 65 Tracing with redaction [agents pack]
- [ ] 66 One complete call flow with confirmation of captured data [voice-a…
- [ ] 67 Barge-in, silence and noise handling [voice-agents pack]
- [ ] 68 Human handoff and keypad fallback [voice-agents pack]
- [ ] 69 Consent notice, redaction and retention [voice-agents pack]

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

## Phase 3 — Voice, automation recipes, marketing insights, Meta Embedded Signup, Urdu/RTL, reorder workflow

- [ ] 86 Marketing insights
- [ ] 87 Voice calls and agent settings
- [ ] 88 Automation recipes
- [ ] 89 System logs
- [ ] 90 Integration: Meta WhatsApp Cloud API (Embedded Signup)
- [ ] 91 Integration: VAPI voice

## Phase 4 — Commercial: pricing and billing, compliance items (Q-001, Q-005), React Flow builder (if trigger met), marketplace connectors

- [ ] 92 (no forms, dashboards or integrations are assigned to this phase i…


## History

Finished work, decisions and rulings are appended to `context/progress-log.md` (append-only). Keep this file short: update the status block and tick the checklist, nothing else.

## Open Questions

_From PRD §0.4. Resolve or escalate before the task that depends on it._

- Q-001 Which Pakistani data-protection and tax rules (FBR POS integration, PECA, draft Personal Data Protection law) apply at paid launch? (blocks §34, phase 4)
- Q-002 Meta Tech Provider application: who holds the verified Meta Business account, and what is the lead time? (blocks I-002, phase 2)
- Q-003 Which LLM provider and model is the production default (Gemini vs OpenAI), and what per-tenant monthly AI spend cap applies? (blocks §36.18, phase 1)
- Q-004 Is Urdu (RTL) UI required at launch or phase 3? (blocks §16, phase 3)
- Q-005 Do retailers need GST/sales-tax invoices with FBR codes at launch? (blocks §34, phase 4)
- Q-006 Pricing plans and limits (messages, AI calls, voice minutes) once the demo ends. (blocks §26, phase 4)
