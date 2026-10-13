# Progress Tracker

Update this file after every completed task. Anyone reading it should immediately know what is done, what is in progress, and what is next.

---

## Current Status

**Phase:** Phases 2 and 3 code complete except the vendor-dependent tasks 31 and 90, and the deferred workflow steps (order drafts, comment replies, draft purchase orders, Urdu/RTL core) built 2026-10-13 (see `docs/superpowers/specs/2026-10-13-deferred-features-design.md`). Phase 1 code closed 2026-10-04
**Last completed:** 91
**In progress:** Phase 2 on branch `feat/phase-1-mvp` (owner is away; see docs/superpowers/specs/2026-10-06-phase-2-design.md)
**Next:** owner decisions on the "Needs a human" list below (Phase 3 and 4 have not been started); owner actions: 02 (confirm CI green after this push), 12 (copy .env.example), 21 (Vercel secrets), 26 (Twilio sandbox)
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

- [x] 50 Integration: Supabase Storage
- [x] 42 Marketing studio
- [x] 36 Home dashboard
- [x] 48 Owner home dashboard
- [x] 46 Public landing page
- [x] 47 Public live demo
- [x] 57 Structured logging, request ids and error reporting [backend-api p…
- [x] 58 Backups and one timed restore [backend-api pack]
- [x] 53 Accessibility and performance gates [web-app pack]
- [x] 54 End-to-end smoke test of the critical flow [web-app pack]
- [ ] 02 CI/CD + verification
- [ ] 12 Secret hygiene
- [ ] 21 Deploy a preview environment on a free tier [web-app pack]
- [ ] 26 Vendor accounts, sandbox access and credentials in the secret mana…

## Phase 2 — Channels and onboarding: Twilio sandbox WhatsApp, unified inbox with AI/Human toggle, onboarding wizard, per-tenant encrypted integrations, Facebook connect + scheduler on DB, finance overview, vendors, daily briefing, platform admin

- [x] 70 Onboarding wizard
- [x] 71 Unified inbox
- [x] 72 Stock movements
- [x] 73 Vendors and payables
- [x] 74 Finance overview and ledger
- [x] 75 Marketing schedule
- [x] 76 Marketing activity
- [x] 77 Integrations (WhatsApp, Facebook, VAPI)
- [x] 78 Shop profile and settings
- [x] 79 Platform admin: tenants
- [x] 80 Finance dashboard
- [x] 81 Agent command center dashboard
- [x] 82 Platform overview dashboard
- [x] 83 Integration: Twilio WhatsApp (sandbox, later production sender)
- [x] 84 Integration: Facebook/Instagram Graph API
- [x] 85 Integration: Pexels images

Deferred from Phase 1 (integration pack):
- [x] 59 Authentication to the vendor (OAuth or key) with token refresh [in…
- [x] 60 One end-to-end integration flow against the sandbox [integrations…
- [x] 61 Webhook endpoint with signature verification and idempotency [inte…
- [x] 62 Failure handling and alerting [integrations pack]

## Phase 3 — Voice, automation recipes, marketing insights, Meta Embedded Signup, Urdu/RTL, reorder workflow

- [x] 86 Marketing insights
- [x] 87 Voice calls and agent settings
- [x] 88 Automation recipes
- [x] 89 System logs
- [ ] 90 Integration: Meta WhatsApp Cloud API (Embedded Signup)
- [x] 91 Integration: VAPI voice

Deferred from Phase 1 (voice pack):
- [x] 66 One complete call flow with confirmation of captured data [voice-a…
- [x] 67 Barge-in, silence and noise handling [voice-agents pack]
- [x] 68 Human handoff and keypad fallback [voice-agents pack]
- [x] 69 Consent notice, redaction and retention [voice-agents pack]

## Phase 4 — Commercial: pricing and billing, compliance items (Q-001, Q-005), React Flow builder (if trigger met), marketplace connectors

- [ ] 92 (no forms, dashboards or integrations are assigned to this phase i…

## Needs a human

Older items (ADR sign-off, `.env.example`, key rotation, `next` bump, pushing the branch) are resolved; see `context/progress-log.md`.

| Task | Question |
| --- | --- |
| INCIDENT | **The real Supabase database was wiped during a verification run.** `verify.sh --slow --all` ran `alembic upgrade/downgrade base/upgrade` against the URL in `.env` (`DATABASE_URL_MIGRATIONS`) instead of its throwaway database. The schema is now empty at revision 06 (demo tenant, demo users, demo products and any visitor sign-ups are gone). `verify.sh` is fixed (both URLs pinned to the throwaway DB, non-local URLs refused before any downgrade, every alembic step fails the run) and a test guards it. To restore the demo data: `uv run alembic upgrade head` then `SEED_ROLE_USERS=true uv run python -m app.cli.seed` (password from `DEMO_USER_PASSWORD`). Please also run `alembic upgrade head` once to reach revision 07 |
| 12 / env | `.env.example` is protected from the assistant and is missing 24 variables (agents, LLM, storage, demo, logging, sign-up limit). Run once: `cp docs/operations/env.example.proposed .env.example` (every variable is documented in `docs/operations/env-vars.md` and a test keeps the two lists equal; all values are empty). That closes the last open item of task 12
| 49 | The live Gemini behaviour (strict tool schemas, Roman Urdu quality) has only been tested against recorded responses and the scripted model: try one real chat with `GEMINI_API_KEY` set |
| demo | The demo password `12345678` is only safe for a local database; use a strong `DEMO_USER_PASSWORD` for anything public |
| 02 | Check the GitHub Actions run for the pushed commit and confirm it is green (no `gh` CLI here) |
| 21 | Vercel secrets, needed after batch 1C |
| 26 | Twilio sandbox account (paused) |
| 2D/2E gate | `verify.sh --slow --all` for batches 2D and 2E has **not** completed: the 2D run was stopped by the system for low memory at about 85% of the Postgres tests with no failure; 2E was checked per file instead (all new tests pass, ruff and mypy clean, 379 unit/architecture tests, 297 UI tests). Run `bash scripts/verify.sh --slow --all` once on a machine with free memory before merging |
| Live providers | No live Twilio, Facebook or Pexels call has been made; adapters are proven against recorded responses in `tests/fixtures/providers/`. Needs task 26 plus `INTEGRATIONS_ENCRYPTION_KEY`, `PUBLIC_BASE_URL`, `PEXELS_API_KEY` (see `docs/operations/integrations.md`) |
| Assumptions to confirm | PRD §5.4.1 marks each judgment call "(assumed)": manager view hides margin and payables; approval rate and time-saved formulas; error rate = failed agent runs; Twilio Account SID as the webhook routing key; AI hands over for anything beyond price and stock |
| Impersonation | Platform-admin impersonation (PRD §14) is not built; it needs your rules for consent and expiry |
| Customer order drafts | Built 2026-10-13: the customer agent's `request_order` files a `customer_order` approval; approving posts the sale on credit (udhaar), finds or adds the customer by phone and confirms on WhatsApp. Proven against the scripted model only: try one real chat with `GEMINI_API_KEY` set |
| Legacy removal | The JSON-backed legacy routes, pages and Facebook manager (`/api/vendors`, `/api/marketing`, the Meta webhook, `app/(marketing)/dashboard/*`) are still mounted in development; the phase brief says replace-and-delete. Say when to remove them (it deletes about 20 test files with them) |
| Phase 3 left | Task 31 (a live hello-world call) needs a VAPI account and a number; task 90 (Meta Embedded Signup) needs a Meta app approved as a Tech Provider; the voice cost and per-turn latency fields of VAPI's end-of-call report, the keypad-to-person setting, silence timeout and noise filtering could not be confirmed from VAPI's docs and are listed as notes on the Voice page for you to set in the VAPI dashboard |
| Phase 3 built 2026-10-13 | Facebook comment replies (W-004 step 4, `/marketing/comments`, reuses the shop's posting approval mode), draft purchase orders (W-006, `/purchase-orders`, one per vendor beside the reorder message) and Urdu/RTL for the core screens (switcher, shell, tables, sign-in, dashboard, sales, inventory, customers, approvals). Phase 4 (billing) has no content in the PRD. Other screens stay English and fall back cleanly |
| Recipe failures | Owner decision 2026-10-13: a transient failure is retried (3 tries), a WhatsApp-sending recipe then falls back to filing its messages as approvals, and only if that fails does the run count as a failure; after three failures in a row the recipe stays on, raises an audit row and shows the banner (no auto-disable, no WhatsApp alert) |
| Defaults chosen while the owner was away (change on request) | Gemini Flash default with a 5 USD per shop per month AI cap (Q-003); Urdu limited to core screens (Q-004); platform-admin impersonation not built (needs consent and expiry rules); legacy JSON routes kept mounted (owner: keep for now); PRD §5.4.1 assumptions accepted by the owner |
| Urdu review | The Urdu strings in `frontend/lib/i18n/dictionary.ts` were written by the assistant: have a native reader check the retail wording before launch |
| Comment replies | Live Facebook comment read and reply calls were not made (recorded responses only); needs task 26 and a connected Page |

Open questions Q-001 to Q-006 are in PRD §0.4; resolve each before the task that depends on it.
