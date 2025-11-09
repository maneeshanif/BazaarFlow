"""
WhatsApp (pywa) client initializer module.

Provides init_wa(app, logger) which initializes the pywa WhatsApp client
with the provided FastAPI app instance and attaches startup tasks.
"""
from typing import Optional
import os
from pywa_async import WhatsApp


def _safe_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def init_wa(fastapi_app, logger):
    """Create and return a WhatsApp client bound to `fastapi_app`.

    This follows pywa's recommended pattern: create the FastAPI app, then
    initialize WhatsApp with server=fastapi_app so decorators work.
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

    # Note: Startup logic moved to lifespan context manager in app.py
    # to avoid conflicts with modern FastAPI lifecycle management

    return wa
