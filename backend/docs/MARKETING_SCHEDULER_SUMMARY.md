# Marketing Scheduler Implementation Summary

This document explains how BazaarFlow's automated marketing scheduler is wired together across backend modules and how it interacts with the rest of the system.

## Key Building Blocks

| File | Responsibility |
| --- | --- |
| `backend/app.py` | Bootstraps FastAPI and starts/stops the `marketing_scheduler` during application lifespan when `MARKETING_SCHEDULER_ENABLED` is truthy. |
| `backend/controllers/marketing_controller.py` | Exposes REST endpoints for account onboarding, schedule management, manual campaign runs, and scheduled run callbacks that ultimately delegate to `marketing_service`. |
| `backend/services/marketing_service.py` | Core orchestration layer that validates Facebook accounts, composes campaign overrides from inventory/sales data, publishes posts, and records results. Its `trigger_scheduled_campaign` API is what the scheduler calls. |
| `backend/services/marketing_scheduler.py` | Background cooperative worker that polls persisted schedules, matches the current time to user-configured slots, and invokes the marketing service while enforcing concurrency limits. |
| `backend/lib/marketing_repository.py` | JSON-store backed persistence for Facebook credentials, schedules, posts, and comment replies. The scheduler reads via `list_schedules()` and updates `last_triggered_at` through the service. |
| `frontend/app/dashboard/marketing/MarketingContext.tsx` & `.../schedule/page.tsx` | Provide the UI for merchants to configure schedule slots and time zones; these screens call the marketing controller endpoints so data lands in the repository that the scheduler consumes. |
| `backend/tests/test_marketing_scheduler.py` | Unit tests that exercise the scheduler's matching logic and guardrails (recent trigger suppression). |

## End-to-End Flow

1. **Account setup**: Merchants register their Facebook Page credentials through `POST /api/marketing/accounts` (`marketing_controller.py` → `marketing_service.register_account` → `marketing_repository` JSON store).
2. **Schedule capture**: The dashboard schedule UI submits slots (up to three `HH:MM` strings with a timezone). `PUT /api/marketing/accounts/{account_id}/schedule` persists them via `save_schedule`.
3. **Scheduler startup**: When FastAPI boots (`app.py`), the lifespan hook creates a shared `httpx.AsyncClient` and starts `marketing_scheduler` if `MARKETING_SCHEDULER_ENABLED` defaults to true or is explicitly set.
4. **Polling loop**: `marketing_scheduler` wakes every `MARKETING_SCHEDULER_POLL_SECONDS` (default 30s), loads all schedules, and evaluates each via `_maybe_trigger`.
5. **Slot matching & throttling**:
   - Slots are interpreted in the schedule's timezone using `ZoneInfo` and compared against `now` with a `matching_window` (default ±45 seconds).
   - `last_triggered_at` prevents duplicate runs within the `trigger_window` (default 90 seconds).
   - A semaphore (`MARKETING_SCHEDULER_MAX_CONCURRENT`, default 3) and `_active_accounts` set ensure the same account is not triggered twice in parallel.
6. **Campaign execution**: When a slot is due, the scheduler calls `marketing_service.trigger_scheduled_campaign`, which in turn:
   - Rehydrates the Facebook account (`get_facebook_account`).
   - Builds operational context (inventory health, sales velocity) to feed the agent.
   - Requests creative payloads from the marketing agent, enriches them with curated hashtags/images, and posts to Facebook via `FacebookManager`.
   - Records the result and updates `mark_schedule_triggered` so follow-up runs know when the slot was last used.
7. **Observability & recovery**: Exceptions inside `_tick` are logged but do not crash the loop; per-account failures are also logged with `exc_info` for diagnosis. When FastAPI shuts down, the lifespan hook stops the scheduler and closes the shared HTTP client cleanly.

## Configuration Surface

Environment variables allow tuning without code changes:

- `MARKETING_SCHEDULER_ENABLED` — opt-out of the scheduler entirely when falsey.
- `MARKETING_SCHEDULER_POLL_SECONDS` — polling cadence (minimum enforced at 5s).
- `MARKETING_SCHEDULER_TRIGGER_WINDOW_SECONDS` — cooldown window before re-triggering same account.
- `MARKETING_SCHEDULER_MATCH_WINDOW_SECONDS` — acceptable drift between configured slot and current clock.
- `MARKETING_SCHEDULER_MAX_CONCURRENT` — maximum concurrent scheduled campaigns.
- `BF_JSON_DB_ROOT` — overrides the filesystem root for JSON stores (accounts, schedules, posts, replies).
- Facebook, inventory, and Pexels related vars (e.g., `FACEBOOK_API_*`, `PEXELS_*`) are consumed downstream by `marketing_service` when composing campaigns.

## Data Model & Persistence

- **Accounts** (`facebook_accounts.json`): stores user/page IDs, access tokens, and metadata. Updated through the marketing controller and consumed by `marketing_service`.
- **Schedules** (`marketing_schedules.json`): contains `account_id`, `user_id`, `times`, `timezone`, and `last_triggered_at`. Read by the scheduler each tick; updated after every successful run.
- **Posts** (`marketing_posts.json`) & **Replies**: store publishing history and auto-reply state, enabling dashboard insights and follow-up automation.

## Testing & Manual Operations

- `backend/tests/test_marketing_scheduler.py` demonstrates how to stub the `campaign_runner` to assert scheduling behavior. Use it as a template for further cases (e.g., timezone edge cases, semaphore contention).
- Operators can still invoke manual campaigns via `POST /api/marketing/accounts/{account_id}/campaign` for smoke-testing creative pipelines without waiting for a schedule slot.
- The `/health` endpoint in `app.py` remains lightweight so scheduler issues surface via logs rather than blocking health checks.

## Operational Tips

- Set `MARKETING_SCHEDULER_ENABLED=false` in staging environments where you only want manual runs.
- Tune `matching_window` and `trigger_window` to accommodate clock drift between clients and the server.
- Watch logs for "Marketing scheduler tick failed" or "Triggering scheduled marketing run" lines to trace executions.
- If you rotate Facebook tokens or Pexels keys, no restart is needed—the services pull from env/JSON stores at call time.
