# BazaarFlow Backend

FastAPI-powered orchestration layer that connects WhatsApp, multi-agent workflows, and the frontend dashboard. The backend exposes `/api/chat/*` endpoints, coordinates specialist agents (sales, finance, inventory), and serves lightweight analytics over the bundled datasets.

## Architecture Snapshot
- **FastAPI app**: defined in `app.py`, bootstrapped via the async lifespan returned by `wa_client.init_wa` so the WhatsApp client starts and stops cleanly.
- **Agents**: located under `my_agents/`. The sales agent acts as the orchestrator, while finance and inventory agents expose analytic tools through the OpenAI Agents SDK.
- **Services**: `services/` wraps deterministic helpers for finance and inventory data. Inventory tooling now includes a customer-safe catalog as well as vendor analytics.
- **Datasets**: JSON fixtures live in `data/`; they seed analytics without requiring external systems during development.
- **WhatsApp integration**: `wa_client.py` houses the client wiring and is activated during lifespan start-up.

## Customer vs Vendor Inventory Flows
- Sales conversations call the inventory agent with a `customer:` prefix, triggering customer-safe tools (`inventory_customer_catalog`, `inventory_search_items`) that list product names without revealing stock counts.
- Vendor dashboards and `/chat/inventory` continue to rely on analytic tools (`inventory_stock_overview`, `inventory_restock_alerts`, `inventory_category_summary`) that surface stock buckets, restock queues, and category breakdowns.

## Local Development
1. **Install dependencies**
	```bash
	cd backend
	uv sync  # or pip install -e . if uv is unavailable
	```
2. **Run the API**
	```bash
	fastapi dev app.py
	```
	The dev server hot-reloads and registers `/api/chat/sales`, `/api/chat/finance`, and `/api/chat/inventory` routes.
3. **Environment variables**
	- `GEMINI_API_KEY` – required by the inventory agent (falls back to a placeholder during local testing).
	- `OPENAI_MODEL` – optional override for the agent model (defaults to `gemini-2.0-flash`).

## Testing
- Targeted suites live in `backend/tests/`.
- After agent changes, prioritise:
  ```bash
  pytest backend/tests/test_inventory_service.py \
			backend/tests/test_inventory_api.py \
			backend/tests/test_chat_service.py
  ```
- Finance coverage remains under `backend/tests/test_finance_service.py` and `backend/tests/test_finance_api.py`.

## Pending Work
- Frontend chat pages still mock responses — wire them to the backend endpoints once agent behaviour stabilises.
- Swap remaining `example=` parameters in pywa hooks to `examples=` to remove deprecation warnings.
- Capture regression tests for the new customer-safe inventory catalogue behaviour.
