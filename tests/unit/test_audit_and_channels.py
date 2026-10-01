"""Fast tests: audit masking and the channel adapter interface."""

from __future__ import annotations

import uuid

import pytest

from app.core.audit import MASK, mask_email, mask_sensitive
from app.integrations.channels import AdapterRegistry, ChannelAdapter, FakeChannelAdapter


def test_mask_sensitive_hides_secret_looking_keys_at_any_depth() -> None:
    masked = mask_sensitive(
        {
            "email": "a@b.com",
            "password": "hunter2",
            "nested": {"access_token": "abc", "ok": 1, "items": [{"api_key": "k", "n": 2}]},
            "Authorization": "Bearer x",
            "credentials_enc": "blob",
        }
    )
    assert masked["email"] == "a@b.com"
    assert masked["password"] == masked["Authorization"] == masked["credentials_enc"] == MASK
    assert masked["nested"]["access_token"] == MASK
    assert masked["nested"]["ok"] == 1
    assert masked["nested"]["items"] == [{"api_key": MASK, "n": 2}]


def test_mask_email_keeps_only_the_first_letter() -> None:
    assert mask_email("ali@example.com") == "a***@example.com"
    assert mask_email("not-an-email") == MASK


def test_fake_adapter_implements_the_channel_interface() -> None:
    assert isinstance(FakeChannelAdapter(), ChannelAdapter)


async def test_send_is_idempotent_on_the_idempotency_key() -> None:
    adapter = FakeChannelAdapter()
    tenant = uuid.uuid4()
    first = await adapter.send(tenant, "+923001234567", "hello", idempotency_key="k1")
    again = await adapter.send(tenant, "+923001234567", "hello", idempotency_key="k1")
    other = await adapter.send(tenant, "+923001234567", "hello", idempotency_key="k2")
    assert first == again
    assert other.provider_message_id != first.provider_message_id
    assert len(adapter.sent) == 2


async def test_webhook_signature_is_checked_before_parsing() -> None:
    adapter = FakeChannelAdapter()
    assert adapter.verify_webhook({"x-signature": "fake-secret"}, b"hi") is True
    assert adapter.verify_webhook({"x-signature": "nope"}, b"hi") is False
    message = await adapter.receive({"x-sender": "+923000000000"}, b"hi")
    assert message is not None and message.text == "hi"
    assert await adapter.receive({}, b"") is None


def test_registry_returns_registered_adapters_and_rejects_unknown_ones() -> None:
    registry = AdapterRegistry()
    adapter = FakeChannelAdapter(channel="whatsapp")
    registry.register(adapter)
    assert registry.get("whatsapp") is adapter
    with pytest.raises(LookupError):
        registry.get("telegram")
    with pytest.raises(TypeError):
        registry.register(object())  # type: ignore[arg-type]
