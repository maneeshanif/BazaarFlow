"""BazaarFlow FastAPI application — MVC production entrypoint.

Run with:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.main_router import main_router
from app.core.settings import settings
from app.utils.live_logs import configure_live_logging

configure_live_logging(logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("BazaarFlow starting up (env=%s)", settings.APP_ENV)
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.http_client.aclose()
    logger.info("BazaarFlow shutdown complete")


app = FastAPI(
    title="BazaarFlow API",
    version="2.0.0",
    description="BazaarFlow — WhatsApp multi-tenant AI sales platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN] if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single include — main_router aggregates everything
app.include_router(main_router)


@app.get("/health", tags=["health"])
async def healthcheck():
    return {"status": "ok", "env": settings.APP_ENV}
