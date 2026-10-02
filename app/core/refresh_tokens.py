"""Opaque rotating refresh tokens (PRD §14).

Only the SHA-256 hash is stored. Using a token rotates it (the old one is revoked and points at its
replacement). Presenting an already-revoked token is treated as theft: every token of that user is revoked.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.models.security import RefreshToken


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def issue(session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    """Create a refresh token for a session and return the raw value (the only time it is visible)."""
    raw = secrets.token_urlsafe(48)
    session.add(
        RefreshToken(
            user_id=user_id,
            tenant_id=tenant_id,
            token_hash=_hash(raw),
            expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    await session.flush()
    return raw


class RefreshError(Exception):
    """The presented refresh token is unknown, expired, revoked or reused."""


async def rotate(session: AsyncSession, raw: str) -> tuple[RefreshToken, str]:
    """Validate ``raw``, revoke it, and return the old row plus a fresh raw token for the same session."""
    # FOR UPDATE: two concurrent refreshes with the same token must not both succeed (theft detection relies on it)
    row = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw)).with_for_update())
    ).scalar_one_or_none()
    if row is None:
        raise RefreshError("unknown token")
    if row.revoked_at is not None:
        # Reuse of a rotated/revoked token: assume it leaked and end every session of this user.
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=_now())
        )
        await session.flush()
        raise RefreshError("token reuse detected")
    if row.expires_at <= _now():
        raise RefreshError("expired")
    new_raw = await issue(session, row.user_id, row.tenant_id)
    row.revoked_at = _now()
    row.replaced_by = (
        await session.execute(select(RefreshToken.id).where(RefreshToken.token_hash == _hash(new_raw)))
    ).scalar_one()
    await session.flush()
    return row, new_raw


async def revoke(session: AsyncSession, raw: str) -> RefreshToken | None:
    """Revoke one token (logout). Unknown tokens are ignored so logout is idempotent."""
    row = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw)).with_for_update())
    ).scalar_one_or_none()
    if row is not None and row.revoked_at is None:
        row.revoked_at = _now()
        await session.flush()
    return row
