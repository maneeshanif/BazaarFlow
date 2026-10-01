"""FastAPI shared dependencies.

Provides:
  - get_db: async database session (from database.py)
  - get_http_client: shared httpx.AsyncClient
  - get_settings: typed settings singleton
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db as _get_db  # re-export
from app.core.settings import Settings, settings


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session. Use as a FastAPI Depends."""
    async for session in _get_db():
        yield session


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return the shared AsyncClient stored on app.state."""
    client: httpx.AsyncClient = request.app.state.http_client
    return client


def get_settings() -> Settings:
    """Return the application settings singleton."""
    return settings
