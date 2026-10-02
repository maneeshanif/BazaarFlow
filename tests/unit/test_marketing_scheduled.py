"""Tests for scheduled marketing campaigns and per-post execution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from app.repositories import marketing_scheduled_repository as scheduled_repo
from app.services.marketing_scheduler import MarketingScheduler
from app.services.marketing_service import MarketingService


def _make_iso(dt: datetime) -> str:
  return dt.replace(microsecond=0).isoformat()


class _MemoryStore:
  """In-memory stand-in for the JSON store (same read / write / update interface)."""

  def __init__(self) -> None:
    self._doc: List[Dict[str, Any]] = []

  def read(self) -> List[Dict[str, Any]]:
    return list(self._doc)

  def write(self, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    self._doc = list(value)
    return self._doc

  def update(self, mutator):  # type: ignore[no-untyped-def]
    doc, result = mutator(list(self._doc))
    self._doc = list(doc)
    return result


@pytest.fixture
def stores(monkeypatch):  # type: ignore[no-untyped-def]
  campaigns, posts = _MemoryStore(), _MemoryStore()
  monkeypatch.setattr(scheduled_repo, "_campaign_store", campaigns)
  monkeypatch.setattr(scheduled_repo, "_post_store", posts)
  return campaigns, posts


def test_repository_create_and_list_pending(stores):  # type: ignore[no-untyped-def]
  """The repository persists a campaign with its posts and returns only the pending posts that are due."""
  now = datetime.now(timezone.utc)
  past = _make_iso(now - timedelta(minutes=5))
  future = _make_iso(now + timedelta(minutes=5))

  result = scheduled_repo.create_scheduled_campaign(
    account_id="acc1",
    user_id="user1",
    prompt="test",
    strategy_summary="summary",
    overrides={"foo": "bar"},
    posts_with_times=[
      {"post_payload": {"message": "m1"}, "scheduled_at": past},
      {"post_payload": {"message": "m2"}, "scheduled_at": future},
    ],
  )

  assert result["campaign"]["account_id"] == "acc1"
  assert len(result["posts"]) == 2
  assert {p["status"] for p in result["posts"]} == {"pending"}
  assert [p["campaign_post_index"] for p in result["posts"]] == [0, 1]

  due = scheduled_repo.list_pending_scheduled_posts(now_iso=_make_iso(now))
  assert len(due) == 1
  assert due[0]["post_payload"]["message"] == "m1"


def test_mark_post_posted_and_failed(stores):  # type: ignore[no-untyped-def]
  """Status updates flip a scheduled post from pending to posted or failed; unknown ids change nothing."""
  now = _make_iso(datetime.now(timezone.utc))
  result = scheduled_repo.create_scheduled_campaign(
    account_id="acc1",
    user_id="user1",
    prompt="test",
    strategy_summary=None,
    overrides={},
    posts_with_times=[
      {"post_payload": {"message": "m1"}, "scheduled_at": now},
      {"post_payload": {"message": "m2"}, "scheduled_at": now},
    ],
  )
  first, second = (p["scheduled_post_id"] for p in result["posts"])

  posted = scheduled_repo.mark_scheduled_post_posted(scheduled_post_id=first, facebook_post_id="fb_1")
  assert posted is not None
  assert posted["status"] == "posted"
  assert posted["facebook_post_id"] == "fb_1"

  failed = scheduled_repo.mark_scheduled_post_failed(scheduled_post_id=second, error="boom")
  assert failed is not None
  assert failed["status"] == "failed"
  assert failed["error"] == "boom"

  assert scheduled_repo.mark_scheduled_post_failed(scheduled_post_id="missing", error="boom") is None
  # posted and failed posts are no longer pending
  assert scheduled_repo.list_pending_scheduled_posts(now_iso=_make_iso(datetime.now(timezone.utc) + timedelta(hours=1))) == []


@pytest.mark.asyncio
async def test_create_scheduled_campaign_validates_future_times(monkeypatch, stores):  # type: ignore[no-untyped-def]
  """MarketingService.create_scheduled_campaign rejects past times and an empty list, and stores nothing."""
  service = MarketingService()
  monkeypatch.setattr(service, "_require_account", lambda account_id: {"account_id": account_id})
  monkeypatch.setattr(service, "_resolve_user_id", lambda user_id: user_id or "user1")

  past = _make_iso(datetime.now(timezone.utc) - timedelta(minutes=1))
  with pytest.raises(ValueError, match="future"):
    await service.create_scheduled_campaign(
      account_id="acc1",
      user_id="user1",
      prompt="test",
      overrides={},
      posts_with_times=[{"post_payload": {"message": "m1"}, "scheduled_at": past}],
    )
  with pytest.raises(ValueError, match="at least one post"):
    await service.create_scheduled_campaign(
      account_id="acc1", user_id="user1", prompt="test", overrides={}, posts_with_times=[]
    )
  assert scheduled_repo.list_pending_scheduled_posts(now_iso=_make_iso(datetime.now(timezone.utc) + timedelta(days=365))) == []

  future = _make_iso(datetime.now(timezone.utc) + timedelta(hours=2))
  created = await service.create_scheduled_campaign(
    account_id="acc1",
    user_id="user1",
    prompt="test",
    overrides={},
    posts_with_times=[{"post_payload": {"message": "m1"}, "scheduled_at": future}],
  )
  assert created, "a future post is accepted"


@pytest.mark.asyncio
async def test_scheduler_publishes_pending_posts(monkeypatch):
  """MarketingScheduler._tick should invoke publish_scheduled_post for due posts."""

  calls: List[str] = []

  class DummyRunner:
    async def trigger_scheduled_campaign(self, *, account_id: str, user_id: str, triggered_at: str | None = None):
      return {"ok": True}

    def publish_scheduled_post(self, *, scheduled_post_id: str):  # type: ignore[no-untyped-def]
      calls.append(scheduled_post_id)

  def fake_list_schedules():  # type: ignore[no-untyped-def]
    return []

  now = datetime.now(timezone.utc)
  pending = [
    {
      "scheduled_post_id": "sp1",
      "scheduled_campaign_id": "cmp1",
      "scheduled_at": _make_iso(now - timedelta(minutes=1)),
      "status": "pending",
      "post_payload": {"message": "m1"},
    }
  ]

  monkeypatch.setattr("app.services.marketing_scheduler.list_schedules", fake_list_schedules)
  monkeypatch.setattr(scheduled_repo, "list_pending_scheduled_posts", lambda now_iso: pending, raising=False)

  scheduler = MarketingScheduler(campaign_runner=DummyRunner())

  await scheduler._tick()  # type: ignore[attr-defined]

  assert calls == ["sp1"]
