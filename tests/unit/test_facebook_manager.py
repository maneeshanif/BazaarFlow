"""Unit tests for the Facebook Manager toolkit.

The tests operate entirely against mocked HTTP calls so that no real
Facebook Graph API traffic is generated. Each scenario validates the
payload the manager attempts to send and the objects returned to
callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import sys


TEST_ROOT = Path(__file__).resolve().parents[1]
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

import pytest

from config.fb_config import FacebookConfig
from src.exceptions import FacebookAPIError, ImageUploadError, PostCreationError
from facebook_manager import FacebookManager
from models.fb_model import (
    CommentReplyRequest,
    CommentReactionRequest,
    ImagePostRequest,
    InsightPeriod,
    ReactionType,
    TextPostRequest,
)


@pytest.fixture()
def fake_config() -> FacebookConfig:
    """Provide a minimal, validated configuration for tests."""

    return FacebookConfig(
        facebook_page_id="123456789012345",
        facebook_access_token="EAA" + ("x" * 60),
        facebook_api_version="v20.0",
    )


@pytest.fixture()
def manager(fake_config: FacebookConfig) -> FacebookManager:
    """Instantiate the manager with the fake configuration and close afterwards."""

    mgr = FacebookManager(config=fake_config)
    yield mgr
    mgr.close()


def test_create_text_post_success(manager: FacebookManager, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, Any] = {}

    def fake_request(self: FacebookManager, method: str, endpoint: str, **kwargs: Any) -> Dict[str, str]:
        captured.update({"method": method, "endpoint": endpoint, "data": kwargs.get("data")})
        return {"id": "123456789012345_67890"}

    monkeypatch.setattr(FacebookManager, "_make_request", fake_request, raising=False)

    response = manager.create_text_post(TextPostRequest(message="Launch day update"))

    assert response.post_id == "123456789012345_67890"
    assert captured["method"] == "POST"
    assert captured["endpoint"].endswith("/feed")
    assert captured["data"] == {"message": "Launch day update"}


def test_create_text_post_missing_post_id(manager: FacebookManager, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(self: FacebookManager, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {"success": True}

    monkeypatch.setattr(FacebookManager, "_make_request", fake_request, raising=False)

    with pytest.raises(PostCreationError):
        manager.create_text_post(TextPostRequest(message="No ID returned"))


def test_create_image_post_from_url(manager: FacebookManager, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, Any] = {}

    def fake_request(self: FacebookManager, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        captured.update({"method": method, "endpoint": endpoint, "data": kwargs.get("data")})
        return {"post_id": "123456789012345_98765"}

    monkeypatch.setattr(FacebookManager, "_make_request", fake_request, raising=False)

    response = manager.create_image_post(
        ImagePostRequest(image_url="https://example.com/image.jpg", message="Check our new product")
    )

    assert response.post_id == "123456789012345_98765"
    assert captured["endpoint"].endswith("/photos")
    assert captured["data"] == {
        "url": "https://example.com/image.jpg",
        "published": "true",
        "message": "Check our new product",
    }


def test_create_image_post_from_file(manager: FacebookManager, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    image_path = tmp_path / "preview.jpg"
    image_path.write_bytes(b"fake image bytes")
    captured: Dict[str, Any] = {}

    def fake_request(self: FacebookManager, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        captured.update({
            "method": method,
            "endpoint": endpoint,
            "data": kwargs.get("data"),
            "files": kwargs.get("files"),
        })
        return {"post_id": "123456789012345_54321"}

    monkeypatch.setattr(FacebookManager, "_make_request", fake_request, raising=False)

    response = manager.create_image_post(
        ImagePostRequest(image_path=str(image_path), message="Local launch photo")
    )

    assert response.post_id == "123456789012345_54321"
    assert captured["endpoint"].endswith("/photos")
    assert captured["data"]["message"] == "Local launch photo"
    assert "source" in captured["files"]
    file_name, file_object, mime_type = captured["files"]["source"]
    assert file_name == "preview.jpg"
    assert mime_type == "image/jpeg"


def test_create_image_post_with_missing_file(manager: FacebookManager) -> None:
    with pytest.raises(ImageUploadError):
        manager.create_image_post(ImagePostRequest(image_path="/does/not/exist.jpg"))


def test_verify_credentials_success(manager: FacebookManager, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(self: FacebookManager, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        assert endpoint == manager.config.facebook_page_id
        return {"id": manager.config.facebook_page_id, "name": "Test Page"}

    monkeypatch.setattr(FacebookManager, "_make_request", fake_request, raising=False)

    assert manager.verify_credentials() is True


def test_get_post_comments_with_keywords(manager: FacebookManager, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(self: FacebookManager, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        if endpoint == "98765":
            return {"post_id": "123456789012345_98765"}

        assert endpoint == "123456789012345_98765/comments"
        return {
            "data": [
                {
                    "id": "c1",
                    "message": "Love the product quality!",
                    "from": {"id": "u1", "name": "Fan"},
                    "created_time": "2024-01-01T00:00:00+0000",
                    "like_count": 3,
                    "comment_count": 1,
                },
                {
                    "id": "c2",
                    "message": "Need more colors please",
                    "from": {"id": "u2", "name": "Customer"},
                    "created_time": "2024-01-02T00:00:00+0000",
                    "like_count": 0,
                    "comment_count": 0,
                },
            ],
            "paging": {"cursors": {"after": "abc123"}},
        }

    monkeypatch.setattr(FacebookManager, "_make_request", fake_request, raising=False)

    response = manager.get_post_comments(post_id="98765", limit=10)

    assert response.total_count == 2
    assert response.has_next_page is False
    assert response.next_cursor == "abc123"
    keywords = {item["keyword"] for item in response.keywords or []}
    assert {"product", "quality", "colors"}.issubset(keywords)


def test_comment_actions(manager: FacebookManager, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[Dict[str, Any]] = []

    def fake_request(self: FacebookManager, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        calls.append({"method": method, "endpoint": endpoint, "data": kwargs.get("data")})
        if endpoint.endswith("/comments"):
            return {"id": "reply123"}
        return {"success": True}

    monkeypatch.setattr(FacebookManager, "_make_request", fake_request, raising=False)

    reply_request = CommentReplyRequest(comment_id="c1", message="Thanks for the feedback!")
    reaction_request = CommentReactionRequest(comment_id="c1", reaction_type=ReactionType.LOVE)

    reply_result = manager.reply_to_comment(reply_request)
    reaction_result = manager.react_to_comment(reaction_request)
    hide_result = manager.hide_comment("c1")
    delete_result = manager.delete_comment("c1")

    assert reply_result.success is True
    assert reaction_result.success is True
    assert hide_result.success is True
    assert delete_result.success is True

    endpoints = [call["endpoint"] for call in calls]
    assert endpoints == ["c1/comments", "c1/likes", "c1", "c1"]


def test_get_post_insights_lifetime(manager: FacebookManager, monkeypatch: pytest.MonkeyPatch) -> None:
    post_id = "123456789012345_55555"

    def fake_request(self: FacebookManager, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        if endpoint.endswith("/insights"):
            return {
                "data": [
                    {"name": "post_impressions", "values": [{"value": 200}]},
                    {"name": "post_impressions_unique", "values": [{"value": 150}]},
                    {"name": "post_clicks", "values": [{"value": 25}]},
                    {
                        "name": "post_reactions_by_type_total",
                        "values": [{"value": {"like": 10, "love": 5, "wow": 2}}],
                    },
                ]
            }
        if endpoint == post_id:
            return {
                "comments": {"summary": {"total_count": 4}},
                "shares": {"count": 3},
            }
        raise AssertionError(f"Unexpected endpoint {endpoint}")

    monkeypatch.setattr(FacebookManager, "_make_request", fake_request, raising=False)

    insights = manager.get_post_insights(post_id=post_id, period=InsightPeriod.LAST_7_DAYS)

    assert insights.period is InsightPeriod.LIFETIME
    assert insights.reach == 150
    assert insights.impressions == 200
    assert insights.reactions.like == 10
    assert insights.reactions.total == 17
    assert insights.comments_count == 4
    assert insights.shares_count == 3
    assert insights.clicked == 25
    assert insights.engagement_rate == pytest.approx(32.67, rel=1e-4)


def test_extract_keywords_helper(manager: FacebookManager) -> None:
    comments = [
        "The delivery was fast and the quality amazing",
        "Quality control could improve but delivery remains fast",
        "Fast shipping wins every time",
    ]

    keywords = manager._extract_keywords(comments, min_length=4, top_n=3)
    words = [item["keyword"] for item in keywords]

    assert words[0] == "fast"
    assert "quality" in words
    assert len(keywords) <= 3


def test_get_post_insights_handles_missing_shares(
    manager: FacebookManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    post_id = "123456789012345_99999"

    def fake_request(self: FacebookManager, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        if endpoint.endswith("/insights"):
            return {
                "data": [
                    {"name": "post_impressions", "values": [{"value": 100}]},
                    {"name": "post_impressions_unique", "values": [{"value": 80}]},
                    {"name": "post_clicks", "values": [{"value": 5}]},
                    {"name": "post_reactions_by_type_total", "values": [{"value": {"like": 3}}]},
                ]
            }
        if endpoint == post_id:
            raise FacebookAPIError("shares not available", 100)
        raise AssertionError(f"Unexpected endpoint {endpoint}")

    monkeypatch.setattr(FacebookManager, "_make_request", fake_request, raising=False)

    insights = manager.get_post_insights(post_id=post_id)

    assert insights.post_id == post_id
    assert insights.shares_count == 0
    assert insights.comments_count == 0
    assert insights.reactions.total == 3
