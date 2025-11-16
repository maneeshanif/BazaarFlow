from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.services.marketing_scheduler import MarketingScheduler, ScheduleRecord


class StubRunner:
    def __init__(self):
        self.calls: list[tuple[str, str, str | None]] = []

    async def trigger_scheduled_campaign(self, *, account_id: str, user_id: str, triggered_at: str | None = None):  # type: ignore[override]
        self.calls.append((account_id, user_id, triggered_at))


@pytest.mark.asyncio
async def test_scheduler_triggers_matching_slot():
    runner = StubRunner()
    scheduler = MarketingScheduler(campaign_runner=runner)
    record = ScheduleRecord(
        account_id="acct-1",
        user_id="user-1",
        times=["09:00"],
        timezone="UTC",
        last_triggered_at=None,
    )

    now = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    await scheduler._maybe_trigger(record, now)  # type: ignore[attr-defined]

    assert len(runner.calls) == 1
    account_id, user_id, triggered_at = runner.calls[0]
    assert account_id == "acct-1"
    assert user_id == "user-1"
    assert triggered_at is not None


@pytest.mark.asyncio
async def test_scheduler_skips_when_recently_triggered():
    runner = StubRunner()
    scheduler = MarketingScheduler(campaign_runner=runner)
    now = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)

    recent_record = ScheduleRecord(
        account_id="acct-2",
        user_id="user-2",
        times=["09:00"],
        timezone="UTC",
        last_triggered_at=(now - timedelta(seconds=45)).isoformat(),
    )

    await scheduler._maybe_trigger(recent_record, now)  # type: ignore[attr-defined]
    assert runner.calls == []

    stale_record = ScheduleRecord(
        account_id="acct-2",
        user_id="user-2",
        times=["09:00"],
        timezone="UTC",
        last_triggered_at=(now - timedelta(hours=3)).isoformat(),
    )

    await scheduler._maybe_trigger(stale_record, now)  # type: ignore[attr-defined]
    assert len(runner.calls) == 1
