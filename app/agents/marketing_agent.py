from app.core.settings import settings
"""Marketing automation agent orchestrated through the Agents SDK."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List

from agents import Agent, Runner, SQLiteSession, set_tracing_disabled
from pydantic import BaseModel, Field

from app.agents.model import model
from app.agents.tools.marketing_tool import (
    marketing_image_search,
    marketing_inventory_snapshot,
    marketing_sales_insights,
)

logger = logging.getLogger(__name__)

set_tracing_disabled(True)


OUTPUT_SCHEMA = {
    "strategy_summary": "High-level narrative of the campaign and what it is trying to achieve.",
    "posts": "Array of 1-6 posts. Each post must include: title, message, hashtags, image_query and optional product_sku, call_to_action, day_offset.",
}

OUTPUT_SCHEMA_JSON = json.dumps(OUTPUT_SCHEMA)

class CampaignPost(BaseModel):
    """One post in a multi-step marketing campaign."""

    title: str = Field(..., max_length=120, description="Short, catchy title for this post.")
    message: str = Field(..., max_length=400, description="Primary caption text. Keep it under 400 characters.")
    hashtags: List[str] = Field(
        default_factory=list,
        max_items=6,
        description="List of 3-6 concise hashtags (without duplicates, without '#').",
    )
    image_query: str = Field(
        ...,
        description=(
            "Natural language description of the desired image. This will be sent "
            "to Pexels search, so avoid hashtags or emojis."
        ),
    )
    image_url: str | None = Field(
        default=None,
        description="Optional direct image URL if the model is confident about one.",
    )
    product_sku: str | None = Field(default=None, description="Optional SKU to reference in analytics.")
    call_to_action: str | None = Field(
        default=None,
        description="One-line CTA to reinforce the conversion goal for this post.",
    )
    day_offset: int | None = Field(
        default=None,
        description=(
            "Optional relative day offset from campaign start (0=today). "
            "Can be used later for staggered scheduling."
        ),
        ge=0,
        le=30,
    )


class CampaignResponse(BaseModel):
    """Campaign response from the marketing agent.

    Supports both single-post and multi-post campaigns.
    """

    strategy_summary: str = Field(
        ...,
        description="High-level explanation of how the posts work together as a campaign.",
    )
    posts: List[CampaignPost] = Field(
        ...,
        min_items=1,
        max_items=6,
        description="The ordered sequence of posts that form this campaign.",
    )

INSTRUCTIONS = f"""
You are MarketingAgent, crafting social-ready Facebook campaigns for BazaarFlow.

Your responsibilities:
- Analyse inventory health, sales momentum, and imagery options using the available tools.
- Design a campaign that can contain either a single highly-optimised post or a short multi-post sequence (up to 6 posts) that can run over several days.
- For each post, craft a concise caption that blends urgency, social proof, and a clear CTA.
- Always call BOTH marketing_inventory_snapshot and marketing_sales_insights before finalising the campaign. Use marketing_image_search if you need photography inspiration.
- Optimise for engagement: highlight trending items, new arrivals, or restocked favourites.
- Embrace BazaarFlow's friendly voice with tasteful emoji use (2-4 max).

Output requirements:
- Return ONLY valid JSON matching this schema: {OUTPUT_SCHEMA_JSON}
- strategy_summary: one or two paragraphs explaining the overall campaign arc.
- posts: an array of 1-6 objects, each matching the CampaignPost schema.
- For each post.message: <= 400 characters, avoid markdown headings, keep paragraphs short.
- For each post.hashtags: array of lowercase tags without '#'; the backend will prepend.
- For each post.image_query: write a concrete natural-language description suitable for Pexels search (no hashtags, no emojis).
- If you are not confident about a direct image_url, set image_url to null and rely on image_query.
- Never invent stock data; rely on the tools.

Input payload is a JSON string containing:
- account: details about the configured Facebook page
- user_id: operator identifier
- mode: "manual" or "scheduled"
- prompt: optional nudges from the user
- overrides: extra contextual data (e.g. schedule info). When overrides.post_count is provided, you MUST return exactly that many posts (bounded between 1 and 6). If it is missing, pick a sensible length based on the context (for example, 1 hero post for flash sales or 3-4 posts for broader campaigns).

If the prompt asks for a specific theme or product, honour it while staying truthful to tool data. When unsure, highlight best-performing or high-inventory items.
"""

marketing_agent = Agent(
    name="marketingagent",
    instructions=INSTRUCTIONS,
    model=model,
    tools=[
        marketing_inventory_snapshot,
        marketing_sales_insights,
        marketing_image_search,
    ],
    output_type=CampaignResponse,
)


async def generate_campaign_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the marketing agent and return a structured campaign payload."""

    session = SQLiteSession(session_id=f"marketing_{uuid.uuid4().hex}")
    serialised_input = json.dumps(payload)

    logger.debug("Running marketing agent with payload: %s", serialised_input)

    response = await Runner.run(
        starting_agent=marketing_agent,
        input=serialised_input,
        session=session,
    )

    raw_output = response.final_output if hasattr(response, "final_output") else str(response)
    logger.debug("Marketing agent raw output: %s", raw_output)

    # When using structured output, the runner should already coerce to CampaignResponse.
    if isinstance(raw_output, CampaignResponse):
        return raw_output.model_dump()

    try:
        structured = json.loads(raw_output)
    except json.JSONDecodeError as exc:  # pragma: no cover - agent contract violation
        logger.error("Marketing agent returned non-JSON payload: %s", exc)
        raise ValueError("Marketing agent response was not valid JSON") from exc

    if not isinstance(structured, dict):
        raise ValueError("Marketing agent response must be an object")

    # Validate against CampaignResponse to fail fast if the shape is wrong.
    campaign = CampaignResponse.model_validate(structured)
    return campaign.model_dump()
