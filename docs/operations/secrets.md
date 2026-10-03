# Where each secret lives (task 26)

Rule: no credential is ever committed. `gitleaks` scans the whole history in CI and in `verify.sh --slow`; the only
findings it accepts are the 22 reviewed historical ones in `.gitleaks-baseline.json` (keys already rotated or fake
test fixtures).

| Where | What lives there | How you set it |
|---|---|---|
| Your laptop: `.env` (gitignored) | everything you need to run locally | copy `docs/operations/env.example.proposed` to `.env.example`, then `cp .env.example .env` and fill it |
| GitHub Actions secrets | `DATABASE_URL_MIGRATIONS`, `FASTAPI_CLOUD_TOKEN`, `FASTAPI_CLOUD_APP_ID`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `SENTRY_AUTH_TOKEN` | repo Settings -> Secrets and variables -> Actions |
| FastAPI Cloud (API runtime) | `SECRET_KEY`, `DATABASE_URL` (`app_user` pooler), `GEMINI_API_KEY`, `META_APP_SECRET`, `META_VERIFY_TOKEN`, `TWILIO_*` | `uv run fastapi cloud env set NAME value --secret` |
| Vercel (web) | `NEXT_PUBLIC_*`, `API_INTERNAL_URL`, `SENTRY_DSN` | project Settings -> Environment Variables |
| Your password manager | the Supabase `postgres` admin password and the three role passwords | never in any environment the agent or CI can read |

Never in an agent's, developer's or CI environment: the Supabase `service_role` key, the `postgres` admin
password, or any production credential other than the ones listed for deploy.

## Checking the Twilio sandbox
Add `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` to `.env` (Twilio console -> Account Info), enable the WhatsApp
sandbox (Messaging -> Try it out -> Send a WhatsApp message), then:

    uv run python -m app.cli.smoke_twilio                                   # credentials only (free, read-only)
    uv run python -m app.cli.smoke_twilio --to +92300XXXXXXX --body hello   # one sandbox message

The recipient must first send `join <your sandbox code>` to the sandbox number from their own WhatsApp.
