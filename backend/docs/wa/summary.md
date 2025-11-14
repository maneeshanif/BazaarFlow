# wiring up all agents

# wiring up all agents

## Key Changes
- Migrated the FastAPI startup flow to an async lifespan context returned from `wa_client.init_wa`, ensuring the WhatsApp client boots and shuts down cleanly without deprecation warnings.
- Consolidated `backend/app.py` around a single `FastAPI` instance that mounts the lifespan hook and exposes the `/api/chat/*` routes used by the sales orchestrator.
- Elevated the sales agent to a strict tool-first orchestrator that now prefixes inventory prompts with `customer:` so downstream tools return product names without stock counts for customer-facing chats.
- Added a customer-safe catalog path inside the inventory toolset: `inventory_customer_catalog` now surfaces curated product names with prices, and `inventory_search_items` strips the customer prefix to suppress internal stock analytics.
- Refreshed `inventory_agent` guidance so vendor requests continue to see full analytics while sales-driven customer requests stay succinct.
- Finance agent now handles order placement through new `create_customer_order` tool that saves orders to `sales_orders.json`.
- Sales agent instructions updated to handle greetings without tool calls and delegate order placement to finance agent.
- Added price field to all inventory items (PKR format).
- Frontend chat UI now maintains persistent session IDs across messages.
- Dashboard updated to fetch and display real order data from `/api/sales` endpoint.

## Current Caveats
- Stock and finance pytest suites have not been re-run after the latest agent instruction changes; execute `pytest backend/tests/test_inventory_service.py backend/tests/test_inventory_api.py backend/tests/test_chat_service.py` before release.
- Frontend `/chat/finance` and `/chat/inventory` pages still return mocked payloads instead of calling the stitched backend endpoints.
- pywa still emits `example` parameter deprecation warnings; migrating to `examples=` remains outstanding.
- Logs page currently shows mock data; need to integrate real agent tracing system.
- Rate limiting from Gemini API (429 errors) - need to implement retry logic or consider rate limiting.
