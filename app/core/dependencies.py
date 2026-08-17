"""FastAPI shared dependencies.

Provides:
  - get_db: async database session (from database.py)
  - get_http_client: shared httpx.AsyncClient
  - get_settings: typed settings singleton
"""

from __future__ import annotations

from typing import AsyncGenerator

import httpx
from fastapi import Depends, Request

from app.core.database import get_db as _get_db  # re-export
from app.core.settings import Settings, settings


async def get_db():
    """Yield an async SQLAlchemy session. Use as a FastAPI Depends."""
    async for session in _get_db():
        yield session


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return the shared AsyncClient stored on app.state."""
    return request.app.state.http_client


def get_settings() -> Settings:
    """Return the application settings singleton."""
    return settings
