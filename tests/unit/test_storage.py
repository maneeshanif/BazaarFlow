"""Task 50 acceptance (PRD I-007): the storage adapter against recorded Supabase responses (httpx MockTransport).

Happy path, a timeout, an error response and a duplicate delivery each have a test, plus the tenant-scoping rules.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from app.core.settings import settings
from app.integrations import storage
from app.integrations.storage import FakeStorage, FileRejected, StorageError, StorageNotConfigured, SupabaseStorage

TENANT = uuid.uuid4()
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture(autouse=True)
def supabase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "service-key")
    monkeypatch.setattr(settings, "STORAGE_BUCKET", "bazaarflow")
    monkeypatch.setattr(settings, "STORAGE_MAX_RETRIES", 2)


def adapter(handler: httpx.MockTransport) -> SupabaseStorage:
    return SupabaseStorage(httpx.AsyncClient(transport=handler))


async def test_upload_sends_the_service_key_and_returns_the_key() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"Key": "bazaarflow/x"})

    key = storage.object_key(TENANT, "image/png", PNG)
    assert key.startswith(f"{TENANT}/") and key.endswith(".png")
    assert await adapter(httpx.MockTransport(handle)).put(key, PNG, "image/png") == key
    request = seen[0]
    assert (
        request.method == "POST" and request.url.path == f"/storage/v1/object/bazaarflow/{TENANT}/{key.split('/')[1]}"
    )
    assert request.headers["authorization"] == "Bearer service-key" and request.headers["x-upsert"] == "false"
    assert request.content == PNG


async def test_a_signed_url_is_short_lived_and_absolute() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path.startswith("/storage/v1/object/sign/bazaarflow/")
        assert request.read() == b'{"expiresIn":600}'
        return httpx.Response(200, json={"signedURL": "/object/sign/bazaarflow/k.png?token=abc"})

    url = await adapter(httpx.MockTransport(handle)).signed_url("k.png")
    assert url == "https://proj.supabase.co/storage/v1/object/sign/bazaarflow/k.png?token=abc"


async def test_a_timeout_is_retried_and_then_reported_in_words() -> None:
    calls = 0

    def slow(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(StorageError, match="did not answer"):
        await adapter(httpx.MockTransport(slow)).put("t/k.png", PNG, "image/png")
    assert calls == 3  # the first try and two retries

    attempts = iter([httpx.ConnectTimeout("x"), None])

    def recovers(request: httpx.Request) -> httpx.Response:
        step = next(attempts)
        if step is not None:
            raise step
        return httpx.Response(200, json={})

    assert await adapter(httpx.MockTransport(recovers)).put("t/k.png", PNG, "image/png") == "t/k.png"


async def test_an_error_response_is_not_retried_and_never_leaks_the_provider_text() -> None:
    calls = 0

    def refuse(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(403, json={"message": "new row violates row-level security policy for bucket xyz"})

    with pytest.raises(StorageError) as excinfo:
        await adapter(httpx.MockTransport(refuse)).put("t/k.png", PNG, "image/png")
    assert calls == 1 and str(excinfo.value) == "The file could not be saved." and "bucket" not in str(excinfo.value)

    with pytest.raises(StorageError, match="did not answer"):
        await adapter(httpx.MockTransport(lambda r: httpx.Response(503))).delete("t/k.png")


async def test_a_duplicate_delivery_is_a_success() -> None:
    def duplicate(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409, json={"statusCode": "409", "error": "Duplicate", "message": "The resource already exists"}
        )

    assert await adapter(httpx.MockTransport(duplicate)).put("t/k.png", PNG, "image/png") == "t/k.png"


async def test_a_missing_file_is_explained_and_deleting_a_missing_file_is_fine() -> None:
    with pytest.raises(StorageError, match="no longer exists"):
        await adapter(httpx.MockTransport(lambda r: httpx.Response(404))).signed_url("t/k.png")
    await adapter(httpx.MockTransport(lambda r: httpx.Response(404))).delete("t/k.png")


def test_keys_are_scoped_to_the_shop_and_files_are_checked() -> None:
    key = storage.object_key(TENANT, "image/webp", PNG)
    assert storage.object_key(TENANT, "image/webp", PNG) == key  # the same picture, the same key
    assert storage.check_key(TENANT, key) == key
    with pytest.raises(FileRejected, match="does not belong"):
        storage.check_key(uuid.uuid4(), key)
    with pytest.raises(FileRejected, match="does not belong"):
        storage.check_key(TENANT, f"{TENANT}/../../other/secret.png")
    with pytest.raises(FileRejected, match="JPEG, PNG or WebP"):
        storage.object_key(TENANT, "application/pdf", PNG)
    with pytest.raises(FileRejected, match="empty"):
        storage.object_key(TENANT, "image/png", b"")
    with pytest.raises(FileRejected, match="5 MB"):
        storage.object_key(TENANT, "image/png", b"0" * (storage.MAX_BYTES + 1))


async def test_the_fake_behaves_like_the_real_one() -> None:
    fake = FakeStorage()
    key = storage.object_key(TENANT, "image/png", PNG)
    await fake.put(key, PNG, "image/png")
    await fake.put(key, PNG, "image/png")  # a duplicate delivery
    assert (await fake.signed_url(key)).startswith("http://storage.local/")
    with pytest.raises(StorageError, match="different file"):
        await fake.put(key, PNG + b"1", "image/png")
    await fake.delete(key)
    await fake.delete(key)
    with pytest.raises(StorageError, match="no longer exists"):
        await fake.signed_url(key)


def test_the_provider_switch_and_the_production_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "fake")
    monkeypatch.setattr(settings, "APP_ENV", "development")
    assert isinstance(storage.get_storage(), FakeStorage)
    monkeypatch.setattr(settings, "APP_ENV", "production")
    with pytest.raises(StorageNotConfigured, match="tests and local demos"):
        storage.get_storage()
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "")
    with pytest.raises(StorageNotConfigured, match="not set up"):
        storage.get_storage()
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "s3")
    with pytest.raises(StorageNotConfigured, match="fake or supabase"):
        storage.get_storage()
