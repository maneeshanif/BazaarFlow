"""Marketing automation agent orchestrated through the Agents SDK."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict

from agents import Agent, Runner, SQLiteSession, set_tracing_disabled
from pydantic import BaseModel, Field

from .model import model
from .tool.marketing_tool import (
    marketing_image_search,
    marketing_inventory_snapshot,
    marketing_sales_insights,
)

logger = logging.getLogger(__name__)

set_tracing_disabled(True)


OUTPUT_SCHEMA = {
    "message": "Primary caption text. Keep it under 400 characters.",
    "hashtags": "List of 3-6 concise hashtags (without duplicates).",
    "angle": "Short descriptor of the campaign angle (e.g. 'Limited-time restock hype').",
    "image_url": "Optional direct image URL to pair with the post.",
    "image_query": "Fallback search phrase if no image_url is provided.",
    "product_sku": "Optional SKU to reference in analytics.",
    "call_to_action": "One-line CTA to append in UI dashboards.",
}

OUTPUT_SCHEMA_JSON = json.dumps(OUTPUT_SCHEMA)


class MarketingAgentResponse(BaseModel):
    message: str = Field(..., max_length=400, description=OUTPUT_SCHEMA["message"])
    hashtags: list[str] = Field(default_factory=list, description=OUTPUT_SCHEMA["hashtags"], max_items=6)
    angle: str | None = Field(default=None, description=OUTPUT_SCHEMA["angle"])
    image_url: str | None = Field(default=None, description=OUTPUT_SCHEMA["image_url"])
    image_query: str | None = Field(default=None, description=OUTPUT_SCHEMA["image_query"])
    product_sku: str | None = Field(default=None, description=OUTPUT_SCHEMA["product_sku"])
    call_to_action: str | None = Field(default=None, description=OUTPUT_SCHEMA["call_to_action"])

INSTRUCTIONS = f"""
You are MarketingAgent, crafting social-ready Facebook campaigns for BazaarFlow.

Your responsibilities:
- Analyse inventory health, sales momentum, and imagery options using the available tools.
- Craft a concise caption that blends urgency, social proof, and a clear CTA.
- Always call BOTH marketing_inventory_snapshot and marketing_sales_insights before finalising the post. Use marketing_image_search if you need photography inspiration.
- Optimise for engagement: highlight trending items, new arrivals, or restocked favourites.
- Embrace BazaarFlow's friendly voice with tasteful emoji use (2-4 max).

Output requirements:
- Return ONLY valid JSON matching this schema: {OUTPUT_SCHEMA_JSON}
- message: <= 400 characters, avoid markdown headings, keep paragraphs short.
- hashtags: array of lowercase tags without '#'; the backend will prepend.
- Provide angle and call_to_action in sentence case.
- If you did not find an image URL, set image_url to null and supply image_query to guide downstream search.
- Never invent stock data; rely on the tools.

Input payload is a JSON string containing:
- account: details about the configured Facebook page
- user_id: operator identifier
- mode: "manual" or "scheduled"
- prompt: optional nudges from the user
- overrides: extra contextual data (e.g. schedule info)

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
    output_type=MarketingAgentResponse,
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

    if isinstance(raw_output, MarketingAgentResponse):
        return raw_output.model_dump()

    try:
        structured = json.loads(raw_output)
    except json.JSONDecodeError as exc:  # pragma: no cover - agent contract violation
        logger.error("Marketing agent returned non-JSON payload: %s", exc)
        raise ValueError("Marketing agent response was not valid JSON") from exc

    if not isinstance(structured, dict):
        raise ValueError("Marketing agent response must be an object")

    return structured
