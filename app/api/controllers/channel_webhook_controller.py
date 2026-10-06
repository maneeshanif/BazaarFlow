"""Channel webhooks (PRD W-003, I-001): the public endpoint Twilio calls for each inbound WhatsApp message.

Public by design (the provider cannot sign in), so it earns its trust the other way: the signature is verified with the
credential of the shop the message claims to be for, before anything is parsed or stored, and a replayed event is ignored.
A bad signature and an unknown shop get the same 403, so the endpoint cannot be used to find out which shops exist.
"""

from __future__ import annotations

from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.auth import public_route
from app.integrations import factory
from app.integrations import vapi as vapi_events
from app.schemas.integrations import WebhookResult
from app.services import channel_webhook_service, voice_webhook_service

router = APIRouter()

_FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")
MAX_BODY_BYTES = 64 * 1024


@router.post("/twilio", response_model=WebhookResult, dependencies=[Depends(public_route)])
async def twilio_webhook(request: Request) -> WebhookResult:
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload too large")
    headers = {key.lower(): value for key, value in request.headers.items()}
    fields = dict(parse_qsl(body.decode("utf-8", errors="replace"), keep_blank_values=True))
    found = await channel_webhook_service.find_integration("whatsapp_twilio", fields.get("AccountSid", ""))
    if found is None:
        raise _FORBIDDEN
    tenant_id, credentials = found
    adapter = factory.build_twilio(credentials)
    try:
        if not adapter.verify_webhook(headers, body):
            raise _FORBIDDEN
        inbound = await adapter.receive(headers, body)
    finally:
        await adapter.aclose()
    if inbound is None:  # a delivery receipt or an empty message: acknowledge so Twilio does not retry
        return WebhookResult(status="ignored")
    outcome = await channel_webhook_service.handle_inbound(
        tenant_id, "whatsapp_twilio", inbound, contact_name=fields.get("ProfileName") or None
    )
    return WebhookResult(status=outcome)  # type: ignore[arg-type]


@router.post("/vapi", dependencies=[Depends(public_route)])
async def vapi_webhook(request: Request) -> dict[str, object]:
    """VAPI server messages for a shop's voice assistant. Public by design; trusted only after the shop's bearer token checks out."""
    body = await request.body()
    if len(body) > 512 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload too large")
    event = vapi_events.parse(body)
    if event is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a VAPI message")
    found = await channel_webhook_service.find_integration("vapi", event.assistant_id)
    if found is None:
        raise _FORBIDDEN
    tenant_id, credentials = found
    adapter = factory.build_vapi(credentials)
    try:
        if not adapter.verify_webhook({key.lower(): value for key, value in request.headers.items()}, body):
            raise _FORBIDDEN
    finally:
        await adapter.aclose()
    return await voice_webhook_service.handle(tenant_id, event)
