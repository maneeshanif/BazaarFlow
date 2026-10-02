"""Tests for multi-post marketing campaigns and scheduler wiring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from app.services.marketing_service import MarketingService


@pytest.mark.asyncio
async def test_generate_campaign_allows_single_post(monkeypatch: Any) -> None:
    """_generate_campaign should accept a single-post campaign when requested."""

    async def fake_runner(payload: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure the post_count hint is propagated to the agent layer
        assert payload.get("post_count") == 1
        return {
            "strategy_summary": "Test campaign",
            "posts": [
                {"title": "One", "message": "m1", "hashtags": [], "image_query": "q1"},
            ],
        }

    service = MarketingService(agent_runner=fake_runner)

    campaign = await service._generate_campaign(
        account={"account_id": "acc1"},
        user_id="user1",
        mode="manual",
        prompt="test",
        overrides={"post_count": 1},
    )

    assert isinstance(campaign, dict)
    assert len(campaign.get("posts") or []) == 1


@pytest.mark.asyncio
async def test_publish_campaign_records_multiple_posts(monkeypatch: Any) -> None:
    """_publish_campaign should loop through all posts and record them with a shared campaign_id."""

    created_posts = []
    recorded = []

    class DummyResponse:
        def __init__(self, post_id: str) -> None:
            self.post_id = post_id

        def model_dump(self) -> Dict[str, Any]:
            return {"id": self.post_id}

    class DummyManager:
        def create_image_post(self, request: Any) -> Any:
            created_posts.append(request.message)
            return DummyResponse(f"post_{len(created_posts)}")

        def create_text_post(self, request: Any) -> Any:
            created_posts.append(request.message)
            return DummyResponse(f"post_{len(created_posts)}")

    def fake_factory(config: Any) -> Any:
        return DummyManager()

    def fake_record_marketing_post(**kwargs: Any) -> Any:
        recorded.append(kwargs)
        return {"record_id": f"rec_{len(recorded)}", **kwargs}

    monkeypatch.setattr("app.services.marketing_service.record_marketing_post", fake_record_marketing_post)

    service = MarketingService(facebook_manager_factory=fake_factory)

    # FacebookConfig validates the shape of the credentials, so the fake ones must look real
    account = {"account_id": "acc1", "page_id": "123456789012345", "access_token": "EAA" + "x" * 40}
    campaign = {
        "strategy_summary": "Test",
        "posts": [
            {"title": "A", "message": "m1", "hashtags": [], "image_query": "q1"},
            {"title": "B", "message": "m2", "hashtags": [], "image_query": "q2"},
        ],
    }

    result = service._publish_campaign(
        account=account,
        user_id="user1",
        campaign=campaign,
        source="manual",
        prompt="test",
        overrides={},
    )

    assert isinstance(result, dict)
    assert len(result["posts"]) == 2
    campaign_ids = {p["post"]["extra"]["campaign_id"] for p in result["posts"]}
    assert len(campaign_ids) == 1  # shared id


def test_scheduler_calls_trigger_scheduled_campaign(monkeypatch: Any) -> None:
    """MarketingScheduler should call trigger_scheduled_campaign for due schedules.

    This is a light-weight behavioural check to ensure the wiring remains intact.
    """

    from app.services.marketing_scheduler import MarketingScheduler

    class DummyRunner:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str | None]] = []

        async def trigger_scheduled_campaign(self, *, account_id: str, user_id: str, triggered_at: str | None = None) -> Any:
            self.calls.append((account_id, user_id, triggered_at))
            return {"ok": True}

    def fake_list_schedules() -> Any:
        return [
            {
                "account_id": "acc1",
                "user_id": "user1",
                "times": [datetime.now(timezone.utc).strftime("%H:%M")],
                "timezone": "UTC",
            }
        ]

    monkeypatch.setattr("app.services.marketing_scheduler.list_schedules", fake_list_schedules)

    runner = DummyRunner()
    # The slot is built from the current HH:MM (seconds truncated), so the matching window must
    # cover a full minute plus a rollover or the test passes only in the first 45 s of each minute.
    scheduler = MarketingScheduler(campaign_runner=runner, matching_window_seconds=90)

    # Run a single tick synchronously
    import asyncio

    asyncio.run(scheduler._tick())

    assert len(runner.calls) == 1
