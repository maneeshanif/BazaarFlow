"""Inbound provider webhooks (PRD W-003, build-plan tasks 61 and 83): find the shop, verify the signature, drop replays.

No shop is known when a webhook arrives, so the integration is looked up by the routing key the provider sends (for
Twilio, the Account SID) through a policy that opens exactly the row whose ``external_id`` equals that key. The signature
is then checked with *that shop's* saved credential, so an unknown key and a bad signature look the same from outside.
Each event is recorded by its provider id before it is processed; the unique key makes a replay a no-op.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.crypto import CredentialsUnreadable, EncryptionNotConfigured, decrypt_credentials
from app.core.tenancy import anonymous_session, tenant_session
from app.integrations.channels import InboundMessage
from app.models.conversation import WebhookEvent
from app.models.tenant import TenantIntegration
from app.services import inbox_service

logger = logging.getLogger("bazaarflow.webhooks")


async def find_integration(provider: str, external_id: str) -> tuple[uuid.UUID, dict[str, Any]] | None:
    """The connected shop (and its decrypted credentials) behind a webhook routing key, or None."""
    if not external_id or len(external_id) > 255:
        return None
    async with anonymous_session() as session:
        if session.get_bind().dialect.name == "postgresql":
            await session.execute(text("SELECT set_config('app.webhook_external_id', :v, true)"), {"v": external_id})
        row = (
            await session.execute(
                select(TenantIntegration).where(
                    TenantIntegration.provider == provider,
                    TenantIntegration.external_id == external_id,
                    TenantIntegration.status == "connected",
                )
            )
        ).scalar_one_or_none()
    if row is None or not row.credentials_enc:
        return None
    try:
        return row.tenant_id, decrypt_credentials(row.credentials_enc)
    except (CredentialsUnreadable, EncryptionNotConfigured):
        logger.error("webhook credentials unreadable", extra={"provider": provider, "tenant_id": str(row.tenant_id)})
        return None


async def handle_inbound(tenant_id: uuid.UUID, provider: str, inbound: InboundMessage, *, contact_name: str | None) -> str:
    """Store the message, answer it if the thread is in AI mode. Returns ``ok`` or ``ignored`` (a replay)."""
    async with tenant_session(tenant_id) as db:
        try:
            async with db.begin_nested():
                db.add(WebhookEvent(tenant_id=tenant_id, provider=provider, event_id=inbound.provider_message_id))
                await db.flush()
        except IntegrityError:
            return "ignored"
        conversation, message = await inbox_service.receive_inbound(db, tenant_id, inbound, contact_name=contact_name)
        await inbox_service.answer_with_ai(db, tenant_id, conversation, message)
    return "ok"
