"""Task 84: the Facebook Graph adapter against recorded responses (happy path, timeout, error, duplicate delivery)."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from urllib.parse import parse_qsl

import httpx
import pytest

from app.integrations.channels import ChannelAdapter
from app.integrations.facebook_graph import FacebookGraphAdapter
from app.integrations.http import ProviderError
from tests.unit.provider_support import Script, Sleeps, json_response

PAGE = "1234567890"
TOKEN = "EAAB-page-token-for-tests"
TENANT = uuid.uuid4()


def adapter(script: Script, sleeps: Sleeps | None = None, app_secret: str = "") -> FacebookGraphAdapter:
    return FacebookGraphAdapter(PAGE, TOKEN, app_secret=app_secret, transport=script.transport, sleep=sleeps or Sleeps())


def test_it_implements_the_channel_adapter_interface() -> None:
    assert isinstance(adapter(Script()), ChannelAdapter)


async def test_connect_checks_the_page_answers_with_its_own_id() -> None:
    script = Script(json_response(200, "fb_page.json"))
    assert await adapter(script).connect(TENANT, {}) == PAGE
    request = script.requests[0]
    assert request.url.path == f"/v21.0/{PAGE}" and request.url.params["fields"] == "id,name"


async def test_connect_refuses_a_token_that_belongs_to_another_page() -> None:
    script = Script(httpx.Response(200, json={"id": "999", "name": "Other"}))
    with pytest.raises(ProviderError) as caught:
        await adapter(script).connect(TENANT, {})
    assert caught.value.kind == "auth"


async def test_publish_text_posts_to_the_feed_and_returns_the_post_id() -> None:
    script = Script(json_response(200, "fb_post_created.json"))
    result = await adapter(script).publish_text("Eid sale: 20% off", idempotency_key="post-1")
    assert result.ok and result.provider_message_id == "1234567890_9876543210"
    request = script.requests[0]
    assert request.method == "POST" and request.url.path == f"/v21.0/{PAGE}/feed"
    form = dict(parse_qsl(request.content.decode()))
    assert form == {"message": "Eid sale: 20% off", "access_token": TOKEN}


async def test_publish_image_posts_the_picture_url_with_its_caption_and_prefers_the_post_id() -> None:
    script = Script(json_response(200, "fb_photo_created.json"))
    result = await adapter(script).publish_image("https://images.example/shirt.jpg", "New shirts", idempotency_key="img-1")
    assert result.provider_message_id == "1234567890_2222222222"
    assert script.requests[0].url.path == f"/v21.0/{PAGE}/photos"
    assert dict(parse_qsl(script.requests[0].content.decode()))["url"] == "https://images.example/shirt.jpg"


async def test_a_duplicate_publish_with_the_same_key_posts_once() -> None:
    script = Script(json_response(200, "fb_post_created.json"))
    fb = adapter(script)
    first = await fb.publish_text("Hello", idempotency_key="dup")
    second = await fb.publish_text("Hello", idempotency_key="dup")
    assert first == second and len(script.requests) == 1


async def test_a_timeout_is_retried_three_times_then_raised() -> None:
    script = Script(httpx.ConnectTimeout("slow"))
    sleeps = Sleeps()
    with pytest.raises(ProviderError) as caught:
        await adapter(script, sleeps).publish_text("Hello", idempotency_key="t")
    assert caught.value.kind == "timeout" and len(script.requests) == 3


async def test_an_expired_token_is_an_auth_error_that_is_not_retried_and_hides_the_token() -> None:
    script = Script(json_response(400, "fb_error_190.json"))
    with pytest.raises(ProviderError) as caught:
        await adapter(script).publish_text("Hello", idempotency_key="e")
    assert caught.value.needs_reconnect and caught.value.code == "190" and len(script.requests) == 1
    assert TOKEN not in str(caught.value)


async def test_throttling_is_waited_out_and_the_post_then_goes_through() -> None:
    script = Script(json_response(400, "fb_error_rate_4.json"), json_response(200, "fb_post_created.json"))
    result = await adapter(script).publish_text("Hello", idempotency_key="r")
    assert result.ok and len(script.requests) == 2


async def test_a_post_with_no_id_in_the_answer_is_an_error_not_a_silent_success() -> None:
    script = Script(httpx.Response(200, json={}))
    with pytest.raises(ProviderError):
        await adapter(script).publish_text("Hello", idempotency_key="n")


async def test_comments_are_listed_with_author_and_text_and_a_missing_author_is_allowed() -> None:
    script = Script(json_response(200, "fb_comments.json"))
    comments = await adapter(script).fetch_comments("1234567890_2222222222")
    assert [(c.id, c.author, c.message) for c in comments] == [
        ("2222222222_3333333333", "Sara", "What is the price?"),
        ("2222222222_4444444444", None, "Nice!"),
    ]
    assert script.requests[0].url.path == "/v21.0/1234567890_2222222222/comments"


async def test_a_reply_goes_to_the_comment_and_is_deduplicated() -> None:
    script = Script(httpx.Response(200, json={"id": "2222222222_5555555555"}))
    fb = adapter(script)
    first = await fb.reply_to_comment("2222222222_3333333333", "Rs 2,500", idempotency_key="reply-1")
    again = await fb.reply_to_comment("2222222222_3333333333", "Rs 2,500", idempotency_key="reply-1")
    assert first == again and len(script.requests) == 1
    assert script.requests[0].url.path == "/v21.0/2222222222_3333333333/comments"


async def test_a_short_lived_token_is_exchanged_for_a_long_lived_one() -> None:
    script = Script(json_response(200, "fb_long_lived_token.json"))
    token = await adapter(script).exchange_token("app-id", "app-secret", "short-token")
    assert token.access_token == "EAABlongLivedTokenExampleOnly" and token.expires_in == 5183944
    params = script.requests[0].url.params
    assert params["grant_type"] == "fb_exchange_token" and params["fb_exchange_token"] == "short-token"


async def test_the_facebook_channel_does_not_receive_inbound_messages() -> None:
    assert await adapter(Script()).receive({}, b"{}") is None


def test_the_webhook_signature_is_checked_with_the_app_secret() -> None:
    secret = "app-secret"
    body = b'{"entry": []}'
    good = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    fb = adapter(Script(), app_secret=secret)
    assert fb.verify_webhook({"X-Hub-Signature-256": good}, body) is True
    assert fb.verify_webhook({"X-Hub-Signature-256": "sha256=bad"}, body) is False
    assert fb.verify_webhook({}, body) is False
    assert adapter(Script()).verify_webhook({"X-Hub-Signature-256": good}, body) is False  # no secret configured: refuse
