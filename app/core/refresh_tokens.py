"""Opaque rotating refresh tokens (PRD §14).

Only the SHA-256 hash is stored. Using a token rotates it (the old one is revoked and points at its
replacement). Presenting an already-revoked token is treated as theft: every token of that user is revoked,
except inside a short grace window after a rotation (a lost response is not theft; REFRESH_REUSE_GRACE_SECONDS).
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


def _is_lost_response(row: RefreshToken) -> bool:
    grace = settings.REFRESH_REUSE_GRACE_SECONDS
    return (
        grace > 0
        and row.replaced_by is not None  # rotated, not revoked by logout or theft handling
        and row.revoked_at is not None
        and _now() - row.revoked_at <= timedelta(seconds=grace)
    )


async def _direct_live_successor(session: AsyncSession, row: RefreshToken) -> RefreshToken | None:
    """The direct successor of a rotated token if it is still live and the session has not expired, else None."""
    if row.replaced_by is None or row.expires_at <= _now():
        return None
    successor = (
        await session.execute(select(RefreshToken).where(RefreshToken.id == row.replaced_by).with_for_update())
    ).scalar_one_or_none()
    return successor if successor is not None and successor.revoked_at is None else None


async def _follow_to_live_head(session: AsyncSession, row: RefreshToken) -> RefreshToken | None:
    """Follow ``replaced_by`` from a rotated token to the token that is still live (None if the chain ended)."""
    current = row
    for _ in range(16):
        if current.replaced_by is None:
            return None
        nxt = (
            await session.execute(select(RefreshToken).where(RefreshToken.id == current.replaced_by).with_for_update())
        ).scalar_one_or_none()
        if nxt is None:
            return None
        if nxt.revoked_at is None:
            return nxt
        current = nxt
    return None


class RefreshError(Exception):
    """The presented refresh token is unknown, expired, revoked or reused."""


async def rotate(session: AsyncSession, raw: str) -> tuple[RefreshToken, str, bool]:
    """Validate ``raw``, revoke it, and return the old row, a fresh raw token for the same session, and whether
    this was a reuse tolerated by the grace window (the caller audits it)."""
    # FOR UPDATE: two concurrent refreshes with the same token must not both succeed (theft detection relies on it)
    row = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw)).with_for_update())
    ).scalar_one_or_none()
    if row is None:
        raise RefreshError("unknown token")
    if row.revoked_at is not None and _is_lost_response(row):
        # The response to a refresh never reached the client (reload, second tab). One replay is tolerated: hand out
        # a fresh token and supersede the successor whose response was lost, so there is still exactly one live token.
        # It is one-shot: if that successor is already gone (replayed before, rotated on, or logged out), it is theft.
        head = await _direct_live_successor(session, row)
        if head is not None:
            new_raw = await issue(session, row.user_id, row.tenant_id)
            head.revoked_at = _now()
            head.replaced_by = (
                await session.execute(select(RefreshToken.id).where(RefreshToken.token_hash == _hash(new_raw)))
            ).scalar_one()
            await session.flush()
            return row, new_raw, True
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
    return row, new_raw, False


async def revoke(session: AsyncSession, raw: str) -> RefreshToken | None:
    """Revoke one token (logout). Unknown tokens are ignored so logout is idempotent."""
    row = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw)).with_for_update())
    ).scalar_one_or_none()
    if row is not None and row.revoked_at is None:
        row.revoked_at = _now()
        await session.flush()
    elif row is not None and row.replaced_by is not None:
        # a stale token (its response was lost, or the client kept it): logging out must still end the session
        head = await _follow_to_live_head(session, row)
        if head is not None:
            head.revoked_at = _now()
            await session.flush()
    return row
