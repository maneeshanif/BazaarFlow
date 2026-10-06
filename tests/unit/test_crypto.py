"""Credentials are encrypted at rest, rotatable, and never fall back to a public key in production."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.core import crypto
from app.core.settings import settings


def test_a_round_trip_returns_the_same_credentials_and_the_token_hides_them() -> None:
    credentials = {"account_sid": "ACaaaa", "auth_token": "super-secret-token"}
    token = crypto.encrypt_credentials(credentials)
    assert "super-secret-token" not in token and "ACaaaa" not in token
    assert crypto.decrypt_credentials(token) == credentials


def test_two_encryptions_of_the_same_value_differ() -> None:
    assert crypto.encrypt_credentials({"a": "b"}) != crypto.encrypt_credentials({"a": "b"})


def test_a_damaged_or_foreign_token_is_unreadable_not_a_crash() -> None:
    with pytest.raises(crypto.CredentialsUnreadable):
        crypto.decrypt_credentials("not-a-token")
    other = Fernet(Fernet.generate_key()).encrypt(b'{"a": "b"}').decode()
    with pytest.raises(crypto.CredentialsUnreadable):
        crypto.decrypt_credentials(other)


def test_a_key_can_be_rotated_without_losing_old_values(monkeypatch: pytest.MonkeyPatch) -> None:
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "INTEGRATIONS_ENCRYPTION_KEY", old)
    token = crypto.encrypt_credentials({"k": "v"})
    monkeypatch.setattr(settings, "INTEGRATIONS_ENCRYPTION_KEY", f"{new},{old}")
    assert crypto.decrypt_credentials(token) == {"k": "v"}  # the old key still reads it
    rotated = crypto.encrypt_credentials({"k": "v"})
    monkeypatch.setattr(settings, "INTEGRATIONS_ENCRYPTION_KEY", new)
    assert crypto.decrypt_credentials(rotated) == {"k": "v"}  # and new values need only the new key
    with pytest.raises(crypto.CredentialsUnreadable):
        crypto.decrypt_credentials(token)  # once the old key is dropped, old values are unreadable


@pytest.mark.parametrize("env", ["production", "staging"])
def test_production_and_staging_refuse_to_guess_a_key(monkeypatch: pytest.MonkeyPatch, env: str) -> None:
    monkeypatch.setattr(settings, "APP_ENV", env)
    monkeypatch.setattr(settings, "INTEGRATIONS_ENCRYPTION_KEY", "")
    with pytest.raises(crypto.EncryptionNotConfigured):
        crypto.encrypt_credentials({"a": "b"})


def test_a_malformed_key_is_reported_as_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "INTEGRATIONS_ENCRYPTION_KEY", "too-short")
    with pytest.raises(crypto.EncryptionNotConfigured):
        crypto.encrypt_credentials({"a": "b"})


def test_the_development_key_is_derived_and_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "INTEGRATIONS_ENCRYPTION_KEY", "")
    token = crypto.encrypt_credentials({"a": "b"})
    assert crypto.decrypt_credentials(token) == {"a": "b"}


def test_masking_shows_only_the_last_four_characters() -> None:
    assert crypto.mask_secret("abcdefghij") == "****ghij"
    assert crypto.mask_secret("abc") == "***"
    assert crypto.mask_secret("") == ""
