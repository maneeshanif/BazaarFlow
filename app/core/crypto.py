"""Encryption of integration credentials at rest (PRD §14, §36: tokens are encrypted, write-only, masked in logs).

``tenant_integrations.credentials_enc`` holds a Fernet token (AES-128-CBC + HMAC-SHA256, authenticated). The key comes
from ``INTEGRATIONS_ENCRYPTION_KEY``: one or more urlsafe-base64 32-byte keys separated by commas. The first encrypts;
every key can decrypt, so a key is rotated by putting the new one first, waiting for rows to be re-saved, then dropping
the old one. Outside production and staging a missing key is derived from ``SECRET_KEY`` so local work and tests need no
setup; in production and staging a missing key is an error at the moment a credential is stored or read, never a silent
fallback to a key that is public in the repository.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.settings import settings


class EncryptionNotConfigured(RuntimeError):
    """No usable ``INTEGRATIONS_ENCRYPTION_KEY`` in an environment that requires one."""


class CredentialsUnreadable(RuntimeError):
    """A stored credential cannot be decrypted (its key was removed or the value is damaged): the owner must reconnect."""


def _keys() -> list[str]:
    configured = [k.strip() for k in settings.INTEGRATIONS_ENCRYPTION_KEY.split(",") if k.strip()]
    if configured:
        return configured
    if settings.APP_ENV in {"production", "staging"}:
        raise EncryptionNotConfigured("set INTEGRATIONS_ENCRYPTION_KEY before connecting an integration")
    derived = hashlib.sha256(f"{settings.SECRET_KEY}|integrations".encode()).digest()
    return [base64.urlsafe_b64encode(derived).decode()]


def _fernet() -> MultiFernet:
    try:
        return MultiFernet([Fernet(key) for key in _keys()])
    except (ValueError, TypeError) as exc:
        raise EncryptionNotConfigured("INTEGRATIONS_ENCRYPTION_KEY is not a valid key (use Fernet.generate_key())") from exc


def encrypt_credentials(credentials: dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(credentials, separators=(",", ":"), sort_keys=True).encode()).decode()


def decrypt_credentials(token: str) -> dict[str, Any]:
    try:
        data = json.loads(_fernet().decrypt(token.encode()))
    except (InvalidToken, ValueError) as exc:
        raise CredentialsUnreadable("the stored credentials cannot be read; reconnect the integration") from exc
    if not isinstance(data, dict):
        raise CredentialsUnreadable("the stored credentials are not in the expected form; reconnect the integration")
    return data


def mask_secret(value: str) -> str:
    """Show only the last four characters of a secret, for an owner who needs to recognise which one is saved."""
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * 4}{value[-4:]}"
