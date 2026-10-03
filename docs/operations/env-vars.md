# Environment variables

`.env` is never committed. `.env.example` must list every key below with an **empty value**. (The agent that
prepared this change is not allowed to read that file, so the owner should add the keys marked *new*.)

| Variable | Used by | Notes |
| --- | --- | --- |
| `APP_ENV` | API | `development`, `test`, `staging`, `production` |
| `SECRET_KEY` | API | JWT signing key. Long random string. **The API refuses to start without it** (only `APP_ENV=test` gets a throwaway key) |
| `ALLOW_INSECURE_DEV_SECRET` | API | *new*. Local development only: `true` lets the API start without `SECRET_KEY`. Ignored in `production`/`staging` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | API | *new*, default 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | API | *new*, default 14 |
| `LOGIN_MAX_FAILURES` / `LOGIN_LOCKOUT_MINUTES` | API | *new*, defaults 5 / 15 |
| `SIGNUP_MAX_PER_HOUR` | API | *new*, default 10 sign-ups per client address per hour, 0 = unlimited |
| `DATABASE_URL` | API runtime | Supabase **pooler** (port 6543), user `app_user`, `postgresql+asyncpg://` |
| `DATABASE_URL_MIGRATIONS` | Alembic | *new*. Supabase **direct** connection (port 5432), user `migrator` |
| `SUPABASE_PROJECT_REF`, `SUPABASE_POOLER_HOST` | `app.cli.provision_supabase` | project ref and `aws-0-<region>.pooler.supabase.com` from Connect -> Session pooler. Not secret |
| `SUPABASE_ADMIN_PASSWORD` | `app.cli.provision_supabase` | the database password. Used once, then the command blanks it. Never keep it in `.env` |
| `MIGRATOR_PASSWORD`, `APP_USER_PASSWORD`, `REPORT_RO_PASSWORD` | `app.cli.provision_db` | *new*. Only needed on the machine that provisions roles; never on the API host |
| `DEMO_USER_PASSWORD` | `app.cli.seed` | optional; generated and printed once if unset |
| `FRONTEND_ORIGIN` | API CORS | production origin of the web app |
| `GEMINI_API_KEY`, `GEMINI_BASE_URL`, `GEMINI_MODEL` | agents | LLM provider |
| `META_VERIFY_TOKEN`, `META_GRAPH_VERSION`, `META_GRAPH_BASE` | WhatsApp webhook | becomes per-tenant in Phase 2 |
| `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN` | marketing | becomes per-tenant in Phase 2 |
| `VAPI_API_KEY`, `VAPI_WEBHOOK_SECRET` | voice | becomes per-tenant in Phase 3 |
| `PEXELS_API_KEY` | marketing images | |
| `MARKETING_SCHEDULER_ENABLED` | scheduler | default true |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | WhatsApp sandbox | demo channel (PRD A-004). Check them with `uv run python -m app.cli.smoke_twilio`. Per-tenant encrypted credentials replace these in phase 2 |
| `META_APP_SECRET` | WhatsApp webhook | verifies the inbound signature (`X-Hub-Signature-256`); the webhook refuses unsigned calls without it |
| `LEGACY_V1_ROUTES` | API | `true` mounts the old JSON-store routes outside development/test; leave empty in production |
| `REFRESH_REUSE_GRACE_SECONDS` | API | default 10. A rotated refresh token presented again within this window is treated as a lost response, not theft. `0` = strict |
| `AGENT_SERVICE_TOKEN` | API, agent service | shared secret for `X-Agent-Service-Token` (ADR 0003). Required outside tests |
| `API_BASE_URL` | agent service | how the agent service reaches the API. It never receives a database variable |
| `API_INTERNAL_URL` | web (server side) | the API address the Next.js auth route handlers call; falls back to `NEXT_PUBLIC_API_BASE_URL` |
| `NEXT_PUBLIC_API_BASE_URL` | web (browser) | public API address used by the browser |
| `NEXT_PUBLIC_VAPI_PUBLIC_KEY`, `NEXT_PUBLIC_VAPI_SUPPORT_ASSISTANT_ID` | web | voice widget (phase 3) |
| `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_DSN` | web | Sentry. A DSN is not secret |
| `SENTRY_AUTH_TOKEN` | CI only | uploads source maps. A secret: never in a build argument or an image |

Never put the Supabase `service_role` key, or any production credential, in an agent's or developer's environment.
