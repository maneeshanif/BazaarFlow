"""Channel adapter interface (PRD §3.7 constraint 11).

Services and agents talk to WhatsApp, Facebook, Instagram and voice only through this interface, so a
provider (Twilio, Meta Cloud API, a BSP) can be swapped per tenant without touching business logic.
Concrete adapters (Twilio first, in phase 2) implement ``ChannelAdapter`` and register themselves here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class InboundMessage:
    """A provider-neutral inbound message; the caller resolves ``external_id`` to a tenant."""

    channel: str
    external_id: str
    sender: str
    text: str
    provider_message_id: str


@dataclass(frozen=True)
class SendResult:
    provider_message_id: str
    ok: bool = True
    error: str | None = None


@runtime_checkable
class ChannelAdapter(Protocol):
    channel: str

    async def connect(self, tenant_id: uuid.UUID, credentials: dict[str, Any]) -> str:
        """Validate a connection; returns the external id (phone number id, page id, ...)."""
        ...

    async def send(self, tenant_id: uuid.UUID, to: str, text: str, *, idempotency_key: str) -> SendResult:
        """Send one message. ``idempotency_key`` makes retries safe."""
        ...

    async def receive(self, headers: dict[str, str], body: bytes) -> InboundMessage | None:
        """Parse a webhook payload into an InboundMessage, or None if it is not a message event."""
        ...

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        """Check the provider's signature. Callers must reject the request when this is False."""
        ...


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ChannelAdapter] = {}

    def register(self, adapter: ChannelAdapter) -> None:
        if not isinstance(adapter, ChannelAdapter):
            raise TypeError("adapter does not implement ChannelAdapter")
        self._adapters[adapter.channel] = adapter

    def get(self, channel: str) -> ChannelAdapter:
        try:
            return self._adapters[channel]
        except KeyError as exc:
            raise LookupError(f"no adapter registered for channel {channel!r}") from exc


registry = AdapterRegistry()


@dataclass
class FakeChannelAdapter:
    """In-memory adapter for tests: records sends and dedupes on the idempotency key."""

    channel: str = "fake"
    secret: str = "fake-secret"
    sent: list[tuple[uuid.UUID, str, str]] = field(default_factory=list)
    _seen: dict[str, SendResult] = field(default_factory=dict)

    async def connect(self, tenant_id: uuid.UUID, credentials: dict[str, Any]) -> str:
        return str(credentials.get("external_id", "fake-external-id"))

    async def send(self, tenant_id: uuid.UUID, to: str, text: str, *, idempotency_key: str) -> SendResult:
        if idempotency_key in self._seen:
            return self._seen[idempotency_key]
        self.sent.append((tenant_id, to, text))
        result = SendResult(provider_message_id=f"fake-{len(self.sent)}")
        self._seen[idempotency_key] = result
        return result

    async def receive(self, headers: dict[str, str], body: bytes) -> InboundMessage | None:
        text = body.decode("utf-8")
        if not text:
            return None
        return InboundMessage(
            channel=self.channel,
            external_id=headers.get("x-external-id", "fake-external-id"),
            sender=headers.get("x-sender", "+920000000000"),
            text=text,
            provider_message_id=headers.get("x-message-id", "fake-in-1"),
        )

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        return headers.get("x-signature") == self.secret
