"""
WhatsApp (pywa) client initializer module.

Provides ``init_wa(app, logger)`` which initializes the pywa WhatsApp client
with the provided FastAPI app instance and returns an async lifespan context
manager for startup/shutdown orchestration.
"""
from contextlib import asynccontextmanager
from typing import Optional
import os
from fastapi import FastAPI
from pywa_async import WhatsApp


def _safe_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def init_wa(fastapi_app, logger):
    """Create a WhatsApp client bound to ``fastapi_app``.

    Returns a tuple ``(wa_client, lifespan_context)`` where
    ``lifespan_context`` is an async context manager compatible with FastAPI's
    lifespan hooks. The caller must wire the context manager into FastAPI to
    avoid deprecated ``on_event`` handlers.
    """
    wa = WhatsApp(
        phone_id=_safe_int(os.getenv("WA_PHONE_ID")),
        token=os.getenv("WA_TOKEN"),
        server=fastapi_app,
        callback_url=os.getenv("WA_CALLBACK_URL", None),
        webhook_endpoint=os.getenv("WA_WEBHOOK_ENDPOINT", "/webhook"),
        verify_token=os.getenv("WA_VERIFY_TOKEN", "test123"),
        app_id=_safe_int(os.getenv("WA_APP_ID")),
        app_secret=os.getenv("WA_APP_SECRET"),
        validate_updates=(os.getenv("WA_VALIDATE_UPDATES", "false").lower() in ("1", "true", "yes")),
    )

    @asynccontextmanager
    async def wa_lifespan(_: FastAPI):
        """FastAPI lifespan hook for WhatsApp startup/shutdown."""
        required_vars = ["WA_TOKEN", "WA_APP_ID", "WA_APP_SECRET", "WA_PHONE_ID"]
        missing = [v for v in required_vars if not os.getenv(v)]
        if missing:
            logger.warning("Missing WA env vars: %s", missing)
            yield
            return

        try:
            webhook_url = os.getenv("WA_CALLBACK_URL")
            logger.info("Registering WhatsApp webhook at %s", webhook_url)
            resp = await wa.send_message(
                to=os.getenv("WA_ADMIN_PHONE", "923012177654"),
                text="👋 BazaarFlow started",
            )
            logger.info("Startup message sent, id=%s", getattr(resp, "id", None))
        except Exception:
            logger.exception("Failed to run WA startup tasks")

        try:
            yield
        finally:
            logger.info("WhatsApp client shutdown complete")

    return wa, wa_lifespan
