"""BazaarFlow FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import httpx  # type: ignore[import-not-found]
from fastapi import FastAPI  # type: ignore[import-not-found]
from fastapi.middleware.cors import CORSMiddleware  # type: ignore[import-not-found]

from .controllers.vendors_controller import router as vendors_router
from .controllers.webhook_controller import router as webhook_router
from .controllers.sales_controller import router as sales_router
from .controllers.chat_controller import router as chat_router
from .controllers.inventory_controller import router as inventory_router



logger = logging.getLogger(__name__)


def _allowed_origins() -> list[str]:
    origins = {
        os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
        "http://127.0.0.1:3000",
    }
    return list(origins)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BazaarFlow FastAPI app")
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    try:
        yield
    finally:
        await app.state.http_client.aclose()
        logger.info("FastAPI app shutdown complete")


app = FastAPI(
    title="BazaarFlow API",
    version="1.0.0",
    description="BazaarFlow WhatsApp multi-tenant sales agent",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins() if os.getenv("PRODUCTION") else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(vendors_router)
# Include API routes up front so pywa can register its handlers against the same app
app.include_router(sales_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(inventory_router)

@app.get("/health")
async def healthcheck():
    return {"status": "ok"}
