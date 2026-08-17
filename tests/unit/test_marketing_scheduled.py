"""Tests for scheduled marketing campaigns and per-post execution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from backend.lib import marketing_scheduled_repository as scheduled_repo
from backend.services.marketing_scheduler import MarketingScheduler
from backend.services.marketing_service import MarketingService


def _make_iso(dt: datetime) -> str:
  return dt.replace(microsecond=0).isoformat()


def test_repository_create_and_list_pending(monkeypatch, tmp_path):
  """Repository should persist campaigns and return only due pending posts."""

  campaigns_path = tmp_path / "campaigns.json"
  posts_path = tmp_path / "posts.json"

  class DummyStore:
    def __init__(self, path):
      self._path = path
      self._doc: List[Dict[str, Any]] = []

    def read(self):
      return list(self._doc)

    def write(self, value):
      self._doc = list(value)
      return self._doc

    def update(self, mutator):  # type: ignore[no-untyped-def]
      doc, result = mutator(list(self._doc))
      self._doc = list(doc)
      return result

  campaigns_store = DummyStore(campaigns_path)
  posts_store = DummyStore(posts_path)

  monkeypatch.setattr(scheduled_repo, "_CAMPAIGNS_STORE", campaigns_store, raising=False)
  monkeypatch.setattr(scheduled_repo, "_POSTS_STORE", posts_store, raising=False)

  now = datetime.now(timezone.utc)
  past = _make_iso(now - timedelta(minutes=5))
  future = _make_iso(now + timedelta(minutes=5))

  campaign, posts = scheduled_repo.create_scheduled_campaign(
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

  assert campaign["account_id"] == "acc1"
  assert len(posts) == 2

  due = scheduled_repo.list_pending_scheduled_posts(now_iso=_make_iso(now))
  assert len(due) == 1
  assert due[0]["post_payload"]["message"] == "m1"


def test_mark_post_posted_and_failed(monkeypatch, tmp_path):
  """Status updates should flip scheduled posts from pending to posted/failed."""

  posts_path = tmp_path / "posts.json"

  class DummyStore:
    def __init__(self, path):
      self._path = path
      self._doc: List[Dict[str, Any]] = []

    def read(self):
      return list(self._doc)

    def write(self, value):
      self._doc = list(value)
      return self._doc

    def update(self, mutator):  # type: ignore[no-untyped-def]
      doc, result = mutator(list(self._doc))
      self._doc = list(doc)
      return result

  posts_store = DummyStore(posts_path)
  monkeypatch.setattr(scheduled_repo, "_POSTS_STORE", posts_store, raising=False)

  now = _make_iso(datetime.now(timezone.utc))
  _, posts = scheduled_repo.create_scheduled_campaign(
    account_id="acc1",
    user_id="user1",
    prompt="test",
    strategy_summary=None,
    overrides={},
    posts_with_times=[{"post_payload": {"message": "m1"}, "scheduled_at": now}],
  )

  post_id = posts[0]["scheduled_post_id"]

  updated = scheduled_repo.mark_scheduled_post_posted(post_id, facebook_post_id="fb_1")
  assert updated is not None
  assert updated["status"] == "posted"
  assert updated.get("facebook_post_id") == "fb_1"

  # Marking a non-existing id should be a no-op
  failed = scheduled_repo.mark_scheduled_post_failed("missing", error="boom")
  assert failed is None


@pytest.mark.asyncio
async def test_create_scheduled_campaign_validates_future_times(monkeypatch):
  """MarketingService.create_scheduled_campaign should reject past times."""

  service = MarketingService()  # type: ignore[call-arg]

  past = _make_iso(datetime.now(timezone.utc) - timedelta(minutes=1))

  with pytest.raises(ValueError):
    await service.create_scheduled_campaign(  # type: ignore[attr-defined]
      account_id="acc1",
      user_id="user1",
      prompt="test",
      raw_campaign=None,
      overrides={},
      posts_with_times=[{"post_payload": {"message": "m1"}, "scheduled_at": past}],
    )


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

  monkeypatch.setattr("backend.services.marketing_scheduler.list_schedules", fake_list_schedules)
  monkeypatch.setattr(scheduled_repo, "list_pending_scheduled_posts", lambda now_iso: pending, raising=False)

  scheduler = MarketingScheduler(campaign_runner=DummyRunner())

  await scheduler._tick()  # type: ignore[attr-defined]

  assert calls == ["sp1"]
