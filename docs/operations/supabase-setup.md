# Supabase setup runbook (PRD §3.8)

BazaarFlow uses Supabase only as managed Postgres (plus Storage later). The FastAPI API is the only
client. Do this once per project (`dev`, `staging`, `prod`), in this order.

## 1. Create the project
- Region: the closest to Pakistan (Singapore or Mumbai). It cannot be changed later.
- Keep the database password in your password manager, not in the repo.
- The free tier pauses after inactivity. Upgrade the demo/prod project to Pro before the public launch (RK-07).

## 2. Provision the three roles (once, before the first migration)
Use the **session pooler** connection string (port 5432, host `aws-0-<region>.pooler.supabase.com`, user
`postgres.<project-ref>`). Do not use the "Direct connection" host `db.<ref>.supabase.co`: Supabase serves it over IPv6
only on the free tier, and many home and office networks (including many in Pakistan) have no IPv6, so it fails to
connect. The session pooler works over IPv4 and behaves like a direct connection for DDL and migrations.

```bash
export MIGRATOR_PASSWORD=...  APP_USER_PASSWORD=...  REPORT_RO_PASSWORD=...   # generate long random values
uv run python -m app.cli.provision_db --admin-url "postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres"
```

This creates `migrator` (owns the schema, used only by Alembic), `app_user` (API runtime, `NOBYPASSRLS`,
no DDL) and `report_ro` (read-only), and sets default privileges so tables created by `migrator` are
usable by the other two. Re-running it is safe and re-sets the passwords.

## 3. Environment variables (names only; values live in the host's secret store)
| Variable | Value |
| --- | --- |
| `DATABASE_URL` | **pooler**, transaction mode (port 6543), user `app_user.<project-ref>`, `postgresql+asyncpg://` |
| `DATABASE_URL_MIGRATIONS` | **session pooler** (port 5432), user `migrator.<project-ref>`, `postgresql+asyncpg://` |
| `SECRET_KEY` | long random string; the API refuses to start in `production`/`staging` without it |
| `APP_ENV` | `production` (or `staging`) |

The app already disables asyncpg's prepared-statement cache, which the transaction pooler requires.

## 4. Run the migrations
```bash
DATABASE_URL_MIGRATIONS="postgresql+asyncpg://migrator.<ref>:...@aws-0-<region>.pooler.supabase.com:5432/postgres" uv run alembic upgrade head
```
The second migration enables and forces row-level security on every business table and revokes every grant
from Supabase's `anon` and `authenticated` roles (the Data API roles). Never edit the schema in the Supabase
dashboard: `alembic check` in CI will flag the drift.

## 5. Verify the lockdown (automated)
```bash
uv run python -m app.cli.check_database --admin-url "postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres"
```
It checks the three roles (no superuser / bypassrls), that every business table has ENABLE + FORCE row level
security and a policy, that `anon` and `authenticated` have no privileges, and that `audit_logs` is append-only.
It exits 1 and lists every problem otherwise. Also run Supabase's security advisor and fix any finding before
launch; in project settings, disable the Data API if the option is available (the app never uses it).

## 6. Seed the demo tenant (optional)
```bash
DEMO_USER_PASSWORD=... uv run python -m app.cli.seed
```

## 7. Prove the whole stack on the real project (task 09)
With `DATABASE_URL`, `DATABASE_URL_MIGRATIONS`, `SECRET_KEY` and `DEMO_USER_PASSWORD` in `.env`:
```bash
uv run python -m app.cli.check_database --admin-url "<session pooler URL of the postgres user>"   # you run this one
uv run python scripts/e2e_auth_stack.py --supabase
```
The second command migrates with the migrator role, seeds the demo tenant (owner, manager and staff logins), starts the
API on the runtime `app_user` URL and runs the browser tests (login, logout, expiry, role pages) against Supabase. It
creates nothing locally. The automated test suite keeps using a throwaway Docker Postgres on purpose: those tests
create and destroy roles and fake accounts and try to break row-level security, which must never run against a real
project.
