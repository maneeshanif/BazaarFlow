# Environment variables

`.env` is never committed. `.env.example` must list every key below with an **empty value**. (The agent that
prepared this change is not allowed to read that file, so the owner should add the keys marked *new*.)

| Variable | Used by | Notes |
| --- | --- | --- |
| `APP_ENV` | API | `development`, `test`, `staging`, `production`. In `staging`/`production` the API refuses to start without `SECRET_KEY`. |
| `SECRET_KEY` | API | JWT signing key. Long random string. *(behaviour changed: no insecure default outside development)* |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | API | *new*, default 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | API | *new*, default 14 |
| `LOGIN_MAX_FAILURES` / `LOGIN_LOCKOUT_MINUTES` | API | *new*, defaults 5 / 15 |
| `DATABASE_URL` | API runtime | Supabase **pooler** (port 6543), user `app_user`, `postgresql+asyncpg://` |
| `DATABASE_URL_MIGRATIONS` | Alembic | *new*. Supabase **direct** connection (port 5432), user `migrator` |
| `MIGRATOR_PASSWORD`, `APP_USER_PASSWORD`, `REPORT_RO_PASSWORD` | `app.cli.provision_db` | *new*. Only needed on the machine that provisions roles; never on the API host |
| `DEMO_USER_PASSWORD` | `app.cli.seed` | optional; generated and printed once if unset |
| `FRONTEND_ORIGIN` | API CORS | production origin of the web app |
| `GEMINI_API_KEY`, `GEMINI_BASE_URL`, `GEMINI_MODEL` | agents | LLM provider |
| `META_VERIFY_TOKEN`, `META_GRAPH_VERSION`, `META_GRAPH_BASE` | WhatsApp webhook | becomes per-tenant in Phase 2 |
| `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN` | marketing | becomes per-tenant in Phase 2 |
| `VAPI_API_KEY`, `VAPI_WEBHOOK_SECRET` | voice | becomes per-tenant in Phase 3 |
| `PEXELS_API_KEY` | marketing images | |
| `MARKETING_SCHEDULER_ENABLED` | scheduler | default true |

Never put the Supabase `service_role` key, or any production credential, in an agent's or developer's environment.
