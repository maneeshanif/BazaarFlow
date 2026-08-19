"""BazaarFlow FastAPI application - Production-ready MVC entrypoint.

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
from app.api.routers.v1 import api_v1_router
from app.core.settings import settings
from app.middleware.request_logger import RequestLoggerMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
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
    version="3.0.0",
    description="BazaarFlow - WhatsApp multi-tenant AI sales & marketing platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Custom Middlewares
app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(RateLimiterMiddleware, limit=200, window=60)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN] if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers (both base /api routes and /api/v1 versioned routes)
app.include_router(main_router)
app.include_router(api_v1_router)


@app.get("/health", tags=["health"])
async def healthcheck():
    return {
        "status": "healthy",
        "app": "BazaarFlow",
        "version": "3.0.0",
        "env": settings.APP_ENV,
    }
