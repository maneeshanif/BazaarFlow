# Progress Log

Append-only history. Never edit or delete a line. The short status lives in `progress-tracker.md`; this file is where finished work, decisions and rulings are recorded, one dated line each, newest at the bottom. Agents read the tracker every session and this log only when they need history.

<!-- one line per event: YYYY-MM-DD — task NN done | decision | ruling — what and why -->

## 2026-10-02 — Phase 0 tenancy foundation
- New models: tenants, memberships, tenant_integrations, audit_logs; tenant_id (native UUID) on every business table; v1 `vendors` (the shop) became `tenants`, `vendors` is now suppliers.
- Migrations 20261002_01 (baseline) and 20261002_02 (RLS: ENABLE+FORCE, fail-closed `app_tenant_id()`, own-membership policy, append-only audit_logs, anon/authenticated lockdown). Apply, `alembic check` and round-trip pass.
- `app/core/tenancy.py` (transaction-local `set_config`), `app/core/auth.py` (JWT principal, `require_role`, `public_route`, `require_platform_admin`), `app/cli/provision_db.py` (migrator/app_user/report_ro).
- Auth: register (user+tenant+owner membership+audit in one transaction), login (tenant claims), me, switch-tenant. Not done yet: refresh, logout, login lockout, role re-check on every request (role comes from the 30-minute token).
- Customers API is the vertical slice (`/api/v1/customers/`).
- Tests: 26 Postgres tests (testcontainers, as `app_user`), route-authorization architecture test, schema-rule tests; mutation-checked by removing RLS from one table.
- Caveat: legacy JSON-backed routes (inventory, sales, marketing, vendors, chat, logs) now require a role but are NOT tenant-isolated until the Phase 1 DB move.
- Seed CLI rewritten for tenancy; export CLI needs `--tenant-id`.
- Real bugs fixed on the way: alembic/__init__.py shadowed the alembic package; FastMCP constructor args; downgrade left an enum behind.

## 2026-10-02 — Phase 0 remainder
- Auth: refresh tokens (hashed, rotating, reuse detection revokes all sessions), logout (idempotent), login lockout (5 failures / 15 min, also for unknown e-mails), membership re-check on every tenant-scoped request so a demoted or removed member loses access immediately.
- Audit: `app/core/audit.py` (`record_audit`, `mask_sensitive`); every auth event, customer write and agent action writes exactly one row. New audited actions are added as modules land.
- Agent layer: `ToolContext` (tenant/user/role from the server), tool catalog that rejects tenant/user/role arguments and un-gated write tools at import time, approvals service (`agent_actions`: request, decide, execute with payload-hash check, expiry).
- `app/integrations/channels.py`: channel adapter Protocol, registry, FakeChannelAdapter (Twilio arrives in Phase 2).
- Migration 20261002_03: refresh_tokens, login_attempts, agent_actions (+RLS).
- Routes: only auth and customers live under /api/v1; the legacy routers keep /api/... (the double prefix is gone, guarded by a test).
- Plan: tasks 15 and 16 (port quarantined tests, burn down mypy list) re-scoped into Phase 1 as tasks 93-94, to be done per module as it moves to the DB; porting them against JSON services that are being replaced would be wasted work.
- Tests: 77 fast + 41 real-Postgres; mutation-checked the membership re-check and the payload-hash check.
- Still open in Phase 0: 00 ADR sign-off (owner), 09 Supabase projects (credentials), 12 .env.example (agent cannot read it; keys listed in docs/operations/env-vars.md), 01/02 need a CI run on GitHub to confirm.
