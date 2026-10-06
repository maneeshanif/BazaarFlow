"""Builds provider adapters from a shop's stored credentials (the only place that knows which class serves which provider).

Production leaves ``providers`` alone. Tests set ``providers.transport`` to an ``httpx.MockTransport`` and
``providers.sleep`` to a recorder, so adapters never touch the network and never wait.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.settings import settings
from app.integrations.facebook_graph import FacebookGraphAdapter
from app.integrations.http import Sleep
from app.integrations.pexels import PexelsClient
from app.integrations.twilio_whatsapp import SANDBOX_NUMBER, TwilioWhatsAppAdapter
from app.integrations.vapi import VapiAdapter


@dataclass
class ProviderHooks:
    transport: httpx.AsyncBaseTransport | None = None
    sleep: Sleep | None = None


providers = ProviderHooks()

TWILIO_WEBHOOK_PATH = "/api/v1/webhooks/twilio"


def twilio_webhook_url() -> str:
    """The exact public URL Twilio calls; the signature covers it, so it comes from configuration, never from the request."""
    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{TWILIO_WEBHOOK_PATH}"


def build_twilio(credentials: dict[str, Any]) -> TwilioWhatsAppAdapter:
    return TwilioWhatsAppAdapter(
        str(credentials["account_sid"]),
        str(credentials["auth_token"]),
        str(credentials.get("whatsapp_number") or SANDBOX_NUMBER),
        webhook_url=twilio_webhook_url(),
        transport=providers.transport,
        sleep=providers.sleep,
        retries=settings.PROVIDER_MAX_RETRIES,
        timeout=settings.PROVIDER_TIMEOUT_SECONDS,
    )


def build_facebook(credentials: dict[str, Any]) -> FacebookGraphAdapter:
    return FacebookGraphAdapter(
        str(credentials["page_id"]),
        str(credentials["access_token"]),
        app_secret=str(credentials.get("app_secret") or settings.META_APP_SECRET),
        base=settings.META_GRAPH_BASE,
        version=settings.META_GRAPH_VERSION,
        transport=providers.transport,
        sleep=providers.sleep,
        retries=settings.PROVIDER_MAX_RETRIES,
        timeout=settings.PROVIDER_TIMEOUT_SECONDS,
    )


def build_pexels() -> PexelsClient:
    return PexelsClient(
        settings.PEXELS_API_KEY,
        transport=providers.transport,
        sleep=providers.sleep,
        retries=settings.PROVIDER_MAX_RETRIES,
        timeout=settings.PROVIDER_TIMEOUT_SECONDS,
    )


def build_vapi(credentials: dict[str, Any]) -> VapiAdapter:
    return VapiAdapter(
        str(credentials["assistant_id"]),
        str(credentials["webhook_secret"]),
        str(credentials.get("api_key") or ""),
        transport=providers.transport,
        sleep=providers.sleep,
        retries=settings.PROVIDER_MAX_RETRIES,
        timeout=settings.PROVIDER_TIMEOUT_SECONDS,
    )
