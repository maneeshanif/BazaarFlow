"""JWT creation/verification + password hashing (direct bcrypt).

Usage:
    from app.core.security import create_access_token, verify_token, hash_password, verify_password
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from app.core.settings import settings

# ---------------------------------------------------------------------------
# Password hashing (direct bcrypt to avoid passlib wrap-bug incompatibility)
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of plain password."""
    # Truncate to 72 bytes (bcrypt max length limit)
    pwd_bytes = plain.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain password matches hashed."""
    pwd_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


async def ahash_password(plain: str) -> str:
    """``hash_password`` on a worker thread: bcrypt takes ~100-300 ms and must not block the event loop."""
    return await asyncio.to_thread(hash_password, plain)


async def averify_password(plain: str, hashed: str) -> bool:
    """``verify_password`` on a worker thread."""
    return await asyncio.to_thread(verify_password, plain, hashed)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
_ALGORITHM = "HS256"


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Create a signed JWT.

    Args:
        subject:       Usually the user UUID or vendor_id.
        expires_delta: Custom TTL; defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.
        extra_claims:  Additional claims merged into the payload.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, **(extra_claims or {})}
    return str(jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM))


def verify_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT.

    Returns the decoded payload dict.
    Raises jwt.PyJWTError on invalid / expired tokens.
    """
    payload: dict[str, Any] = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
    return payload
