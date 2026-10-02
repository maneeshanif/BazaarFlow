"""Meta WhatsApp webhook: verification handshake and inbound message processing.

Restored from the v1 controller (the restructure had reduced the POST handler to a log line, so inbound customer
messages were dropped). It still stores data in the v1 JSON repositories; phase 2 moves it behind the channel adapter
and onto the tenant-scoped database (build-plan tasks 13 and the phase 2 WhatsApp work).

Security (PRD §14.4): when ``META_APP_SECRET`` is set every POST must carry a valid ``X-Hub-Signature-256``; in
production and staging a missing secret refuses all POSTs instead of accepting unsigned traffic.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http_status
from fastapi.responses import JSONResponse, PlainTextResponse

from app import runner as runner_module
from app.core.dependencies import get_http_client
from app.core.settings import settings
from app.repositories import repository
from app.services import whatsapp

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/webhook/test")
async def test_webhook() -> JSONResponse:
    """Simple endpoint to check that the webhook route is reachable."""
    return JSONResponse(
        {
            "status": "ok",
            "message": "Webhook endpoint is accessible",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def _iso_timestamp(value: Optional[str]) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        if value.isdigit():
            return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
        return datetime.fromisoformat(value).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


@router.get("/webhook")
async def verify_webhook(request: Request) -> PlainTextResponse:
    """Meta's subscription handshake: echo ``hub.challenge`` as plain text (a JSON string would fail verification)."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token", "")
    challenge = request.query_params.get("hub.challenge", "")
    if mode == "subscribe" and hmac.compare_digest(token.encode(), settings.META_VERIFY_TOKEN.encode()):
        logger.info("WhatsApp webhook verified")
        return PlainTextResponse(challenge)
    logger.warning("WhatsApp webhook verification failed (mode=%s)", mode)
    raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Invalid verify token")


def _signature_is_valid(body: bytes, header: str | None) -> bool:
    expected = "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return bool(header) and hmac.compare_digest(expected.encode(), (header or "").encode())


def _extract_messages(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                messages.append(
                    {"message": message, "metadata": value.get("metadata", {}), "contacts": value.get("contacts", [])}
                )
    return messages


async def _handle_message(
    *,
    http_client: Any,
    message: Dict[str, Any],
    metadata: Dict[str, Any],
    contacts: List[Dict[str, Any]],
) -> None:
    phone_number_id = metadata.get("phone_number_id")
    if not phone_number_id:
        logger.warning("Webhook message missing phone_number_id metadata")
        return

    vendor = repository.upsert_vendor(
        phone_number_id=phone_number_id,
        name=metadata.get("display_phone_number"),
        waba_id=metadata.get("wa_id") or metadata.get("phone_number_id"),
    )

    customer_phone = message.get("from")
    if not customer_phone:
        logger.warning("Webhook message missing sender phone")
        return

    profile = next((c.get("profile") for c in contacts if c.get("wa_id") == customer_phone), None)
    customer_name = profile.get("name") if isinstance(profile, dict) else None
    customer = repository.upsert_customer(vendor["vendor_id"], phone=customer_phone, name=customer_name)

    message_type = message.get("type")
    text = message.get("text", {}).get("body") if message_type == "text" else None
    if message_type != "text":
        logger.warning("Non-text WhatsApp message type received: %s", message_type)

    repository.record_message(
        vendor_id=vendor["vendor_id"],
        customer_phone=customer_phone,
        direction="inbound",
        text=text,
        raw_payload=message,
        timestamp=_iso_timestamp(message.get("timestamp")),
    )

    action = await runner_module.runner_hook(
        vendor=vendor,
        customer=customer,
        incoming_message={"text": text, "raw": message},
        metadata=metadata,
    )
    reply_text = action.get("reply_text")
    if not reply_text:
        return

    access_token = vendor.get("access_token")
    if not access_token:
        logger.warning("Vendor %s has no access token; the reply is stored but not sent", vendor["vendor_id"])
        repository.record_message(
            vendor_id=vendor["vendor_id"],
            customer_phone=customer_phone,
            direction="outbound",
            text=reply_text,
            raw_payload={"status": "not_sent", "reason": "missing_access_token"},
            timestamp=_iso_timestamp(None),
        )
        return

    response: Any = None
    try:
        response = await whatsapp.send_text_message(
            client=http_client,
            phone_number_id=vendor["phone_number_id"],
            access_token=access_token,
            to=customer_phone,
            body=reply_text,
        )
    except whatsapp.WhatsAppAPIError as exc:
        logger.warning("WhatsApp API rejected the message to %s: %s", customer_phone, exc)
        response = {"status": "send_failed", "source": "whatsapp_api", "error": exc.payload}
        if exc.status_code is not None:
            response["http_status"] = exc.status_code
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to send outbound WhatsApp message")
        response = {"status": "send_failed", "error": "whatsapp_api_error"}

    repository.record_message(
        vendor_id=vendor["vendor_id"],
        customer_phone=customer_phone,
        direction="outbound",
        text=reply_text,
        raw_payload=response or {"status": "unknown"},
        timestamp=_iso_timestamp(None),
    )


@router.post("/webhook")
async def inbound_webhook(request: Request, http_client: Any = Depends(get_http_client)) -> JSONResponse:
    raw = await request.body()
    if settings.META_APP_SECRET:
        if not _signature_is_valid(raw, request.headers.get("X-Hub-Signature-256")):
            logger.warning("Rejected a WhatsApp webhook with a missing or invalid signature")
            return JSONResponse({"status": "error", "message": "Invalid signature"}, status_code=401)
    elif settings.APP_ENV in {"production", "staging"}:
        logger.error("META_APP_SECRET is not configured; refusing unsigned WhatsApp webhooks")
        return JSONResponse({"status": "error", "message": "Webhook secret not configured"}, status_code=503)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)

    messages = _extract_messages(body)
    if not messages:
        return JSONResponse({"status": "ignored"})

    for envelope in messages:
        await _handle_message(
            http_client=http_client,
            message=envelope["message"],
            metadata=envelope.get("metadata", {}),
            contacts=envelope.get("contacts", []),
        )
    return JSONResponse({"status": "ok"})
