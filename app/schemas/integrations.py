"""Integration settings schemas (PRD F-018): connect a channel, see its status. A credential is write-only.

``IntegrationOut`` never carries a credential: only the status, the last error, the routing key and the last four
characters of the saved token, so an owner can recognise which one is saved.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Provider = Literal["whatsapp_twilio", "whatsapp_meta", "facebook", "instagram", "vapi"]
Status = Literal["not_connected", "pending", "connected", "error", "revoked"]

PROVIDERS: tuple[str, ...] = ("whatsapp_twilio", "whatsapp_meta", "facebook", "instagram", "vapi")
AVAILABLE: frozenset[str] = frozenset({"whatsapp_twilio", "facebook"})  # the rest arrive in Phase 3 or later
LABELS: dict[str, str] = {
    "whatsapp_twilio": "WhatsApp (Twilio sandbox)",
    "whatsapp_meta": "WhatsApp (Meta Cloud API)",
    "facebook": "Facebook Page",
    "instagram": "Instagram",
    "vapi": "Voice (VAPI)",
}


class TwilioCredentials(BaseModel):
    """The shop's own Twilio account. The Account SID is also the key an inbound webhook is routed by."""

    model_config = ConfigDict(extra="forbid")

    account_sid: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^AC[0-9a-fA-F]{32}$")]
    auth_token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=16, max_length=64)]
    whatsapp_number: Annotated[str, Field(pattern=r"^\+[1-9][0-9]{7,14}$")] | None = None  # defaults to the sandbox number


class FacebookCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_id: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9]{5,30}$")]
    access_token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=600)]


class ConnectRequest(BaseModel):
    """``credentials`` is checked against the provider's own shape in the service, so the error names the right field."""

    model_config = ConfigDict(extra="forbid")

    credentials: dict[str, str]


class IntegrationOut(BaseModel):
    provider: Provider
    label: str
    available: bool  # false: not built yet, shown as "coming soon"
    status: Status
    external_id: str | None
    token_hint: str | None  # "****abcd"
    last_error: str | None
    reconnect_required: bool  # the provider refused the saved credential: paste a new one
    connected_at: datetime | None
    webhook_url: str | None  # where to point the provider (WhatsApp only)


class WebhookResult(BaseModel):
    status: Literal["ok", "ignored"]
