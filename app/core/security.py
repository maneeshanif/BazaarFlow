"""JWT creation/verification + password hashing (direct bcrypt).

Usage:
    from app.core.security import create_access_token, verify_token, hash_password, verify_password
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

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


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
_ALGORITHM = "HS256"


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
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
    payload: dict = {"sub": str(subject), "exp": expire, **(extra_claims or {})}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and validate a JWT.

    Returns the decoded payload dict.
    Raises jose.JWTError on invalid / expired tokens.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])