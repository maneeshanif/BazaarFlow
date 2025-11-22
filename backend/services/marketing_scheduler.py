"""Background worker that fires marketing campaigns at scheduled times."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple, Protocol
from zoneinfo import ZoneInfo

from ..lib import list_schedules
from ..lib import marketing_scheduled_repository as scheduled_repo
from .marketing_service import marketing_service

logger = logging.getLogger(__name__)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid integer for %s=%s; falling back to %s", name, raw, default)
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float for %s=%s; falling back to %s", name, raw, default)
        return default


class ScheduledCampaignRunner(Protocol):
    async def trigger_scheduled_campaign(
        self,
        *,
        account_id: str,
        user_id: str,
        triggered_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class ScheduleRecord:
    account_id: str
    user_id: str
    times: Sequence[str]
    timezone: str
    last_triggered_at: Optional[str]


class MarketingScheduler:
    """Simple cooperative scheduler that polls stored marketing slots."""

    def __init__(
        self,
        *,
        poll_interval: float = 30.0,
        trigger_window_seconds: int = 90,
        matching_window_seconds: int = 45,
        max_concurrent_runs: int = 3,
        campaign_runner: Optional[ScheduledCampaignRunner] = None,
    ) -> None:
        self._poll_interval = max(poll_interval, 5.0)
        self._trigger_window = timedelta(seconds=max(trigger_window_seconds, 30))
        self._matching_window = timedelta(seconds=max(matching_window_seconds, 10))
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._campaign_runner = campaign_runner or marketing_service
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent_runs))
        self._active_accounts: set[str] = set()

    async def start(self) -> None:
        if self._task and not self._task.done():
            logger.debug("Marketing scheduler already running")
            return
        logger.info("Starting marketing scheduler (poll %.1fs)", self._poll_interval)
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="marketing_scheduler")

    async def stop(self) -> None:
        if not self._task:
            return
        logger.info("Stopping marketing scheduler")
        if self._stop_event:
            self._stop_event.set()
        try:
            await self._task
        except asyncio.CancelledError:  # pragma: no cover - shutdown path
            logger.debug("Marketing scheduler task cancelled")
        finally:
            self._task = None
            self._stop_event = None

    async def _run(self) -> None:
        assert self._stop_event is not None
        while True:
            if self._stop_event.is_set():
                return
            try:
                await self._tick()
            except Exception:  # pragma: no cover - defensive guard
                logger.exception("Marketing scheduler tick failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_interval)
            except asyncio.TimeoutError:
                continue

    async def _tick(self) -> None:
        now_utc = datetime.now(timezone.utc)
        records = self._load_schedules()
        if records:
            tasks = [self._maybe_trigger(record, now_utc) for record in records]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for record, result in zip(records, results):
                if isinstance(result, Exception):
                    logger.exception(
                        "Failed to evaluate schedule for account %s",
                        record.account_id,
                        exc_info=result,
                    )

        # Additionally, look for any pending scheduled posts that are due
        # and dispatch them via the campaign runner if it supports the
        # publish_scheduled_post interface.
        pending_posts = scheduled_repo.list_pending_scheduled_posts(now_iso=now_utc.isoformat())
        if not pending_posts:
            return

        if not hasattr(self._campaign_runner, "publish_scheduled_post"):
            logger.debug("Campaign runner does not support publish_scheduled_post; skipping scheduled posts dispatch")
            return

        for record in pending_posts:
            scheduled_post_id = record.get("scheduled_post_id")
            if not isinstance(scheduled_post_id, str):
                continue
            async with self._semaphore:
                try:
                    logger.info("Publishing scheduled marketing post %s", scheduled_post_id)
                    # type: ignore[call-arg]
                    await asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda spid=scheduled_post_id: self._campaign_runner.publish_scheduled_post(scheduled_post_id=spid),
                    )
                except Exception:  # pragma: no cover - defensive guard
                    logger.exception("Failed to publish scheduled post %s", scheduled_post_id)

    def _load_schedules(self) -> List[ScheduleRecord]:
        payload: List[ScheduleRecord] = []
        for entry in list_schedules():
            account_id = entry.get("account_id")
            user_id = entry.get("user_id")
            times = entry.get("times") or []
            timezone_name = entry.get("timezone") or "UTC"
            if not account_id or not user_id or not times:
                continue
            payload.append(
                ScheduleRecord(
                    account_id=account_id,
                    user_id=user_id,
                    times=list(times),
                    timezone=timezone_name,
                    last_triggered_at=entry.get("last_triggered_at"),
                )
            )
        return payload

    async def _maybe_trigger(self, schedule: ScheduleRecord, now_utc: datetime) -> None:
        slot = self._locate_due_slot(schedule, now_utc)
        if not slot:
            return

        last_triggered_dt = self._parse_iso(schedule.last_triggered_at)
        if last_triggered_dt and now_utc - last_triggered_dt < self._trigger_window:
            logger.debug(
                "Skipping account %s; last triggered %ss ago",
                schedule.account_id,
                int((now_utc - last_triggered_dt).total_seconds()),
            )
            return

        if schedule.account_id in self._active_accounts:
            logger.debug("Account %s already has a pending run", schedule.account_id)
            return

        async with self._semaphore:
            self._active_accounts.add(schedule.account_id)
            try:
                logger.info(
                    "Triggering scheduled marketing run for account=%s slot=%s (%s)",
                    schedule.account_id,
                    slot,
                    schedule.timezone,
                )
                await self._campaign_runner.trigger_scheduled_campaign(
                    account_id=schedule.account_id,
                    user_id=schedule.user_id,
                    triggered_at=now_utc.isoformat(),
                )
            finally:
                self._active_accounts.discard(schedule.account_id)

    def _locate_due_slot(self, schedule: ScheduleRecord, now_utc: datetime) -> Optional[str]:
        tz = self._safe_zone(schedule.timezone)
        now_local = now_utc.astimezone(tz)
        for slot in schedule.times:
            parsed = self._parse_slot(slot)
            if not parsed:
                continue
            slot_hour, slot_minute = parsed
            slot_local = now_local.replace(hour=slot_hour, minute=slot_minute, second=0, microsecond=0)
            delta = abs(now_local - slot_local)
            if delta <= self._matching_window:
                return slot
        return None

    @staticmethod
    def _parse_slot(slot: str) -> Optional[Tuple[int, int]]:
        try:
            hour_str, minute_str = slot.split(":", 1)
            hour = int(hour_str)
            minute = int(minute_str)
        except (ValueError, AttributeError):
            return None
        if not (0 <= hour < 24 and 0 <= minute < 60):
            return None
        return hour, minute

    @staticmethod
    def _parse_iso(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            logger.debug("Unable to parse ISO timestamp: %s", value)
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _safe_zone(timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except Exception:
            logger.warning("Unknown timezone '%s', defaulting to UTC", timezone_name)
            return ZoneInfo("UTC")
marketing_scheduler = MarketingScheduler(
    poll_interval=_float_env("MARKETING_SCHEDULER_POLL_SECONDS", 30.0),
    trigger_window_seconds=_int_env("MARKETING_SCHEDULER_TRIGGER_WINDOW_SECONDS", 90),
    matching_window_seconds=_int_env("MARKETING_SCHEDULER_MATCH_WINDOW_SECONDS", 45),
    max_concurrent_runs=_int_env("MARKETING_SCHEDULER_MAX_CONCURRENT", 3),
)
