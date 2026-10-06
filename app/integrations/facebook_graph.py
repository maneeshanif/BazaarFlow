"""Facebook Graph API adapter (PRD I-003, build-plan task 84; scheduler workflow W-004).

One instance serves one shop's Facebook Page: it publishes a text or image post to the page feed, reads the comments of a
post, replies to a comment and trades a short-lived user token for a long-lived one. All HTTP goes through
``ProviderClient`` (timeout, retries, typed errors), and the token travels in the request body or query only, never in a
log line or an error message.

Graph has no idempotency key, so a publish with a key this instance has already seen returns the first post id; the
scheduler also records ``fb_post_id`` on the post before it ever publishes twice, which covers a restart.

Endpoints, as the legacy ``facebook_manager`` and Meta's Graph API reference use them: ``POST /{page_id}/feed`` (message),
``POST /{page_id}/photos`` (url, caption), ``GET /{post_id}/comments``, ``POST /{comment_id}/comments`` (message),
``GET /oauth/access_token?grant_type=fb_exchange_token``. An expired or revoked token is HTTP 400 with error code 190.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from app.integrations.channels import InboundMessage, SendResult
from app.integrations.http import ProviderClient, ProviderError, Sleep

CHANNEL = "facebook"
DEFAULT_BASE = "https://graph.facebook.com"
DEFAULT_VERSION = "v21.0"


@dataclass(frozen=True)
class PageComment:
    id: str
    message: str
    author: str | None
    created_time: str | None


@dataclass(frozen=True)
class LongLivedToken:
    access_token: str
    expires_in: int | None  # seconds; None when Facebook does not say (page tokens made from a long-lived token never expire)


class FacebookGraphAdapter:
    channel = CHANNEL

    def __init__(
        self,
        page_id: str,
        access_token: str,
        *,
        app_secret: str = "",
        base: str = DEFAULT_BASE,
        version: str = DEFAULT_VERSION,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep | None = None,
        retries: int = 3,
        timeout: float = 10.0,
    ) -> None:
        self._page_id = page_id
        self._token = access_token
        self._app_secret = app_secret
        self._http = ProviderClient("facebook", f"{base.rstrip('/')}/{version}", transport=transport, sleep=sleep, retries=retries, timeout=timeout)
        self._published: dict[str, SendResult] = {}

    async def aclose(self) -> None:
        await self._http.aclose()

    async def connect(self, tenant_id: uuid.UUID, credentials: dict[str, Any]) -> str:
        """Prove the page token works: the page must answer with the id we were given. Returns the page id."""
        response = await self._http.request("GET", f"/{self._page_id}", params={"fields": "id,name", "access_token": self._token})
        body = response.json()
        if str(body.get("id")) != self._page_id:
            raise ProviderError("facebook", "auth", "the token does not belong to this page")
        return self._page_id

    async def page_name(self) -> str | None:
        response = await self._http.request("GET", f"/{self._page_id}", params={"fields": "id,name", "access_token": self._token})
        name = response.json().get("name")
        return str(name) if name else None

    async def publish_text(self, message: str, *, idempotency_key: str) -> SendResult:
        return await self._publish(f"/{self._page_id}/feed", {"message": message}, idempotency_key)

    async def publish_image(self, image_url: str, caption: str, *, idempotency_key: str) -> SendResult:
        return await self._publish(f"/{self._page_id}/photos", {"url": image_url, "caption": caption}, idempotency_key)

    async def _publish(self, path: str, fields: dict[str, str], idempotency_key: str) -> SendResult:
        if idempotency_key in self._published:
            return self._published[idempotency_key]
        response = await self._http.request("POST", path, data={**fields, "access_token": self._token})
        body = response.json()
        post_id = str(body.get("post_id") or body.get("id") or "")
        if not post_id:
            raise ProviderError("facebook", "server", "Facebook accepted the post but returned no id")
        result = SendResult(provider_message_id=post_id)
        self._published[idempotency_key] = result
        return result

    async def fetch_comments(self, post_id: str, *, limit: int = 100) -> list[PageComment]:
        response = await self._http.request(
            "GET",
            f"/{post_id}/comments",
            params={"fields": "id,message,from,created_time", "limit": str(limit), "access_token": self._token},
        )
        return [
            PageComment(
                id=str(item["id"]),
                message=str(item.get("message", "")),
                author=(item.get("from") or {}).get("name"),
                created_time=item.get("created_time"),
            )
            for item in response.json().get("data", [])
            if item.get("id")
        ]

    async def reply_to_comment(self, comment_id: str, message: str, *, idempotency_key: str) -> SendResult:
        return await self._publish(f"/{comment_id}/comments", {"message": message}, idempotency_key)

    async def exchange_token(self, app_id: str, app_secret: str, short_lived_token: str) -> LongLivedToken:
        """Trade a short-lived user token for a long-lived one (about 60 days) so the page keeps working unattended."""
        response = await self._http.request(
            "GET",
            "/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_lived_token,
            },
        )
        body = response.json()
        token = body.get("access_token")
        if not token:
            raise ProviderError("facebook", "auth", "Facebook did not return a token")
        expires = body.get("expires_in")
        return LongLivedToken(access_token=str(token), expires_in=int(expires) if expires is not None else None)

    # -- ChannelAdapter protocol: Facebook is an outbound publishing channel in Phase 2 -------------------------

    async def send(self, tenant_id: uuid.UUID, to: str, text: str, *, idempotency_key: str) -> SendResult:
        """Publish ``text`` to the page feed (``to`` is the page id and is ignored: an adapter serves one page)."""
        return await self.publish_text(text, idempotency_key=idempotency_key)

    async def receive(self, headers: dict[str, str], body: bytes) -> InboundMessage | None:
        return None  # Facebook comments are pulled by the scheduler, not pushed to a webhook, in Phase 2

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        signature = {k.lower(): v for k, v in headers.items()}.get("x-hub-signature-256", "")
        if not signature or not self._app_secret:
            return False
        expected = "sha256=" + hmac.new(self._app_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected.encode(), signature.encode())
