# Project Overview

> Generated from `docs/prd/PRD.md` (v0.1.2, profile `production`) by Honey's Spec Harness. This is a living document: edit it freely; the PRD stays the source for scope.

## About the Project

BazaarFlow is an AI back-office for small retailers. A shopkeeper runs inventory, sales, vendor and customer finance, social media marketing and customer support by chatting (text or voice) with specialized agents over WhatsApp and a web dashboard, instead of filling forms in an ERP. It automates daily retail tasks: recording sales, tracking stock, scheduling Facebook campaigns and replying to comments, answering customer messages, and handling support calls through a voice agent.

The v1 application (built eight months ago) proves the core loop: FastAPI services, four OpenAI-Agents-SDK agents, Facebook scheduler, WhatsApp webhook and a VAPI support line *(observed)*. It is single-tenant, stores part of its data in JSON files, reads credentials from global environment variables, and has a generic UI. This PRD defines the v2 product: multi-tenant on Supabase Postgres, role-based, audited, with per-tenant integrations, a Twilio-sandbox WhatsApp demo path, an approval-driven agent layer and a redesigned application shell.

Delivery profile is **production** (real tenants must be isolated and auditable), with launch scoped as a free public demo. **Positioning:** BazaarFlow is a conversational AI back-office for small retailers. It covers the ERP essentials (inventory, sales, customer credit, vendors, basic finance) but is not a full ERP: no general ledger, payroll or multi-warehouse. The shopkeeper operates it by chat and voice instead of forms. What makes it different from general personal agents (OpenClaw, Hermes) is that it is vertical: retail data model, retail agents, guided connection of WhatsApp/Facebook for non-technical owners, and an approval center that makes AI actions safe.

## Product Objectives

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

## Modules & Primary Screens

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

## Feature Priority

| Priority | Meaning | Items |
| --- | --- | --- |
| P0 — Mandatory MVP | Cannot ship without | Tenancy + RLS, auth + roles, DB-backed inventory/sales/customers, sales chat agent, approvals, audit, app shell + dashboard, onboarding, landing page |
| P1 — Commercial release | Needed to charge money | Twilio/Meta WhatsApp inbox, Facebook scheduler on DB, finance overview, vendors, integrations UI, daily briefing, platform admin |
| P2 — Expansion | Growth features | Marketing insights, voice agent settings, automation recipes, reports export, Urdu/RTL, voice-note orders (speech-to-text on WhatsApp audio), photo-to-product add (image → draft product), walkthrough videos for connecting WhatsApp/Facebook |
| P3 — Differentiation | Moat | React Flow builder, MCP server for tenant data, Instagram, marketplace connectors, anomaly detection |

## Non-Negotiable Architectural Constraints

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

## Deployment Models

Local (Docker Compose + SQLite or local Postgres), CI (ephemeral Postgres), staging (Supabase branch/project), production (Supabase project). Configuration via Pydantic `Settings` from environment variables; `.env.example` lists keys with empty values; secrets live in the host's secret store. Per-tenant credentials are stored encrypted in `tenant_integrations` (envelope encryption with an app key), never in env vars or logs.

## Definition of Done

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

