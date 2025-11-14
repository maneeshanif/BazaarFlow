# Quickstart

## Backend (FastAPI + Agents)
1. Install uv (or activate the repo's existing `.venv`).
2. From `backend/`, install dependencies:
   - With uv: `uv sync`
   - Or with pip: `pip install -e .`
3. Export the required environment variables (see `.env.example` if available). At minimum set WhatsApp credentials and `GEMINI_API_KEY`.
4. Launch the API:
   - `uv run uvicorn app:fastapi_app --reload`
5. Run backend tests any time with:
   - `uv run pytest backend/tests`

The service exposes REST endpoints under `http://localhost:8000/api`, including `/api/chat/sales`, `/api/chat/finance`, and `/api/chat/inventory`.

## Frontend (Next.js)
1. From `frontend/`, install dependencies: `npm install` (or `pnpm install` if preferred).
2. Start the dev server: `npm run dev` (defaults to `http://localhost:3000`).
3. Chat agent pages live at:
   - `/chat/sales`
   - `/chat/finance`
   - `/chat/inventory`

Run frontend unit/integration tests with `npm test`.
