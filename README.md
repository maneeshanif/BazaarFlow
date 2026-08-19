# BazaarFlow

BazaarFlow is an AI-powered conversational sales, inventory, and marketing management platform for WhatsApp and multi-tenant commerce.

## Architecture

Built with FastAPI (Python 3.12+), SQLAlchemy 2.0 Async, Alembic, Pydantic v2, and Next.js.

### Quick Start

```bash
# Install dependencies
uv sync

# Run backend
uv run uvicorn app.main:app --reload --port 8000
```