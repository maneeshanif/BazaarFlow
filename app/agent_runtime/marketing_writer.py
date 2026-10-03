"""The marketing writer (PRD F-014, build-plan task 42): turns a short brief into a draft post.

It only writes text. It never publishes, never reaches Facebook, and the draft is saved as a draft for a person to
edit and send for approval. It obeys the same guardrails as the sales agent: the shop switch, the monthly spend cap,
a timeout, and every call is recorded (redacted) in the agent activity log.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.llm import LlmNotConfigured, describe_failure, provider_settings
from app.agent_runtime.runtime import _spend, month_spend_micros, shop_switch_on, tenant_cap_micros
from app.core.problems import DomainError
from app.core.settings import settings
from app.core.tenancy import Principal
from app.models.agent_run import AgentRun
from app.schemas.marketing_studio import DraftRequest, clean_hashtags


@dataclass(frozen=True)
class Draft:
    title: str
    message: str
    hashtags: str


GOALS = {
    "promote_product": "promote the product {product}",
    "announce_offer": "announce an offer ({notes})",
    "festival_greeting": "send a festival greeting to customers",
    "general": "post a friendly update from the shop",
}


def _prompt(shop: str, brief: DraftRequest, product: str | None) -> str:
    goal = GOALS[brief.goal].format(product=product or "", notes=brief.notes or "a special price this week")
    language = "Roman Urdu (Urdu written in English letters)" if brief.language == "roman_urdu" else "English"
    return (
        f"Write one short Facebook post for the shop '{shop}' to {goal}. Tone: {brief.tone}. Language: {language}. "
        "Do not invent prices, discounts or stock levels that were not given. No phone numbers or addresses. "
        'Reply with JSON only: {"title": "...", "message": "...", "hashtags": "#a #b"}. '
        "Title up to 8 words, message up to 60 words, 3 to 5 hashtags."
    )


def _scripted(shop: str, brief: DraftRequest, product: str | None) -> Draft:
    """A fixed, rule-based draft for tests and offline demos (refused in production like the scripted chat model)."""
    subject = product or ("our latest offer" if brief.goal == "announce_offer" else "the shop")
    if brief.language == "roman_urdu":
        message = f"{shop} mein {subject} ab available hai. Aaj hi tashreef layein!"
    else:
        message = f"{subject} is now at {shop}. Come and see it today!"
    return Draft(title=f"{subject} at {shop}"[:120], message=message, hashtags="#BazaarFlow #LocalShop")


async def write_draft(
    db: AsyncSession, principal: Principal, *, shop: str, brief: DraftRequest, product: str | None
) -> Draft:
    if not await shop_switch_on(db, principal.tenant_id):
        raise DomainError(
            "The AI assistant is paused for this shop. The owner can switch it on in Agent activity.",
            code="agents_paused",
            status_code=409,
        )
    if await month_spend_micros(db, principal.tenant_id) >= await tenant_cap_micros(db, principal.tenant_id):
        raise DomainError(
            "This month's AI allowance is used up. Drafting works again next month.",
            code="spend_limit",
            status_code=409,
        )

    started = time.monotonic()
    prompt = _prompt(shop, brief, product)
    tokens_in = tokens_out = 0
    outcome, draft, failure = "ok", None, ""
    try:
        if settings.LLM_PROVIDER.lower() == "scripted":
            if settings.APP_ENV in {"production", "staging"}:
                raise LlmNotConfigured("The scripted model is for tests and offline demos only")
            draft = _scripted(shop, brief, product)
        else:
            provider, key, base_url, model = provider_settings()
            if not key:
                raise LlmNotConfigured(f"The {provider} API key is not set")
            client = AsyncOpenAI(
                api_key=key,
                base_url=base_url,
                timeout=settings.LLM_TIMEOUT_SECONDS,
                max_retries=settings.LLM_MAX_RETRIES,
            )
            response = await client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}
            )
            usage = response.usage
            tokens_in, tokens_out = (usage.prompt_tokens, usage.completion_tokens) if usage else (0, 0)
            data = json.loads(response.choices[0].message.content or "{}")
            draft = Draft(
                title=str(data["title"]).strip()[:120],
                message=str(data["message"]).strip()[:1000],
                hashtags=clean_hashtags(str(data.get("hashtags", ""))),
            )
            if not draft.title or not draft.message:
                raise ValueError("empty draft")
    except (ValueError, KeyError):  # json.JSONDecodeError is a ValueError
        outcome, failure = "failed", "The assistant's answer could not be read. Try again."
    except Exception as exc:  # noqa: BLE001 - any provider failure becomes a plain sentence
        outcome, failure = "failed", describe_failure(exc)

    db.add(
        AgentRun(
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            agent="marketing",
            session_id=str(uuid.uuid4()),
            input_text=f"Draft a {brief.goal} post, {brief.tone}, {brief.language}",
            output_text=(draft.message if draft else failure)[:2000],
            trace_json=[],
            action_ids=[],
            outcome=outcome,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            spend_micros=_spend(tokens_in, tokens_out),
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    )
    await db.flush()
    if draft is None:
        raise DomainError(failure, code="draft_failed", status_code=502)
    return draft
