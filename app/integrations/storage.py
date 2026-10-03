"""File storage behind one interface (PRD I-007, build-plan task 50).

Everything that stores a file (product photos, marketing images) goes through ``StorageAdapter``. Two adapters:

* ``SupabaseStorage``: Supabase Storage over REST with the service key. The key exists only in the API host's
  environment, never in the browser. Files are private; the browser gets a short-lived signed URL.
* ``FakeStorage``: in memory, for tests and local demos. It refuses to load in production.

Every key starts with the tenant id, so one shop's files can never be named by another shop's request. Uploads
retry on a timeout or a 5xx, and uploading the same key twice with the same bytes is a success (a duplicate delivery),
so a retry can never turn into an error.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Protocol, runtime_checkable
from urllib.parse import quote

import httpx

from app.core.settings import settings

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class StorageError(Exception):
    """A storage failure with a sentence a person can act on."""


class StorageNotConfigured(StorageError):
    """No storage is set up for this environment."""


class FileRejected(StorageError):
    """The file itself is not acceptable (type or size)."""


def object_key(tenant_id: uuid.UUID, content_type: str, data: bytes) -> str:
    """`<tenant>/<sha256 prefix>.<ext>`: the same picture uploaded twice lands on the same key."""
    ext = ALLOWED_TYPES.get(content_type)
    if ext is None:
        raise FileRejected("Only JPEG, PNG or WebP pictures can be uploaded.")
    if not data:
        raise FileRejected("The file is empty.")
    if len(data) > MAX_BYTES:
        raise FileRejected("The picture is larger than 5 MB.")
    return f"{tenant_id}/{hashlib.sha256(data).hexdigest()[:32]}.{ext}"


_KEY = re.compile(r"^[0-9a-f-]{36}/[0-9a-f]{32}\.(jpg|png|webp)$")


def check_key(tenant_id: uuid.UUID, key: str) -> str:
    """A key a caller names must be well formed and inside its own shop's folder."""
    if not _KEY.match(key) or not key.startswith(f"{tenant_id}/"):
        raise FileRejected("That file does not belong to this shop.")
    return key


@runtime_checkable
class StorageAdapter(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str: ...
    async def signed_url(self, key: str, expires_in: int | None = None) -> str: ...
    async def delete(self, key: str) -> None: ...


class FakeStorage:
    """In-memory storage with the same behaviour the real one promises."""

    def __init__(self) -> None:
        self.files: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        existing = self.files.get(key)
        if existing is not None and existing[0] != data:
            raise StorageError("A different file already uses that name.")
        self.files[key] = (data, content_type)
        return key

    async def signed_url(self, key: str, expires_in: int | None = None) -> str:
        if key not in self.files:
            raise StorageError("That file no longer exists.")
        return f"http://storage.local/{quote(key)}?expires={expires_in or settings.STORAGE_SIGNED_URL_SECONDS}"

    async def delete(self, key: str) -> None:
        self.files.pop(key, None)


class SupabaseStorage:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise StorageNotConfigured("File storage is not set up. Ask the person who runs the server.")
        self._base = settings.SUPABASE_URL.rstrip("/") + "/storage/v1"
        self._bucket = settings.STORAGE_BUCKET
        self._headers = {
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            "apikey": settings.SUPABASE_SERVICE_KEY,
        }
        self._client = client or httpx.AsyncClient(timeout=settings.STORAGE_TIMEOUT_SECONDS)

    async def _send(
        self, method: str, path: str, extra_headers: dict[str, str] | None = None, **kwargs: object
    ) -> httpx.Response:
        """One request with retries on a timeout, a dropped connection or a 5xx. Anything else is final."""
        headers = {**self._headers, **(extra_headers or {})}
        last = "no answer"
        for _ in range(settings.STORAGE_MAX_RETRIES + 1):
            try:
                response = await self._client.request(method, f"{self._base}{path}", headers=headers, **kwargs)  # type: ignore[arg-type]
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last = type(exc).__name__
                continue
            if response.status_code >= 500:
                last = f"HTTP {response.status_code}"
                continue
            return response
        raise StorageError(f"File storage did not answer ({last}). Try again in a moment.")

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        response = await self._send(
            "POST",
            f"/object/{self._bucket}/{quote(key)}",
            content=data,
            extra_headers={"Content-Type": content_type, "x-upsert": "false"},
        )
        if response.status_code in (200, 201):
            return key
        if response.status_code in (400, 409) and "Duplicate" in response.text:
            # a duplicate delivery: the key is a hash of the bytes, so what is there is what we sent
            return key
        raise StorageError("The file could not be saved.")

    async def signed_url(self, key: str, expires_in: int | None = None) -> str:
        seconds = expires_in or settings.STORAGE_SIGNED_URL_SECONDS
        response = await self._send("POST", f"/object/sign/{self._bucket}/{quote(key)}", json={"expiresIn": seconds})
        if response.status_code == 404:
            raise StorageError("That file no longer exists.")
        if response.status_code != 200:
            raise StorageError("A link to the file could not be made.")
        return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1{response.json()['signedURL']}"

    async def delete(self, key: str) -> None:
        response = await self._send("DELETE", f"/object/{self._bucket}/{quote(key)}")
        if response.status_code not in (200, 404):
            raise StorageError("The file could not be deleted.")


_fake = FakeStorage()


def get_storage() -> StorageAdapter:
    provider = settings.STORAGE_PROVIDER.lower()
    if provider == "fake":
        if settings.APP_ENV in {"production", "staging"}:
            raise StorageNotConfigured("The in-memory storage is for tests and local demos only")
        return _fake
    if provider == "supabase":
        return SupabaseStorage()
    raise StorageNotConfigured(f"STORAGE_PROVIDER must be fake or supabase, not {settings.STORAGE_PROVIDER!r}")
