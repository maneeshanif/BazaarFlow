# Marketing Automation Flow

BazaarFlow's marketing agent delivers Facebook campaigns that blend live inventory, sales performance, and curated imagery. This document outlines the moving parts so operators can hook a storefront into the workflow quickly.

## High-Level Architecture

1. **Credentials & Scheduling** – Stored in JSON-backed repositories (`backend/lib/marketing_repository.py`). The new FastAPI router (`/api/marketing/...`) exposes CRUD endpoints for Facebook page credentials and posting schedules.
2. **Campaign Generation** – `MarketingService` orchestrates the run:
   - Delegates copy and creative planning to `MarketingAgent` (OpenAI Agents SDK) via `generate_campaign_payload`.
   - Tools (`marketing_inventory_snapshot`, `marketing_sales_insights`, `marketing_image_search`) provide real-time context from inventory, sales orders, and Pexels search results.
3. **Publishing & Tracking** – `FacebookManager` handles posting (text or image) and later fetches lifetime insights. Posts, schedules, and credentials are persisted for the dashboard UI.
4. **Frontend Experience** – `/dashboard/marketing` page surfaces forms for credentials, schedule management, manual campaign triggers, and an insights-driven feed of recent posts.

```
Dashboard Action ─┐
                  │  POST /api/marketing/accounts/{id}/campaign
                  ▼
MarketingService ─┬─> MarketingAgent (tools: inventory, sales, Pexels)
                  │
                  └─> FacebookManager publish -> JsonStore history
```

## API Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/marketing/accounts` | List stored Facebook credentials. |
| `POST` | `/api/marketing/accounts` | Validate & upsert a credential bundle (requires page token). |
| `DELETE` | `/api/marketing/accounts/{account_id}` | Remove credentials. |
| `PUT` | `/api/marketing/accounts/{account_id}/schedule` | Save up to three preferred posting times (UTC or IANA timezone). |
| `GET` | `/api/marketing/accounts/{account_id}/schedule` | Retrieve the active schedule. |
| `POST` | `/api/marketing/accounts/{account_id}/campaign` | Trigger a manual marketing run (optional prompt + JSON overrides). |
| `POST` | `/api/marketing/accounts/{account_id}/campaign/scheduled` | Fire the same flow for cron/worker usage; updates `last_triggered_at`. |
| `GET` | `/api/marketing/accounts/{account_id}/posts` | Fetch most recent campaigns and stored metadata. |
| `POST` | `/api/marketing/accounts/{account_id}/posts/{facebook_post_id}/insights` | Refresh lifetime metrics from Facebook. |

All endpoints respond with `{ "ok": true, ... }` payloads on success; validation errors return HTTP 400.

## Agent Input/Output Contract

- **Input**: JSON string containing `account`, `user_id`, `mode`, optional `prompt`, and `overrides`.
- **Output**: JSON object with `message`, `hashtags`, `angle`, `image_url`/`image_query`, `product_sku`, and `call_to_action`. The marketing service enforces this schema before publishing.

The agent always calls both the inventory and sales tools to ground suggestions in real data. If `image_url` is missing, the backend performs a Pexels lookup using the optional `image_query`.

## Scheduling Strategy

- Persist up to three preferred posting slots per account (e.g., morning/noon/evening).
- A background worker can invoke `POST /campaign/scheduled` at those times. The service records `last_triggered_at` to aid monitoring.
- Manual runs can be launched from the dashboard to preview or boost urgent campaigns.

## Environment Variables

Ensure the following keys are present in `.env` when enabling marketing automation:

- `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN` – Page credentials with publish & insights permissions.
- `PEXELS_API_KEY` – Enables fallback image suggestions when the agent does not provide a direct URL.
- Optional: `FACEBOOK_API_VERSION`, `FACEBOOK_API_BASE_URL`, `REQUEST_TIMEOUT`, `MAX_RETRIES` for tuning the Graph API client.

## Operational Checklist

1. Add Facebook credentials through the dashboard (or POST endpoint) – verification ensures tokens are valid.
2. Set local timezone-aware posting slots.
3. Confirm `PEXELS_API_KEY` is configured if you rely on automated imagery.
4. Trigger a manual campaign to validate copy, hashtags, and published posts.
5. Use the "Refresh Insights" action after a post has gathered engagement to populate the performance cards.

This flow keeps content generation reproducible while still allowing human operators to steer messaging when needed.
