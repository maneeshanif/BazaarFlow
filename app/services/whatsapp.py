from app.core.settings import settings
"""Thin wrapper around the WhatsApp Business Cloud API."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

import httpx  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

_GRAPH_VERSION = settings.META_GRAPH_VERSION
_GRAPH_BASE = settings.META_GRAPH_BASE


class WhatsAppAPIError(Exception):
    """Raised when the Meta WhatsApp API rejects a request."""

    def __init__(self, message: str, *, status_code: Optional[int], payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


def _endpoint(phone_number_id: str) -> str:
    return f"{_GRAPH_BASE}/{_GRAPH_VERSION}/{phone_number_id}/messages"


def _mask_token(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}…{token[-4:]}"


def _extract_whatsapp_error(response: httpx.Response) -> Tuple[str, Dict[str, Any]]:
    """Return a readable error message and JSON payload from the WhatsApp API."""

    detail: Dict[str, Any] = {
        "status": response.status_code,
    }

    try:
        body = response.json()
        detail["body"] = body
    except ValueError:
        text = response.text.strip()
        if text:
            detail["body_text"] = text
        return (
            f"WhatsApp API error (status {response.status_code})",
            detail,
        )

    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        message = error.get("message") or "WhatsApp API error"
        meta: list[str] = []
        code = error.get("code")
        if code is not None:
            meta.append(f"code {code}")
        subcode = error.get("error_subcode")
        if subcode is not None:
            meta.append(f"subcode {subcode}")
        if meta:
            message = f"{message} ({', '.join(meta)})"
        return message, detail

    return (
        f"WhatsApp API error (status {response.status_code})",
        detail,
    )


async def send_text_message(
    *,
    client: httpx.AsyncClient,
    phone_number_id: str,
    access_token: str,
    to: str,
    body: str,
) -> Dict[str, Any]:
    """Send a text reply via the Cloud API."""

    url = _endpoint(phone_number_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }

    logger.debug(
        "Sending WhatsApp message to %s via %s (token=%s)",
        to,
        url,
        _mask_token(access_token),
    )

    try:
        response = await client.post(url, headers=headers, json=payload, timeout=30.0)
    except httpx.RequestError as exc:
        logger.warning("Network error while sending WhatsApp message: %s", exc)
        raise WhatsAppAPIError("Unable to reach WhatsApp API", status_code=None, payload={"reason": str(exc)}) from exc

    if response.is_error:
        message, detail = _extract_whatsapp_error(response)
        logger.warning(
            "WhatsApp API returned %s for recipient %s: %s",
            response.status_code,
            to,
            message,
        )
        raise WhatsAppAPIError(message, status_code=response.status_code, payload=detail)

    try:
        return response.json()
    except ValueError as exc:  # pragma: no cover - unexpected API behaviour
        logger.exception("Invalid JSON body from WhatsApp API: %s", response.text)
        raise WhatsAppAPIError(
            "Unexpected WhatsApp API response",
            status_code=response.status_code,
            payload={"body_text": response.text},
        ) from exc


async def validate_phone_number(
    *,
    client: httpx.AsyncClient,
    phone_number_id: str,
    access_token: str,
) -> Dict[str, Any]:
    """Verify provided credentials by hitting the Graph API."""

    url = f"{_GRAPH_BASE}/{_GRAPH_VERSION}/{phone_number_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"fields": "id,display_phone_number"}
    logger.debug(
        "Validating phone number %s via %s (token=%s)",
        phone_number_id,
        url,
        _mask_token(access_token),
    )
    response = await client.get(url, headers=headers, params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()


__all__ = ["send_text_message", "validate_phone_number", "WhatsAppAPIError"]
