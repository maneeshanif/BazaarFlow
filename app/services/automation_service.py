"""Automation recipes (PRD F-024, W-008): switch them on and off, run one now, read their history, and run them on schedule.

A shop gets one ``automations`` row per recipe, created the first time the list is opened. A recipe that has nothing to do
leaves no history (the scheduler passes every minute or so); a run that did something, or failed, is recorded. A failure is
caught, recorded with a plain reason and counted: three in a row raise ``automation.failing`` (an audit row and an error log
line) and a banner on the page. The recipe stays on and is tried again on the next pass.

``tick`` is the scheduler's entry point. It finds the shops with a recipe switched on (``system_session``, ids only) and
runs the due recipes inside each shop's own ``tenant_session``.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.problems import Conflict, DomainError, NotFound
from app.core.tenancy import Principal, system_session, tenant_session
from app.integrations.http import ProviderError
from app.models.automation import Automation, AutomationRun
from app.models.tenant import TenantIntegration
from app.models.voice import VoiceSettings
from app.schemas.automations import AutomationOut, LastRun, RunOut
from app.services import voice_service
from app.services.automation_recipes import RECIPES, Outcome, Recipe, RecipeError, deferred_sends

logger = logging.getLogger("bazaarflow.automations")
FAILURE_ALERT_AT = 3
MAX_ATTEMPTS = 3  # one try and two retries of a failure that may pass by itself
RETRY_DELAY_SECONDS = 1.0  # tests set this to 0


def _recipe(key: str) -> Recipe:
    recipe = RECIPES.get(key)
    if recipe is None:
        raise NotFound("Automation")
    return recipe


async def _connected(db: AsyncSession, tenant_id: uuid.UUID) -> set[str]:
    rows = (
        await db.execute(
            select(TenantIntegration.provider).where(TenantIntegration.tenant_id == tenant_id, TenantIntegration.status == "connected")
        )
    ).scalars()
    return set(rows)


async def ensure_rows(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Automation]:
    rows = {a.key: a for a in (await db.execute(select(Automation).where(Automation.tenant_id == tenant_id))).scalars()}
    added = False
    for key, recipe in RECIPES.items():
        if key not in rows:
            rows[key] = Automation(tenant_id=tenant_id, key=key, enabled=False, trigger=recipe.trigger, conditions_json={}, actions_json=[{"type": key}])
            db.add(rows[key])
            added = True
    if added:
        await db.flush()
    return rows


async def _last_runs(db: AsyncSession, tenant_id: uuid.UUID) -> dict[uuid.UUID, AutomationRun]:
    latest = (
        select(AutomationRun.automation_id, func.max(AutomationRun.created_at).label("at"))
        .where(AutomationRun.tenant_id == tenant_id)
        .group_by(AutomationRun.automation_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(AutomationRun).join(
                latest, (latest.c.automation_id == AutomationRun.automation_id) & (latest.c.at == AutomationRun.created_at)
            ).where(AutomationRun.tenant_id == tenant_id)
        )
    ).scalars()
    return {r.automation_id: r for r in rows}


def _out(automation: Automation, recipe: Recipe, connected: set[str], last: AutomationRun | None) -> AutomationOut:
    return AutomationOut(
        key=recipe.key,
        label=recipe.label,
        description=recipe.description,
        trigger=recipe.trigger,
        enabled=automation.enabled,
        requires=list(recipe.requires),
        requirements_met=all(r in connected for r in recipe.requires),
        last_run_at=automation.last_run_at,
        consecutive_failures=automation.consecutive_failures,
        needs_attention=automation.consecutive_failures >= FAILURE_ALERT_AT,
        last_run=LastRun(status=last.status, summary=last.summary, error=last.error, finished_at=last.finished_at) if last else None,  # type: ignore[arg-type]
    )


async def list_automations(db: AsyncSession, principal: Principal) -> list[AutomationOut]:
    rows = await ensure_rows(db, principal.tenant_id)
    connected = await _connected(db, principal.tenant_id)
    last = await _last_runs(db, principal.tenant_id)
    return [_out(rows[k], r, connected, last.get(rows[k].id)) for k, r in RECIPES.items()]


async def toggle(db: AsyncSession, principal: Principal, key: str, enabled: bool) -> AutomationOut:
    recipe = _recipe(key)
    rows = await ensure_rows(db, principal.tenant_id)
    connected = await _connected(db, principal.tenant_id)
    automation = rows[key]
    if enabled and not all(r in connected for r in recipe.requires):
        raise Conflict("Connect WhatsApp in Settings -> Integrations before switching this on.", code="integration_required")
    if enabled and not automation.enabled:
        automation.last_run_at = datetime.now(timezone.utc)  # start from now: never message about old orders
        automation.consecutive_failures = 0
    automation.enabled = enabled
    await db.flush()
    record_audit(
        db,
        "automation.enabled" if enabled else "automation.disabled",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="automation",
        entity_id=automation.id,
        after={"key": key},
    )
    last = await _last_runs(db, principal.tenant_id)
    return _out(automation, recipe, connected, last.get(automation.id))


async def _record_run(
    db: AsyncSession, tenant_id: uuid.UUID, automation: Automation, *, status: str, source: str, summary: str | None, error: str | None, started: datetime
) -> AutomationRun:
    run = AutomationRun(
        tenant_id=tenant_id,
        automation_id=automation.id,
        status=status,
        trigger_source=source,
        summary=(summary or "")[:300] or None,
        error=error,
        started_at=started,
        finished_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    return run


async def _attempt(
    db: AsyncSession, tenant_id: uuid.UUID, automation: Automation, recipe: Recipe, now: datetime
) -> tuple[Outcome | None, str | None, bool]:
    """One try of a recipe: (outcome, error, whether the error may pass by itself). A failed try leaves nothing behind."""
    try:
        async with db.begin_nested():  # a failed run leaves nothing half done
            return await recipe.run(db, tenant_id, now), None, False
    except RecipeError as exc:
        return None, str(exc), exc.transient
    except DomainError as exc:
        return None, exc.detail, False
    except ProviderError:
        return None, "The provider did not answer. It will be tried again.", True
    except Exception:  # a bug must not stop the other recipes or shops
        logger.exception("automation crashed", extra={"automation": automation.key, "tenant_id": str(tenant_id)})
        return None, "Something went wrong. It will be tried again.", False


async def execute(db: AsyncSession, tenant_id: uuid.UUID, automation: Automation, now: datetime, *, source: str) -> AutomationRun | None:
    """Run one recipe once. Returns the recorded run, or None when it had nothing to do (and nothing is recorded)."""
    recipe = RECIPES[automation.key]
    started = datetime.now(timezone.utc)
    outcome, error, transient = await _attempt(db, tenant_id, automation, recipe, now)
    attempts = 1
    while error is not None and transient and attempts < MAX_ATTEMPTS:  # only a failure that may pass by itself is retried
        await asyncio.sleep(RETRY_DELAY_SECONDS * attempts)
        outcome, error, transient = await _attempt(db, tenant_id, automation, recipe, now)
        attempts += 1
    if error is not None and transient and recipe.defers_sends:
        # the provider kept refusing: file each message as an approval so the owner can send it when WhatsApp is back
        with deferred_sends():
            outcome, fallback_error, _ = await _attempt(db, tenant_id, automation, recipe, now)
        if fallback_error is None and outcome is not None:
            error = None
            if outcome.count:
                outcome = Outcome(
                    f"WhatsApp was not available, so {outcome.count} message(s) were filed for your approval instead.", outcome.count
                )
    if error is not None:
        automation.consecutive_failures += 1
        run = await _record_run(db, tenant_id, automation, status="failed", source=source, summary=None, error=error, started=started)
        if automation.consecutive_failures == FAILURE_ALERT_AT:
            record_audit(
                db,
                "automation.failing",
                tenant_id=tenant_id,
                actor_type="system",
                entity="automation",
                entity_id=automation.id,
                after={"key": automation.key, "error": error},
            )
            logger.error("automation failing", extra={"automation": automation.key, "tenant_id": str(tenant_id), "failures": automation.consecutive_failures})
        return run
    assert outcome is not None
    automation.consecutive_failures = 0
    automation.last_run_at = now
    await db.flush()
    if outcome.count == 0 and source != "manual":
        return None
    return await _record_run(db, tenant_id, automation, status="succeeded", source=source, summary=outcome.summary, error=None, started=started)


def _run_out(run: AutomationRun, key: str) -> RunOut:
    return RunOut(
        id=run.id,
        automation_key=key,
        label=RECIPES[key].label if key in RECIPES else key,
        status=run.status,  # type: ignore[arg-type]
        trigger_source=run.trigger_source,  # type: ignore[arg-type]
        summary=run.summary,
        error=run.error,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


async def run_now(db: AsyncSession, principal: Principal, key: str) -> RunOut:
    _recipe(key)
    automation = (await ensure_rows(db, principal.tenant_id))[key]
    if not automation.enabled:
        raise Conflict("Switch this automation on before running it.", code="not_enabled")
    run = await execute(db, principal.tenant_id, automation, datetime.now(timezone.utc), source="manual")
    assert run is not None  # a manual run is always recorded
    record_audit(
        db,
        "automation.run_now",
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        entity="automation",
        entity_id=automation.id,
        after={"key": key, "status": run.status},
    )
    return _run_out(run, key)


async def list_runs(
    db: AsyncSession, principal: Principal, *, key: str | None, status: str | None, limit: int, offset: int
) -> tuple[list[RunOut], int]:
    conditions: list[Any] = [AutomationRun.tenant_id == principal.tenant_id]
    if key:
        _recipe(key)
        conditions.append(Automation.key == key)
    if status:
        conditions.append(AutomationRun.status == status)
    base = select(AutomationRun, Automation.key).join(Automation, Automation.id == AutomationRun.automation_id).where(*conditions)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(base.order_by(AutomationRun.created_at.desc(), AutomationRun.id.desc()).limit(limit).offset(offset))).all()
    return [_run_out(run, k) for run, k in rows], int(total)


async def tick(now: datetime | None = None) -> int:
    """One scheduler pass: run every due recipe of every shop that has one switched on. Returns how many runs were recorded."""
    moment = now or datetime.now(timezone.utc)
    async with system_session() as scan:
        tenants = sorted((await scan.execute(select(Automation.tenant_id).where(Automation.enabled.is_(True)).distinct())).scalars(), key=str)
    async with system_session() as scan:
        voice_shops = sorted((await scan.execute(select(VoiceSettings.tenant_id))).scalars(), key=str)
    for tenant_id in voice_shops:  # transcripts are kept only as long as each shop's retention period
        try:
            async with tenant_session(tenant_id) as db:
                await voice_service.purge_expired(db, tenant_id, moment)
        except Exception:
            logger.exception("transcript purge failed for a shop", extra={"tenant_id": str(tenant_id)})
    recorded = 0
    for tenant_id in tenants:
        try:
            async with tenant_session(tenant_id) as db:
                for automation in (await db.execute(select(Automation).where(Automation.tenant_id == tenant_id, Automation.enabled.is_(True)))).scalars().all():
                    recipe = RECIPES.get(automation.key)
                    if recipe is None or not recipe.due(moment, automation.last_run_at):
                        continue
                    if await execute(db, tenant_id, automation, moment, source="schedule") is not None:
                        recorded += 1
        except Exception:  # one shop must not stop the others
            logger.exception("automation pass failed for a shop", extra={"tenant_id": str(tenant_id)})
    return recorded
