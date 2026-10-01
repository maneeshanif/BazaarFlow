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
