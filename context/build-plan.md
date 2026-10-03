# Build Plan

> Generated from `docs/prd/PRD.md` (v0.1.2, profile `production`) by Honey's Spec Harness. This is a living document: edit it freely; the PRD stays the source for scope.

## Core Principle

Full-page UI built with mock data first and verified visually before any logic is written; then functionality is wired step by step. Every feature is visible and testable before the next one starts. No invisible backend phases.

Every task cites its **feature ID** (F-, D-, R-, W-, I-xxx) or PRD section. Never invent a business field that is not in the PRD (PRD §5.3); record a change request first (PRD §25).

## Phase Map

| Phase | Scope | Exit Criteria |
| --- | --- | --- |
| 0 | Foundation: spec harness, CI (`verify.sh`), Supabase projects and roles (§3.8), Data API lockdown, Alembic baseline, tenancy tables, RLS, JWT claims, role dependencies, architecture tests, secret hygiene (remove committed DSN script) | CI green; two seeded tenants cannot read each other's rows through any API route (test passes); login returns tenant and role |
| 1 | Public demo launch: services moved from JSON to DB, inventory/sales/customers/udhaar with stock movements, sales chat agent, approvals center, agent activity log, home dashboard, app shell, landing page, demo seed | A new visitor signs up, adds a product, records a sale by chat, sees stock and dashboard update, approves a pending action; all within 15 minutes |
| 2 | Channels and onboarding: Twilio sandbox WhatsApp, unified inbox with AI/Human toggle, onboarding wizard, per-tenant encrypted integrations, Facebook connect + scheduler on DB, finance overview, vendors, daily briefing, platform admin | A tenant connects WhatsApp sandbox and Facebook in the wizard; a customer message gets an AI reply; an owner takes over; a scheduled post publishes |
| 3 | Voice, automation recipes, marketing insights, Meta Embedded Signup, Urdu/RTL, reorder workflow | A VAPI call is answered and logged; an owner enables the low-stock recipe and receives a drafted vendor message; embedded signup connects a number without developer tools |
| 4 | Commercial: pricing and billing, compliance items (Q-001, Q-005), React Flow builder (if trigger met), marketplace connectors | Chosen plan can be purchased and enforced; compliance checklist signed off |

## Production MVP and the Infrastructure Ladder

Phase 0 and Phase 1 are a **production MVP**: the smallest thing real users can rely on. Do not build for scale that has not arrived. Start at step 1 and move up only when the stated trigger is true and measured.

| Step | Setup | Move up when |
| --- | --- | --- |
| 1 | Free tiers: one managed host, one managed database, free error tracking and uptime check | Free-tier limits are reached or the uptime check shows repeated failures |
| 2 | Paid small instances, automated backups, staging environment, secrets in a manager | Paying users exist, or an outage would cost money |
| 3 | Autoscaling or multiple instances, read replicas or caching, structured logs and alerts | p95 latency or CPU stays above the PRD §17 target for a week |
| 4 | Multi-region, queues and workers, formal on-call and DR drills | A written availability or compliance requirement the lower steps cannot meet |

Anything the PRD wants beyond the MVP goes in a later phase with its trigger written next to it.

## Task Size Rule

A task must be verifiable in one fast-tier cycle (`bash scripts/verify.sh`, seconds). If its acceptance criteria need more than 6 checks, or any check needs the slow tier to prove the basic behaviour, split the task before starting it. `python3 scripts/check_plan.py` flags oversized tasks, duplicates, tasks without acceptance criteria, and a tracker that disagrees with this plan.

---

## Phase 0 — Foundation: spec harness, CI (`verify.sh`), Supabase projects and roles (§3.8), Data API lockdown, Alembic baseline, tenancy tables, RLS, JWT claims, role dependencies, architecture tests, secret hygiene (remove committed DSN script)

Exit gate: CI green; two seeded tenants cannot read each other's rows through any API route (test passes); login returns tenant and role

- [x] 00 Architecture Decision Record + sign-off — write `docs/adr/0001-stack-decision.md` from PRD §3.1 (stack, why, rejected alternatives)
  - Acceptance: `docs/adr/0001-stack-decision.md` exists and names the stack, the reasons and the rejected alternatives
  - Acceptance: the developer has signed it off (DONE: owner accepted it on 2026-10-03, recorded in the progress log; ADR status is accepted)
- [x] 01 Repo scaffold — folders per PRD §3.4 (`.`, `frontend`), package managers, `.env.example` with empty values
  - Acceptance: Every folder in PRD §3.4 exists and each part builds or runs an empty smoke test
  - Acceptance: `.env.example` lists every variable with an empty value; no real secret is committed (DONE: committed by the owner's instruction; verified byte-identical to docs/operations/env.example.proposed, whose names are enforced against docs/operations/env-vars.md by tests/architecture/test_env_docs.py)
- [ ] 02 CI/CD + verification — one workflow per lane (api, web) calling `scripts/verify.sh`; secret scan; dependency scan
  - Acceptance: Every lane has a workflow that calls `scripts/verify.sh`; a deliberately broken commit turns CI red
  - Acceptance: Secret scan and dependency scan run and pass on the clean tree
- [x] 03 Database foundation — PostgreSQL (Supabase), SQLite for local tests only + Alembic (async); first migration; naming and key conventions from PRD §12.2; migration check in `verify.sh`
  - Acceptance: The first migration applies to an empty database and the migration check in `verify.sh` passes
  - Acceptance: Table, column and key names follow PRD §12.2
- [x] 04 Authentication & authorization — login/refresh/logout, roles and permission matrix from PRD §14.2, enforced in the API
  - Acceptance: Login, refresh and logout work; a wrong password and an expired token are rejected
  - Acceptance: A user without the role gets 403 on a protected endpoint (test per role in PRD §14.2)
- [x] 05 Tenancy enforcement — central scoping filter, deny-by-default, cross-tenant access tests (PRD §3.5)
  - Acceptance: A test proves tenant A cannot read or write tenant B's rows
  - Acceptance: A request with no tenant context returns zero rows (deny by default)
- [x] 06 Audit infrastructure — audit rows for the actions in PRD §14.1, sensitive-field masking, test that each audited action writes a row
  - Acceptance: Each audited action in PRD §14.1 writes exactly one audit row (one test per action); §14.1 actions whose feature does not exist yet are listed with their phase in tests/pg/test_audit_actions.py (NOT_YET_BUILT) and get their test in the task that builds them
  - Acceptance: Sensitive fields are masked in the stored row
- [x] 07 UI foundation — design tokens, layout shell, the mandated form layout (PRD §5.1), reusable grid/form/status components, `context/ui-registry.md` started
  - Acceptance: Design tokens are the only source of colour, type and spacing; a lint or grep check finds no hard-coded values
  - Acceptance: The layout shell renders at mobile and desktop widths without horizontal scroll
- [x] 08 Vertical slice — the smallest end-to-end feature across every layer, to prove the pattern later tasks copy
  - Acceptance: The smallest feature works end to end across every layer with one automated test
  - Acceptance: `scripts/verify.sh` passes and the pattern is written down for later tasks to copy (docs/design/vertical-slice-pattern.md)
- [x] 09 Supabase projects (dev/staging/prod), database roles migrator/app_user/report_ro, pooler and direct connection strings, Data API lockdown — PRD §3.8
  - Acceptance: `docs/operations/supabase-setup.md` describes the dev/staging/prod setup, role provisioning and both connection strings
  - Acceptance: `app.cli.provision_db` creates migrator/app_user/report_ro and `app.cli.check_database` passes on a provisioned, migrated database (tests/pg/test_check_database.py)
  - Acceptance: `app.cli.check_database` passes against the real Supabase dev project (DONE 2026-10-03: project llwinbumuaqvypgnickd, Mumbai; roles provisioned, 4 migrations applied, every check passed; staging and prod projects are still to be created before launch)
- [x] 10 Tenancy schema and RLS baseline migration — tenants, memberships, tenant_id on every table, ENABLE+FORCE RLS, per-request app.tenant_id — PRD §3.5 and §3.8
  - Acceptance: Migrations create tenants and memberships and a tenant_id column on every business table (tests/architecture/test_data_conventions.py, tests/pg/test_schema_rules.py)
  - Acceptance: Every business table has ENABLE + FORCE row level security with a fail-closed policy keyed on app.tenant_id; migrations apply, match the models and round-trip (`verify.sh --slow --lane api-db`)
  - Acceptance: The API sets app.tenant_id per request transaction (tests/pg/test_rls.py: no context sees nothing, a tenant sees only its own rows)
- [x] 11 Architecture tests in CI — every table has tenant_id+RLS and no anon grants, every route has an authorization decision, agent tools take no tenant argument — PRD §3.7 and §19
  - Acceptance: Every table has tenant_id + forced RLS + a policy, and anon/authenticated have no grants (tests/pg/test_schema_rules.py)
  - Acceptance: Every route has an explicit authorization decision and only the expected routes are public (tests/architecture/test_authorization.py)
  - Acceptance: No agent tool takes a tenant/user/role argument (tests/architecture/test_agent_tools.py) and these tests run in the `api` CI lane (verify.sh with Docker)
- [ ] 12 Secret hygiene — remove default SECRET_KEY fallback in settings (fail fast when unset outside tests), .env.example complete, gitleaks passing — PRD RK-06
  - Acceptance: The API refuses to start without SECRET_KEY unless APP_ENV=test or ALLOW_INSECURE_DEV_SECRET is set outside production (tests/unit/test_settings_secret.py)
  - Acceptance: `.env.example` lists every variable in docs/operations/env-vars.md with an empty value
  - Acceptance: gitleaks passes on the full history in CI and locally
- [x] 13 Channel adapter interface (connect, send, receive, verify_webhook) with a fake adapter for tests — PRD §3.7 constraint 11
  - Acceptance: A ChannelAdapter interface with connect, send, receive and verify_webhook exists, with an in-memory fake that passes the interface check, idempotent sends and signature verification (tests/unit/test_audit_and_channels.py)
  - Acceptance: Provider SDKs and hard-coded provider hosts appear only in app/integrations, apart from a shrink-only legacy list (tests/architecture/test_provider_isolation.py)
- [x] 14 Agent tool layer inside the API process: tools call services with a tenant-scoped context, approvals via agent_actions — PRD §36.2-36.4
  - Acceptance: Agent tools receive tenant, user and role from a server-side ToolContext; the catalog rejects tools that take them as arguments or write without an approval level (tests/architecture/test_agent_tools.py)
  - Acceptance: Agent writes go through agent_actions: request, approve/reject, execute exactly once with the stored payload hash, expire, all audited and tenant-isolated (tests/pg/test_approvals.py, tests/pg/test_review_fixes.py)
- [x] 15 Rewrite the 19 quarantined tests (pytest markers legacy_port and live) against app.* and tenant-scoped data, then remove both markers from addopts
  - Acceptance: tests/ contains no `live` or `legacy_port` marker and pyproject.toml no longer excludes them; the default `pytest` run executes every former quarantined test
  - Acceptance: every former live-LLM test runs offline against a recording fake runner and asserts our behaviour; tests never write to app/data (tests/unit/conftest.py)
- [x] 16 Burn down the mypy legacy override list in pyproject.toml module by module until strict passes everywhere
  - Acceptance: `uv run mypy .` passes in strict mode with no ignore_errors override (tests/architecture/test_typing_policy.py enforces it)
  - Acceptance: the only mypy override is for a third-party package that ships no stubs
- [x] 17 Fix the double-prefixed v1 routes (/api/v1/api/...) and consolidate router mounting in app/api/routers
  - Acceptance: The done-condition for this task is written here and has an automated check
- [x] 18 Scaffold the web app with the chosen framework, strict TypeScript, lint and format [web-app pack]
  - Acceptance: Fresh clone installs and builds
  - Acceptance: lint and typecheck run in the fast tier
- [x] 19 Design tokens and layout shell [web-app pack]
  - Acceptance: Tokens are the only source of colour, type and spacing
  - Acceptance: shell renders at 360 px and 1440 px without horizontal scroll
- [x] 20 Authentication and role guard [web-app pack]
  - Acceptance: login, logout and silent token refresh work end to end against the real backend (e2e/auth.spec.ts, 8 tests via scripts/e2e_auth_stack.py)
  - Acceptance: a role without access sees the restricted view, and the API itself answers 401/403 (UI guard is a convenience)
  - Acceptance: the refresh token is an httpOnly cookie, never in JS or storage
- [ ] 21 Deploy a preview environment on a free tier [web-app pack]
  - Acceptance: Every pull request gets a preview URL
  - Acceptance: production deploy is one command
- [x] 22 Scaffold the API with lint, format, typecheck and a health endpoint [backend-api pack]
  - Acceptance: the service starts from a clean clone (DONE: scripts/check_clean_clone.sh clones HEAD, installs from the lockfiles, starts the API and the agent service, type-checks the web app)
  - Acceptance: the health endpoint answers (DONE: same script; tests/architecture/test_repo_layout.py)
- [x] 23 Database foundation and first migration [backend-api pack]
  - Acceptance: migration applies to an empty database (done in task 03: tests/pg/test_migration_04.py, alembic upgrade/check/round-trip in verify.sh api-db)
  - Acceptance: the migration check passes in the fast tier (alembic check runs in the api-db lane when Docker is up)
- [x] 24 Authentication and authorisation skeleton [backend-api pack]
  - Acceptance: login works (done in task 04: tests/pg/test_auth.py; web: e2e/auth.spec.ts)
  - Acceptance: a role without access gets 403, one test per role (tests/architecture/test_authorization.py, tests/pg/test_rls.py, e2e/auth.spec.ts)
- [x] 25 OpenAPI contract and generated client with a drift check [backend-api pack]
  - Acceptance: the drift check fails when an endpoint changes without regeneration (tests/architecture/test_openapi_contract.py; mutation-checked)
  - Acceptance: TypeScript client types are generated from contracts/openapi.json and checked byte for byte
- [ ] 26 Vendor accounts, sandbox access and credentials in the secret manager [integrations pack]
  - Acceptance: A sandbox call succeeds from the dev environment
  - Acceptance: no credential is in the repository
- [x] 27 Integration skill: install an upstream one or generate a project-local one [integrations pack]
  - Acceptance: the skill cites the vendor documentation URL and date (.claude/skills/integration-twilio-whatsapp/SKILL.md: two Twilio URLs, read 2026-10-03)
- [x] 28 Agent service skeleton, separate from the API, with no database credentials [agents pack]
  - Acceptance: The service starts
  - Acceptance: its environment contains no database variable (checked by a test)
- [ ] 29 Tool catalogue with schemas, permissions and a test per tool [agents pack]
  - Acceptance: every tool an agent can call (16 functions and the 2 delegation wrappers) is declared with permission and approval (DONE: app/agents/tools/manifest.py; an undeclared tool fails the suite)
  - Acceptance: each tool has its own unit tests (DONE: tests/unit/test_agent_tool_catalog.py)
  - Acceptance: authorize_call rejects unknown tools, roles below the minimum and approval-gated writes (DONE as a function, tested)
  - Acceptance: a forbidden call is rejected AT RUNTIME: the gate sits in the path of every agent tool call with a ToolContext (OPEN: needs phase 1, call sites do not pass a ToolContext yet; tools run raw through the SDK)
- [x] 30 Evaluation harness with a first golden set [agents pack]
  - Acceptance: the suite runs in the fast tier against recorded model responses (tests/unit/evals; no network or key; 12 golden cases)
  - Acceptance: the harness catches regressions: removing a tool from an agent fails a case; a tool that crashes, a customer-facing tool leaking stock, or an injected invented tool fails a case (mutation-checked). Limit: replayed turns are hand-recorded, so a prompt change alone does not fail a case; re-record against the live model for that.
Each task: confirm the acceptance criteria (`/architect` turns them into failing tests first), then build, then `bash scripts/verify.sh`, then `/review`.

## Phase 1 — Public demo launch: services moved from JSON to DB, inventory/sales/customers/udhaar with stock movements, sales chat agent, approvals center, agent activity log, home dashboard, app shell, landing page, demo seed

Exit gate: A new visitor signs up, adds a product, records a sale by chat, sees stock and dashboard update, approves a pending action; all within 15 minutes

- [ ] 34 Sign in — F-001 (Auth; master; P0; roles: public)
  - Acceptance: A user with one of the roles (public) can complete the Auth flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-001 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 35 Create account and shop — F-002 (Auth; master; P0; roles: public)
  - Acceptance: A user with one of the roles (public) can complete the Auth flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-002 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 36 Home dashboard — F-004 (Overview; report; P0; roles: owner, manager, staff)
  - Acceptance: A user with one of the roles (owner, manager, staff) can complete the Overview flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-004 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 37 Sales chat (agent) — F-006 (Sales; transaction; P0; roles: owner, manager, staff)
  - Acceptance: A user with one of the roles (owner, manager, staff) can complete the Sales flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-006 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 38 New sale — F-007 (Sales; transaction; P0; roles: owner, manager, staff)
  - Acceptance: A user with one of the roles (owner, manager, staff) can complete the Sales flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-007 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 39 Orders list and detail — F-008 (Sales; list; P0; roles: owner, manager, staff)
  - Acceptance: A user with one of the roles (owner, manager, staff) can complete the Sales flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-008 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 40 Customers and udhaar ledger — F-009 (Sales; master; P0; roles: owner, manager)
  - Acceptance: A user with one of the roles (owner, manager) can complete the Sales flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-009 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 41 Products and stock — F-010 (Inventory; master; P0; roles: owner, manager (staff view))
  - Acceptance: A user with one of the roles (owner, manager (staff view)) can complete the Inventory flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-010 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 42 Marketing studio — F-014 (Marketing; transaction; P0; roles: owner, manager)
  - Acceptance: A user with one of the roles (owner, manager) can complete the Marketing flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-014 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 43 Team and roles — F-019 (Settings; master; P0; roles: owner)
  - Acceptance: A user with one of the roles (owner) can complete the Settings flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-019 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 44 Approvals center — F-021 (Overview; transaction; P0; roles: owner, manager)
  - Acceptance: A user with one of the roles (owner, manager) can complete the Overview flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-021 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 45 Agent activity log — F-022 (Overview; list; P0; roles: owner, manager)
  - Acceptance: A user with one of the roles (owner, manager) can complete the Overview flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-022 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 46 Public landing page — F-026 (Public; page; P0; roles: public)
  - Acceptance: A user with one of the roles (public) can complete the Public flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-026 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 47 Public live demo — F-027 (Public; page; P1; roles: public)
  - Acceptance: A user with one of the roles (public) can complete the Public flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-027 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 48 Owner home dashboard — D-001 (role: owner, manager; KPIs: Today's sales, Profit today, Orders today, Low-stock items, Unpaid udhaar, Approvals waiting, AI briefing)
  - Acceptance: Each KPI (Today's sales, Profit today, Orders today, Low-stock items, Unpaid udhaar, Approvals waiting, AI briefing) matches a hand-computed value on a seeded dataset
  - Acceptance: Only role owner, manager can open it; an empty dataset shows an empty state, not an error
- [ ] 49 Integration: LLM provider (Gemini or OpenAI) — I-005 (out; REST)
  - Acceptance: A contract test against a recorded or sandbox response proves the happy path
  - Acceptance: A timeout, an error response and a duplicate delivery are each handled by a test
- [ ] 50 Integration: Supabase Storage — I-007 (out; REST)
  - Acceptance: A contract test against a recorded or sandbox response proves the happy path
  - Acceptance: A timeout, an error response and a duplicate delivery are each handled by a test
- [ ] 51 First vertical slice through the UI, API and database [web-app pack]
  - Acceptance: The slice works end to end with one automated test
  - Acceptance: the pattern is written down
- [ ] 52 Form pattern: validation, error display, double-submit protection [web-app pack]
  - Acceptance: Server and client reject the same invalid inputs
  - Acceptance: a second click does not create a second record
- [ ] 53 Accessibility and performance gates [web-app pack]
  - Acceptance: axe finds no serious issue on the slice
  - Acceptance: the performance budget lane passes
- [ ] 54 End-to-end smoke test of the critical flow [web-app pack]
  - Acceptance: One browser test signs in and completes the main task
- [ ] 55 First vertical slice: one resource with create, read, update, delete [backend-api pack]
  - Acceptance: Validation, authorisation and pagination are tested
  - Acceptance: error format matches the contract
- [ ] 56 Tenant or branch scoping (if the PRD has it) [backend-api pack]
  - Acceptance: A test proves tenant A cannot read or write tenant B
  - Acceptance: no tenant context returns nothing
- [ ] 57 Structured logging, request ids and error reporting [backend-api pack]
  - Acceptance: A failed request can be traced from the response id to the log line
- [ ] 58 Backups and one timed restore [backend-api pack]
  - Acceptance: The restore completes within the PRD recovery target
- [ ] 59 Authentication to the vendor (OAuth or key) with token refresh [integrations pack]
  - Acceptance: Expired token refreshes without user action
  - Acceptance: revoked token produces a clear re-consent path
- [ ] 60 One end-to-end integration flow against the sandbox [integrations pack]
  - Acceptance: Contract test passes against a recorded response
  - Acceptance: timeout, 429 and error response each have a test
- [ ] 61 Webhook endpoint with signature verification and idempotency [integrations pack]
  - Acceptance: A replayed event is ignored
  - Acceptance: a bad signature is rejected
- [ ] 62 Failure handling and alerting [integrations pack]
  - Acceptance: A forced vendor outage shows the defined degraded behaviour and raises an alert
- [ ] 63 First agent flow end to end with human approval on side effects [agents pack]
  - Acceptance: An approved action runs
  - Acceptance: a rejected action does not
  - Acceptance: the trace shows both
- [ ] 64 Run caps, spend cap and kill switch [agents pack]
  - Acceptance: Exceeding a cap stops the run with a clear message
  - Acceptance: the kill switch works without a deploy
- [ ] 65 Tracing with redaction [agents pack]
  - Acceptance: A trace of a run contains no personal data from the test fixtures
- [ ] 66 One complete call flow with confirmation of captured data [voice-agents pack]
  - Acceptance: Names, numbers and dates are read back
  - Acceptance: wrong data can be corrected by the caller
- [ ] 67 Barge-in, silence and noise handling [voice-agents pack]
  - Acceptance: Each behaviour has a recorded test case that passes
- [ ] 68 Human handoff and keypad fallback [voice-agents pack]
  - Acceptance: A forced trigger transfers the call with context
- [ ] 69 Consent notice, redaction and retention [voice-agents pack]
  - Acceptance: The notice plays
  - Acceptance: a transcript in the test set contains no personal data after redaction

Each task: confirm the acceptance criteria (`/architect` turns them into failing tests first), then build, then `bash scripts/verify.sh`, then `/review`.

## Phase 2 — Channels and onboarding: Twilio sandbox WhatsApp, unified inbox with AI/Human toggle, onboarding wizard, per-tenant encrypted integrations, Facebook connect + scheduler on DB, finance overview, vendors, daily briefing, platform admin

Exit gate: A tenant connects WhatsApp sandbox and Facebook in the wizard; a customer message gets an AI reply; an owner takes over; a scheduled post publishes

- [ ] 70 Onboarding wizard — F-003 (Onboarding; transaction; P0; roles: owner)
  - Acceptance: A user with one of the roles (owner) can complete the Onboarding flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-003 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 71 Unified inbox — F-005 (Inbox; transaction; P0; roles: owner, manager, staff)
  - Acceptance: A user with one of the roles (owner, manager, staff) can complete the Inbox flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-005 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 72 Stock movements — F-011 (Inventory; list; P1; roles: owner, manager)
  - Acceptance: A user with one of the roles (owner, manager) can complete the Inventory flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-011 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 73 Vendors and payables — F-012 (Inventory; master; P1; roles: owner, manager)
  - Acceptance: A user with one of the roles (owner, manager) can complete the Inventory flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-012 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 74 Finance overview and ledger — F-013 (Finance; report; P1; roles: owner (manager view))
  - Acceptance: A user with one of the roles (owner (manager view)) can complete the Finance flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-013 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 75 Marketing schedule — F-015 (Marketing; settings; P1; roles: owner, manager)
  - Acceptance: A user with one of the roles (owner, manager) can complete the Marketing flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-015 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 76 Marketing activity — F-016 (Marketing; list; P1; roles: owner, manager)
  - Acceptance: A user with one of the roles (owner, manager) can complete the Marketing flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-016 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 77 Integrations (WhatsApp, Facebook, VAPI) — F-018 (Settings; settings; P0; roles: owner)
  - Acceptance: A user with one of the roles (owner) can complete the Settings flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-018 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 78 Shop profile and settings — F-020 (Settings; settings; P1; roles: owner)
  - Acceptance: A user with one of the roles (owner) can complete the Settings flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-020 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 79 Platform admin: tenants — F-025 (Platform; master; P1; roles: platform admin)
  - Acceptance: A user with one of the roles (platform admin) can complete the Platform flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-025 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 80 Finance dashboard — D-002 (role: owner; KPIs: Revenue trend, Gross margin, Receivables aging, Vendor payables, Cash vs udhaar split)
  - Acceptance: Each KPI (Revenue trend, Gross margin, Receivables aging, Vendor payables, Cash vs udhaar split) matches a hand-computed value on a seeded dataset
  - Acceptance: Only role owner can open it; an empty dataset shows an empty state, not an error
- [ ] 81 Agent command center dashboard — D-003 (role: owner, manager; KPIs: Agent runs today, Approval rate, Failed runs, AI spend vs cap, Time saved estimate)
  - Acceptance: Each KPI (Agent runs today, Approval rate, Failed runs, AI spend vs cap, Time saved estimate) matches a hand-computed value on a seeded dataset
  - Acceptance: Only role owner, manager can open it; an empty dataset shows an empty state, not an error
- [ ] 82 Platform overview dashboard — D-004 (role: platform admin; KPIs: Tenants, Active tenants (7 d), Messages/day, AI spend, Error rate)
  - Acceptance: Each KPI (Tenants, Active tenants (7 d), Messages/day, AI spend, Error rate) matches a hand-computed value on a seeded dataset
  - Acceptance: Only role platform admin can open it; an empty dataset shows an empty state, not an error
- [ ] 83 Integration: Twilio WhatsApp (sandbox, later production sender) — I-001 (both; REST + webhook)
  - Acceptance: A contract test against a recorded or sandbox response proves the happy path
  - Acceptance: A timeout, an error response and a duplicate delivery are each handled by a test
- [ ] 84 Integration: Facebook/Instagram Graph API — I-003 (both; REST)
  - Acceptance: A contract test against a recorded or sandbox response proves the happy path
  - Acceptance: A timeout, an error response and a duplicate delivery are each handled by a test
- [ ] 85 Integration: Pexels images — I-006 (out; REST)
  - Acceptance: A contract test against a recorded or sandbox response proves the happy path
  - Acceptance: A timeout, an error response and a duplicate delivery are each handled by a test

Each task: confirm the acceptance criteria (`/architect` turns them into failing tests first), then build, then `bash scripts/verify.sh`, then `/review`.

## Phase 3 — Voice, automation recipes, marketing insights, Meta Embedded Signup, Urdu/RTL, reorder workflow

Exit gate: A VAPI call is answered and logged; an owner enables the low-stock recipe and receives a drafted vendor message; embedded signup connects a number without developer tools

- [ ] 31 Channel setup (number or WebRTC room) and a hello-world call [voice-agents pack, moved from Phase 0 by the owner]
  - Acceptance: A test call connects and the agent answers
- [ ] 32 Latency and cost instrumentation per turn [voice-agents pack, moved from Phase 0 by the owner]
  - Acceptance: Each call logs per-turn latency and cost
  - Acceptance: a cap stops runaway calls
- [ ] 33 Evaluation set of recorded calls [voice-agents pack, moved from Phase 0 by the owner]
  - Acceptance: The set replays offline and reports task success
- [ ] 86 Marketing insights — F-017 (Marketing; report; P2; roles: owner, manager)
  - Acceptance: A user with one of the roles (owner, manager) can complete the Marketing flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-017 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 87 Voice calls and agent settings — F-023 (Voice; list/settings; P1; roles: owner (manager view))
  - Acceptance: A user with one of the roles (owner (manager view)) can complete the Voice flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-023 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 88 Automation recipes — F-024 (Automations; settings; P1; roles: owner, manager)
  - Acceptance: A user with one of the roles (owner, manager) can complete the Automations flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-024 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 89 System logs — F-028 (Platform; list; P2; roles: platform admin)
  - Acceptance: A user with one of the roles (platform admin) can complete the Platform flow; a user without them gets 403
  - Acceptance: Validation and required fields match the field spec for F-028 in PRD §5.3 (one test per rule)
  - Acceptance: One end-to-end test drives the form and checks what was stored
- [ ] 90 Integration: Meta WhatsApp Cloud API (Embedded Signup) — I-002 (both; REST + webhook)
  - Acceptance: A contract test against a recorded or sandbox response proves the happy path
  - Acceptance: A timeout, an error response and a duplicate delivery are each handled by a test
- [ ] 91 Integration: VAPI voice — I-004 (both; REST + webhook)
  - Acceptance: A contract test against a recorded or sandbox response proves the happy path
  - Acceptance: A timeout, an error response and a duplicate delivery are each handled by a test

Each task: confirm the acceptance criteria (`/architect` turns them into failing tests first), then build, then `bash scripts/verify.sh`, then `/review`.

## Phase 4 — Commercial: pricing and billing, compliance items (Q-001, Q-005), React Flow builder (if trigger met), marketplace connectors

Exit gate: Chosen plan can be purchased and enforced; compliance checklist signed off

- [ ] 92 (no forms, dashboards or integrations are assigned to this phase in the PRD registers — assign them in PRD §5.2 / §7 / §13.3 or add tasks here)
  - Acceptance: Assign registered items to this phase, then regenerate

Each task: confirm the acceptance criteria (`/architect` turns them into failing tests first), then build, then `bash scripts/verify.sh`, then `/review`.

## Pack Checklists — answer before Phase 1 exits

Each item becomes a PRD requirement and a candidate acceptance test. Tick it here when the PRD answers it.

- [ ] C-WA-01 Every protected page and every API route checks the user and role on the server, not only in the UI; one test per role proves a 403. (web-app)
- [ ] C-WA-02 Session expiry, refresh and logout are defined and tested, including what the user sees when a session ends mid-form. (web-app)
- [ ] C-WA-03 All input is validated on the client for feedback and again on the server for safety; the same rules are shared, not copied. (web-app)
- [ ] C-WA-04 Every list and screen has designed loading, empty and error states. (web-app)
- [ ] C-WA-05 Forms cannot be double-submitted; a repeated submit is safe. (web-app)
- [ ] C-WA-06 Keyboard-only use works on every page: logical focus order, visible focus, no keyboard traps; forms have labels and linked error messages. (web-app)
- [ ] C-WA-07 Layouts work at 360 px, tablet and desktop widths without horizontal scroll. (web-app)
- [ ] C-WA-08 Every page has a title, a description, one h1 and a canonical URL; public pages appear in the sitemap; private pages are noindex. (web-app)
- [ ] C-WA-09 Security headers and a content security policy are set; cookies are HttpOnly, Secure and SameSite; state-changing requests are protected against CSRF. (web-app)
- [ ] C-WA-10 Rate limiting protects sign-in, password reset and any public form. (web-app)
- [ ] C-WA-11 No secret reaches the browser bundle; environment files are separated per environment and `.env.example` lists every variable. (web-app)
- [ ] C-WA-12 Image, font and JavaScript budgets are written down as numbers and checked in a lane. (web-app)
- [ ] C-WA-13 Errors are captured with a request or session id and without personal data. (web-app)
- [ ] C-WA-14 404 and 500 pages exist and keep the navigation usable. (web-app)
- [ ] C-BA-01 Every endpoint validates input and rejects unknown or oversized fields with a consistent error format. (backend-api)
- [ ] C-BA-02 Authorisation is tested per endpoint and per role, including the case of a valid user reading another user's or tenant's data. (backend-api)
- [ ] C-BA-03 List endpoints are paginated with a hard maximum page size and a stable sort. (backend-api)
- [ ] C-BA-04 Requests that may be retried (payments, orders, imports) are idempotent or carry an idempotency key. (backend-api)
- [ ] C-BA-05 Migrations apply to an empty database and to a copy of production data, and each has a tested way back or a stated reason it has none. (backend-api)
- [ ] C-BA-06 Filtered and joined columns are indexed; the slowest queries are measured with realistic data volume. (backend-api)
- [ ] C-BA-07 Transaction boundaries are explicit; a failure half-way leaves no partial records. (backend-api)
- [ ] C-BA-08 Every outbound call has a timeout and a defined failure behaviour. (backend-api)
- [ ] C-BA-09 Health and readiness endpoints exist and reflect real dependencies. (backend-api)
- [ ] C-BA-10 Logs are structured, carry a request id, and never contain secrets or personal data. (backend-api)
- [ ] C-BA-11 CORS is an allowlist; secrets come from the environment or a secret manager, never the repository. (backend-api)
- [ ] C-BA-12 The OpenAPI document matches the running service; the generated client is checked for drift. (backend-api)
- [ ] C-BA-13 Rate limits protect authentication and expensive endpoints. (backend-api)
- [ ] C-BA-14 Personal data is identified, minimised, and has a stated retention and deletion rule. (backend-api)
- [ ] C-BA-15 A restore from backup has been performed once and timed. (backend-api)
- [ ] C-I-01 A sandbox or recorded-fixture suite proves the happy path for every integration without touching production. (integrations)
- [ ] C-I-02 Tokens refresh automatically; revocation and re-consent are handled and tested. (integrations)
- [ ] C-I-03 Requested scopes are the minimum needed and each is justified in the PRD. (integrations)
- [ ] C-I-04 Incoming webhooks verify the signature, reject replays, and are idempotent. (integrations)
- [ ] C-I-05 Outgoing calls use timeouts, retries with backoff and jitter, and a dead-letter or failure record after the last retry. (integrations)
- [ ] C-I-06 Vendor rate limits are respected, and a 429 response is handled. (integrations)
- [ ] C-I-07 Vendor error codes are mapped to our error format; raw vendor errors never reach users. (integrations)
- [ ] C-I-08 The vendor is mocked in CI so builds do not depend on the vendor being up. (integrations)
- [ ] C-I-09 A data-mapping table lists each field, its source, its destination and any transformation. (integrations)
- [ ] C-I-10 Credentials are stored in a secret manager and have a rotation procedure. (integrations)
- [ ] C-I-11 The vendor API version is pinned and a change-notice source is subscribed to. (integrations)
- [ ] C-I-12 Failures are monitored and alert a human when the failure rate crosses the stated threshold. (integrations)
- [ ] C-I-13 The vendor's terms and data-processing obligations are read and any personal-data transfer is recorded. (integrations)
- [ ] C-A-01 Every tool has the least privilege it needs, and a forbidden call is rejected, not merely discouraged in the prompt. (agents)
- [ ] C-A-02 The agent service has no database credentials; it reaches data only through the API with the caller's identity. (agents)
- [ ] C-A-03 Text returned by tools, web pages and documents is treated as untrusted and cannot change the agent's instructions or permissions. (agents)
- [ ] C-A-04 Each run has a maximum number of steps, tokens and wall-clock time, and ends with a clear message when a cap is hit. (agents)
- [ ] C-A-05 Destructive and customer-visible actions require explicit human approval until evaluations justify removing it. (agents)
- [ ] C-A-06 A golden-case evaluation suite runs in CI; a regression fails the build. (agents)
- [ ] C-A-07 Structured outputs are validated against a schema; invalid output is retried once and then escalated. (agents)
- [ ] C-A-08 Traces record prompts, tool calls and results with personal data redacted, and are kept for a stated period. (agents)
- [ ] C-A-09 Model errors, rate limits and timeouts have a defined fallback (retry, smaller model, human). (agents)
- [ ] C-A-10 Prompts and tool descriptions are versioned in the repository and changes go through review. (agents)
- [ ] C-A-11 A per-day spend cap exists with an alert and an automatic stop. (agents)
- [ ] C-A-12 A kill switch disables the agent without a deploy. (agents)
- [ ] C-A-13 Personal data sent to the model provider is identified and covered by the provider terms in use. (agents)
- [ ] C-VA-01 Per-turn latency is measured and the 95th percentile is within the stated target. (voice-agents)
- [ ] C-VA-02 Barge-in works: the agent stops speaking when the caller starts. (voice-agents)
- [ ] C-VA-03 Silence, background noise and cross-talk have defined behaviour (re-prompt, then handoff). (voice-agents)
- [ ] C-VA-04 Recording and consent notices follow the law of every target jurisdiction, and the consent is logged. (voice-agents)
- [ ] C-VA-05 Personal data in transcripts and logs is redacted, with a stated retention period. (voice-agents)
- [ ] C-VA-06 Names, numbers, dates and addresses are read back and confirmed before any action depends on them. (voice-agents)
- [ ] C-VA-07 A human handoff and a keypad (DTMF) fallback exist and are tested. (voice-agents)
- [ ] C-VA-08 Tool calls with side effects need explicit confirmation from the caller. (voice-agents)
- [ ] C-VA-09 Cost per minute is measured; a daily spend cap and concurrency limit exist. (voice-agents)
- [ ] C-VA-10 Accents, noisy audio and each supported language have recorded test calls in the evaluation set. (voice-agents)
- [ ] C-VA-11 Provider outage degrades gracefully: a clear message and a way to reach a person. (voice-agents)
- [ ] C-VA-12 A set of real, anonymised calls is replayed in CI or nightly to catch regressions. (voice-agents)

## Deferred — with the trigger that brings each back

| Item | Trigger | Pack |
| --- | --- | --- |
| CDN and caching tuning | p95 time to first byte is above the PRD target for a week | web-app |
| Internationalisation | A second language or market is committed | web-app |
| Feature flags and A/B testing | Two or more releases are blocked by the same unfinished feature, or a decision needs measured data | web-app |
| Offline or installable app (PWA) | Users must work without connectivity, as stated in the PRD | web-app |
| Background job queue | A task takes longer than a request should wait, or must retry independently of the request | backend-api |
| Caching layer (Redis or similar) | A measured query or endpoint exceeds its target after indexing | backend-api |
| Search engine | Database search cannot meet the PRD response target at real data volume | backend-api |
| Read replicas | Reads saturate the primary after caching | backend-api |
| Microservices split | Two teams cannot deploy independently because of the monolith | backend-api |
| Bulk sync and backfill jobs | Initial data volume cannot be handled by the incremental path | integrations |
| Second vendor in the same category | A customer requires it; extract a vendor-neutral interface then, not before | integrations |
| Real-time sync instead of polling | Polling latency breaks a stated user need | integrations |
| Long-term memory | Users repeat context across sessions and a retrieval test shows it improves outcomes | agents |
| Multiple cooperating agents | A single agent fails the golden set because of context length or role conflict | agents |
| Fine-tuning | Prompting and retrieval cannot reach the target on the golden set | agents |
| Autonomous execution without approval | The golden set shows a stated success rate over a stated number of runs | agents |
| Custom or cloned voice | Brand requires it and the licence and consent for the voice are in hand | voice-agents |
| Outbound campaigns | Inbound flow meets its success target and legal review of outbound calling is done | voice-agents |
| Multiple languages beyond the first | A second language is committed and has its own recorded evaluation set | voice-agents |
| Sentiment analytics | Handoff triggers prove insufficient in the evaluation set | voice-agents |

