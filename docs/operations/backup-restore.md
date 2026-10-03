# Backups and restore

Targets (PRD section 18): **RPO 24 hours, RTO 4 hours** at launch. Backups are kept 7 days.

## What protects the data

| Layer | What it gives | Who runs it |
| --- | --- | --- |
| Supabase daily backups | A managed restore of the whole project, 24 h RPO | Supabase (check it is on in Project settings, Database, Backups) |
| `scripts/backup.sh` | A logical dump you hold yourself (`pg_dump --format=custom`) | You, daily (cron, a scheduled workflow, or by hand) |
| Alembic | The schema can always be rebuilt from `alembic upgrade head` | CI and deploy |
| Point in time recovery | 15 minute RPO | Supabase Pro, switch on before paid shops arrive |

## Take a backup

```bash
BACKUP_DATABASE_URL="postgresql://migrator:...@host:5432/postgres" bash scripts/backup.sh backups
```

The URL is the owner role's (the same value as `DATABASE_URL_MIGRATIONS`). It is never printed. Keep the files somewhere
other than the database host (a different account or bucket), and treat them as secret: they hold every shop's data.

## Restore (into a scratch project first)

1. Create an empty scratch database (a second Supabase project, or any Postgres 16). Never restore over production first.
2. Create the roles the schema grants to, if they are missing: `anon`, `authenticated`, `app_user`, `report_ro`
   (`uv run python -m app.cli.provision_supabase` does it for Supabase).
3. Restore: `pg_restore --no-owner -d "<scratch url>" backups/bazaarflow-<time>.dump`
4. Check: row counts match the source, `alembic current` shows the head revision, and sign in to a shop.
5. Only then decide whether to point production at it (change `DATABASE_URL` and `DATABASE_URL_MIGRATIONS`, restart the API).

## The drill that proves it works

`tests/pg/test_backup_restore.py` takes a dump of a database holding two demo shops, restores it into a fresh database and
checks: every table has the same rows, row level security is still on and forced, and the policies still isolate one shop
from another. It prints the timings. Measured on the first run (189 rows, local Docker): dump 0.2 s, restore 1.7 s, against a
target of 14,400 s. Real data will be larger, so repeat the drill monthly against a scratch project with a real backup
(PRD section 18) and write the time in `context/progress-log.md`.

## Demo shops

Visitors' temporary shops are removed by `uv run python -m app.cli.purge_demos` (owner role). Schedule it hourly.
