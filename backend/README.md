# BazaarFlow Backend

FastAPI backend that powers the BazaarFlow WhatsApp sales agent. It now runs a
multi-tenant webhook pipeline on top of the WhatsApp Business Cloud API, keeps
vendor/customer state inside a lightweight JSON DB, and orchestrates replies via
the OpenAI Agents SDK.

## Key Components
- **FastAPI app (`app.py`)** – exposes `/webhook` plus dashboard APIs under
	`/api/vendors/*`. Startup initialises a shared `httpx.AsyncClient` for Meta
	Graph calls.
- **Webhook handler (`webhook.py`)** – parses inbound Meta payloads, upserts
	vendors and customers, stores transcripts, executes the sales agent, and
	replies through the Cloud API.
- **JSON DB (`db/json_store.py`, `db/repository.py`)** – tiny persistence layer
	with POSIX file locking. Stores vendors, customers, and messages in
	`backend/db/*.json` files.
- **Runner glue (`runner.py`)** – prepares context for the sales agent and
	applies fallback rules if the agent response is empty.
- **Vendor API (`api/vendors.py`)** – dashboard endpoints for managing WhatsApp
	credentials, browsing customers, loading conversation history, and sending
	manual replies.

## JSON Storage Layout
```
backend/db/vendors.json   # vendor profile + tokens
backend/db/customers.json # vendor scoped customer list
backend/db/messages.json  # ordered transcript history
```
Each file is written atomically with a sibling `.lock` file to stay safe under
concurrent access.

## Local Development
1. **Install dependencies**
	 ```bash
	 cd backend
	 uv sync  # or: pip install -e .
	 ```
2. **Environment variables**
	 - `META_VERIFY_TOKEN` – verification token for GET `/webhook` (defaults to
		 `test123`).
	 - `META_GRAPH_VERSION` / `META_GRAPH_BASE` – optional overrides for the Cloud
		 API base URL (default `https://graph.facebook.com/v17.0`).
	 - `GEMINI_API_KEY`, `OPENAI_MODEL` – agent credentials as before.
3. **Run the server**
	 ```bash
	 fastapi dev app.py
	 ```
	 or via uvicorn: `uvicorn backend.app:app --reload`.

## Testing
```bash
pytest backend/tests/test_db_repository.py backend/tests/test_webhook.py
```
`test_webhook.py` stubs the runner + WhatsApp client to verify payload parsing
and JSON DB writes. Repository tests cover the JSON store’s locking helpers.

## Tooling / Harness
- `backend/scripts/mock_webhook.py` – quick CLI to POST a sample payload to a
	running server (use `--payload` to inject a custom JSON file).

## Frontend Contract
The dashboard should call the following endpoints:
- `GET /api/vendors/{vendor_id}/customers`
- `GET /api/vendors/{vendor_id}/customers/{phone}/messages`
- `POST /api/vendors/{vendor_id}/customers/{phone}/messages`
- `GET /api/vendors/{vendor_id}/settings`
- `POST /api/vendors/{vendor_id}/settings`

Each route is functional and returns JSON payloads ready for the React client.
