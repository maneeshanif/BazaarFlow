# Supabase setup runbook (PRD §3.8)

BazaarFlow uses Supabase only as managed Postgres (plus Storage later). The FastAPI API is the only
client. Do this once per project (`dev`, `staging`, `prod`), in this order.

## 1. Create the project
- Region: the closest to Pakistan (Singapore or Mumbai). It cannot be changed later.
- Keep the database password in your password manager, not in the repo.
- The free tier pauses after inactivity. Upgrade the demo/prod project to Pro before the public launch (RK-07).

## 2. Provision the three roles (once, before the first migration)
Use the **direct** connection string (port 5432) of the `postgres` user:

```bash
export MIGRATOR_PASSWORD=...  APP_USER_PASSWORD=...  REPORT_RO_PASSWORD=...   # generate long random values
uv run python -m app.cli.provision_db --admin-url "postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres"
```

This creates `migrator` (owns the schema, used only by Alembic), `app_user` (API runtime, `NOBYPASSRLS`,
no DDL) and `report_ro` (read-only), and sets default privileges so tables created by `migrator` are
usable by the other two. Re-running it is safe and re-sets the passwords.

## 3. Environment variables (names only; values live in the host's secret store)
| Variable | Value |
| --- | --- |
| `DATABASE_URL` | **pooler**, transaction mode (port 6543), user `app_user.<project-ref>`, `postgresql+asyncpg://` |
| `DATABASE_URL_MIGRATIONS` | **direct** connection (port 5432), user `migrator`, `postgresql+asyncpg://` |
| `SECRET_KEY` | long random string; the API refuses to start in `production`/`staging` without it |
| `APP_ENV` | `production` (or `staging`) |

The app already disables asyncpg's prepared-statement cache, which the transaction pooler requires.

## 4. Run the migrations
```bash
DATABASE_URL_MIGRATIONS="postgresql+asyncpg://migrator:...@db.<ref>.supabase.co:5432/postgres" uv run alembic upgrade head
```
The second migration enables and forces row-level security on every business table and revokes every grant
from Supabase's `anon` and `authenticated` roles (the Data API roles). Never edit the schema in the Supabase
dashboard: `alembic check` in CI will flag the drift.

## 5. Verify the lockdown
In the SQL editor:
```sql
SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class
 WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace ORDER BY 1;   -- all true except users, alembic_version
SELECT has_table_privilege('anon', 'public.customers', 'SELECT');             -- false
```
Also run Supabase's security advisor and fix any finding before launch. In project settings, disable the
Data API if the option is available (the app never uses it).

## 6. Seed the demo tenant (optional)
```bash
DEMO_USER_PASSWORD=... uv run python -m app.cli.seed
```
