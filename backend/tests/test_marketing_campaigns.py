"""Tests for multi-post marketing campaigns and scheduler wiring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from backend.services.marketing_service import MarketingService


@pytest.mark.asyncio
async def test_generate_campaign_allows_single_post(monkeypatch):
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

    service = MarketingService(agent_runner=fake_runner)  # type: ignore[arg-type]

    campaign = await service._generate_campaign(  # type: ignore[attr-defined]
        account={"account_id": "acc1"},
        user_id="user1",
        mode="manual",
        prompt="test",
        overrides={"post_count": 1},
    )

    assert isinstance(campaign, dict)
    assert len(campaign.get("posts") or []) == 1


@pytest.mark.asyncio
async def test_publish_campaign_records_multiple_posts(monkeypatch):
    """_publish_campaign should loop through all posts and record them with a shared campaign_id."""

    created_posts = []
    recorded = []

    class DummyResponse:
        def __init__(self, post_id: str) -> None:
            self.post_id = post_id

        def model_dump(self) -> Dict[str, Any]:
            return {"id": self.post_id}

    class DummyManager:
        def create_image_post(self, request):  # type: ignore[no-untyped-def]
            created_posts.append(request.message)
            return DummyResponse(f"post_{len(created_posts)}")

        def create_text_post(self, request):  # type: ignore[no-untyped-def]
            created_posts.append(request.message)
            return DummyResponse(f"post_{len(created_posts)}")

    def fake_factory(config):  # type: ignore[no-untyped-def]
        return DummyManager()

    def fake_record_marketing_post(**kwargs):  # type: ignore[no-untyped-def]
        recorded.append(kwargs)
        return {"record_id": f"rec_{len(recorded)}", **kwargs}

    monkeypatch.setattr("backend.services.marketing_service.record_marketing_post", fake_record_marketing_post)

    service = MarketingService(facebook_manager_factory=fake_factory)  # type: ignore[arg-type]

    account = {"account_id": "acc1", "page_id": "p1", "access_token": "t"}
    campaign = {
        "strategy_summary": "Test",
        "posts": [
            {"title": "A", "message": "m1", "hashtags": [], "image_query": "q1"},
            {"title": "B", "message": "m2", "hashtags": [], "image_query": "q2"},
        ],
    }

    result = service._publish_campaign(  # type: ignore[attr-defined]
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


def test_scheduler_calls_trigger_scheduled_campaign(monkeypatch):
    """MarketingScheduler should call trigger_scheduled_campaign for due schedules.

    This is a light-weight behavioural check to ensure the wiring remains intact.
    """

    from backend.services.marketing_scheduler import MarketingScheduler

    class DummyRunner:
        def __init__(self) -> None:
            self.calls = []

        async def trigger_scheduled_campaign(self, *, account_id: str, user_id: str, triggered_at: str | None = None):
            self.calls.append((account_id, user_id, triggered_at))
            return {"ok": True}

    def fake_list_schedules():  # type: ignore[no-untyped-def]
        return [
            {
                "account_id": "acc1",
                "user_id": "user1",
                "times": [datetime.now(timezone.utc).strftime("%H:%M")],
                "timezone": "UTC",
            }
        ]

    monkeypatch.setattr("backend.services.marketing_scheduler.list_schedules", fake_list_schedules)

    runner = DummyRunner()
    scheduler = MarketingScheduler(campaign_runner=runner)

    # Run a single tick synchronously
    import asyncio

    asyncio.run(scheduler._tick())  # type: ignore[attr-defined]

    assert len(runner.calls) == 1
