"""Per-shop provider connections (PRD F-018, build-plan tasks 59, 62, 77): connect, disconnect, status, health.

A credential is checked with the provider before it is saved, stored encrypted (``app.core.crypto``) and never returned.
``adapter_for`` is how every other service reaches a provider: it refuses when the shop is not connected or the provider
refused the saved credential, so a paused integration stops costing calls until the owner pastes a new token.

When a provider fails, ``record_failure`` writes the shop's side of the defined degraded behaviour: a refused credential
moves the integration to ``error`` with a plain "reconnect" message; any other failure keeps it connected but records the
last error. Both leave an audit row (``integration.degraded``) and an error log line (provider, kind, status; never a
token), which is the alert (there is no email vendor in the PRD).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.crypto import (
    CredentialsUnreadable,
    EncryptionNotConfigured,
    decrypt_credentials,
    encrypt_credentials,
    mask_secret,
)
from app.core.problems import Conflict, DomainError
from app.core.tenancy import Principal
from app.integrations import factory
from app.integrations.http import ProviderError
from app.models.tenant import TenantIntegration
from app.schemas.integrations import (
    AVAILABLE,
    LABELS,
    PROVIDERS,
    FacebookCredentials,
    IntegrationOut,
    TwilioCredentials,
)

logger = logging.getLogger("bazaarflow.integrations")

_SCHEMAS: dict[str, type[BaseModel]] = {"whatsapp_twilio": TwilioCredentials, "facebook": FacebookCredentials}
_SECRET_FIELD = {"whatsapp_twilio": "auth_token", "facebook": "access_token"}
_NAMES = {"whatsapp_twilio": "Twilio", "facebook": "Facebook"}
RECONNECT = "The provider rejected the saved credential. Paste a new one to reconnect."


def _name(provider: str) -> str:
    return _NAMES.get(provider, LABELS.get(provider, provider))


async def _row(db: AsyncSession, tenant_id: uuid.UUID, provider: str) -> TenantIntegration | None:
    return (
        await db.execute(
            select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id, TenantIntegration.provider == provider)
        )
    ).scalar_one_or_none()


def _hint(provider: str, row: TenantIntegration) -> tuple[str | None, bool]:
    """The last four characters of the saved secret, and whether the stored value can still be read."""
    if not row.credentials_enc:
        return None, True
    try:
        secret = str(decrypt_credentials(row.credentials_enc).get(_SECRET_FIELD.get(provider, ""), ""))
    except (CredentialsUnreadable, EncryptionNotConfigured):
        return None, False
    return (mask_secret(secret) if secret else None), True


def _out(provider: str, row: TenantIntegration | None) -> IntegrationOut:
    webhook = factory.twilio_webhook_url() if provider == "whatsapp_twilio" else None
    if row is None:
        return IntegrationOut(
            provider=provider,  # type: ignore[arg-type]
            label=LABELS[provider],
            available=provider in AVAILABLE,
            status="not_connected",
            external_id=None,
            token_hint=None,
            last_error=None,
            reconnect_required=False,
            connected_at=None,
            webhook_url=webhook,
        )
    hint, readable = _hint(provider, row)
    return IntegrationOut(
        provider=provider,  # type: ignore[arg-type]
        label=LABELS[provider],
        available=provider in AVAILABLE,
        status=row.status if readable else "error",  # type: ignore[arg-type]
        external_id=row.external_id,
        token_hint=hint,
        last_error=row.last_error if readable else RECONNECT,
        reconnect_required=row.status == "error" or not readable,
        connected_at=row.connected_at,
        webhook_url=webhook,
    )


async def list_integrations(db: AsyncSession, principal: Principal) -> list[IntegrationOut]:
    rows = (await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == principal.tenant_id))).scalars().all()
    by_provider = {r.provider: r for r in rows}
    return [_out(p, by_provider.get(p)) for p in PROVIDERS]


def _validate(provider: str, raw: dict[str, str]) -> dict[str, Any]:
    if provider not in AVAILABLE:
        raise DomainError(f"{LABELS.get(provider, provider)} is not available yet", code="provider_not_available")
    try:
        return _SCHEMAS[provider].model_validate(raw).model_dump(exclude_none=True)
    except ValidationError as exc:
        errors = [{"field": ".".join(str(p) for p in e["loc"]) or "credentials", "message": str(e["msg"])} for e in exc.errors()]
        summary = "; ".join(f"{e['field']}: {e['message']}" for e in errors[:3])
        raise DomainError(summary, code="validation_failed", extra={"errors": errors}) from exc


def _explain(provider: str, error: ProviderError) -> DomainError:
    name = _name(provider)
    if error.kind == "auth":
        return DomainError(f"{name} did not accept these credentials. Check them and try again.", code="credentials_rejected")
    if error.kind == "client":
        return DomainError(f"{name} refused the request: {error.message}", code="provider_rejected")
    return DomainError(f"{name} is not answering right now. Try again in a few minutes.", code="provider_unavailable", status_code=502)


async def _external_id(provider: str, tenant_id: uuid.UUID, credentials: dict[str, Any]) -> str:
    adapter: Any = factory.build_twilio(credentials) if provider == "whatsapp_twilio" else factory.build_facebook(credentials)
    try:
        return str(await adapter.connect(tenant_id, credentials))
    finally:
        await adapter.aclose()


async def connect(db: AsyncSession, principal: Principal, provider: str, raw: dict[str, str]) -> IntegrationOut:
    """Check the credentials with the provider, then save them encrypted and mark the integration connected."""
    credentials = _validate(provider, raw)
    try:
        external_id = await _external_id(provider, principal.tenant_id, credentials)
    except ProviderError as error:
        raise _explain(provider, error) from error
    try:
        encrypted = encrypt_credentials(credentials)
    except EncryptionNotConfigured as exc:
        raise DomainError("Saving credentials is not set up on this server yet. Ask BazaarFlow support.", code="encryption_not_configured", status_code=503) from exc

    now = datetime.now(timezone.utc)
    row = await _row(db, principal.tenant_id, provider)
    try:
        async with db.begin_nested():  # a duplicate routing key must not poison the request transaction
            if row is None:
                row = TenantIntegration(tenant_id=principal.tenant_id, provider=provider)
                db.add(row)
            row.external_id = external_id
            row.credentials_enc = encrypted
            row.status = "connected"
            row.last_error = None
            row.connected_at = now
            await db.flush()
    except IntegrityError as exc:
        raise Conflict("This account is already connected to another shop", code="already_connected") from exc
    record_audit(
        db,
        "integration.connected",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="integration",
        entity_id=row.id,
        after={"provider": provider, "external_id": external_id},
    )
    return _out(provider, row)


async def disconnect(db: AsyncSession, principal: Principal, provider: str) -> IntegrationOut:
    row = await _row(db, principal.tenant_id, provider)
    if row is not None and row.status != "revoked":
        row.status = "revoked"
        row.credentials_enc = None
        row.external_id = None  # frees the routing key
        row.last_error = None
        await db.flush()
        record_audit(
            db,
            "integration.disconnected",
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
            entity="integration",
            entity_id=row.id,
            after={"provider": provider},
        )
    return _out(provider, row)


async def adapter_for(db: AsyncSession, tenant_id: uuid.UUID, provider: str) -> Any:
    """The shop's adapter for ``provider``, or a plain error when it is not connected or its credential was refused."""
    row = await _row(db, tenant_id, provider)
    name = _name(provider)
    if row is None or row.status in {"pending", "revoked"} or not row.credentials_enc:
        raise DomainError(f"{name} is not connected. Connect it in Settings -> Integrations.", code="integration_not_connected")
    if row.status == "error":
        raise DomainError(f"{name} needs to be reconnected in Settings -> Integrations.", code="integration_reconnect", status_code=409)
    try:
        credentials = decrypt_credentials(row.credentials_enc)
    except (CredentialsUnreadable, EncryptionNotConfigured) as exc:
        raise DomainError(f"{name} needs to be reconnected in Settings -> Integrations.", code="integration_reconnect", status_code=409) from exc
    return factory.build_twilio(credentials) if provider == "whatsapp_twilio" else factory.build_facebook(credentials)


async def record_failure(db: AsyncSession, tenant_id: uuid.UUID, provider: str, error: ProviderError) -> None:
    """The degraded-behaviour half of a provider failure: remember it, tell the owner, leave an audit row and a log line."""
    row = await _row(db, tenant_id, provider)
    if row is None:
        return
    if error.kind == "auth":
        row.status = "error"
        row.last_error = RECONNECT
    else:
        row.last_error = f"{_name(provider)} is not answering ({error.kind}). We will keep trying."
    await db.flush()
    record_audit(
        db,
        "integration.degraded",
        tenant_id=tenant_id,
        actor_type="system",
        entity="integration",
        entity_id=row.id,
        after={"provider": provider, "kind": error.kind, "status": error.status, "integration_status": row.status},
    )
    logger.error(
        "integration degraded",
        extra={"provider": provider, "kind": error.kind, "http_status": error.status, "tenant_id": str(tenant_id)},
    )


async def record_success(db: AsyncSession, tenant_id: uuid.UUID, provider: str) -> None:
    row = await _row(db, tenant_id, provider)
    if row is not None and row.status == "connected" and row.last_error:
        row.last_error = None
        await db.flush()
