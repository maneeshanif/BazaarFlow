"""BazaarFlow FastAPI application - Production-ready MVC entrypoint.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError

from app.api.routers.main_router import main_router
from app.api.routers.v1 import api_v1_router
from app.core.auth import public_route
from app.core.problems import install_problem_handlers
from app.core.settings import settings
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware
from app.services.marketing_scheduler import marketing_scheduler
from app.utils.live_logs import configure_live_logging

configure_live_logging(logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("BazaarFlow starting up (env=%s)", settings.APP_ENV)
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    scheduler_started = False
    if settings.MARKETING_SCHEDULER_ENABLED and settings.APP_ENV != "test":
        await marketing_scheduler.start()
        scheduler_started = True
    yield
    if scheduler_started:
        await marketing_scheduler.stop()
    await app.state.http_client.aclose()
    logger.info("BazaarFlow shutdown complete")


def _allowed_origins() -> list[str]:
    """Explicit origins only: credentials are allowed, so a wildcard is never acceptable (not even in development)."""
    origins = [settings.FRONTEND_ORIGIN]
    if settings.APP_ENV in {"development", "test"}:
        origins += ["http://localhost:3000", "http://127.0.0.1:3000"]
    return sorted(set(origins))


app = FastAPI(
    title="BazaarFlow API",
    version="3.0.0",
    description="BazaarFlow - WhatsApp multi-tenant AI sales & marketing platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.exception_handler(StaleDataError)
async def stale_data_handler(_request: Request, _exc: StaleDataError) -> JSONResponse:
    """Another request changed the same row first (optimistic concurrency, PRD §12.2): reload and retry."""
    return JSONResponse(
        status_code=409,
        content={"detail": "The record was changed by someone else. Reload it and try again."},
    )


install_problem_handlers(app)

# Custom Middlewares
app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(RateLimiterMiddleware, limit=200, window=60)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers (both base /api routes and /api/v1 versioned routes)
app.include_router(main_router)
app.include_router(api_v1_router)


@app.get("/health", tags=["health"], dependencies=[Depends(public_route)])
async def healthcheck() -> dict[str, str]:
    return {
        "status": "healthy",
        "app": "BazaarFlow",
        "version": "3.0.0",
        "env": settings.APP_ENV,
    }
