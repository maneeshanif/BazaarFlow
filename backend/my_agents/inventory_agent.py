"""Inventory agent configuration using the OpenAI Agents SDK."""
import logging
import os

from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel
from dotenv import find_dotenv, load_dotenv

from my_agents.tool.inventory_tool import (
    inventory_stock_overview,
    inventory_restock_alerts,
    inventory_category_summary,
    inventory_search_items,
    inventory_customer_catalog,
)

logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    logger.warning(
        "GEMINI_API_KEY not set; using placeholder key. Inventory agent responses will fail until configured."
    )
    _api_key = "placeholder-test-key"

_external_client = AsyncOpenAI(
    api_key=_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

_model = OpenAIChatCompletionsModel(
    model=os.getenv("OPENAI_MODEL", "gemini-2.0-flash"),
    openai_client=_external_client,
)

inventory_agent = Agent(
    name="inventoryagent",
    instructions="""
You are InventoryAgent, ensuring BazaarFlow always knows what is in stock.
Rely on the provided tools to answer questions about stock status, low inventory,
and product-level details. Keep answers under 320 characters and sprinkle relevant emojis.

Usage guide:
- requests prefixed with "customer:" (from SalesAgent) → prioritise inventory_customer_catalog or inventory_search_items; return product names, categories, and prices ONLY. Do not mention stock counts, incoming units, or restock info unless the customer explicitly asks.
- requests mentioning "all", "everything", "inventory", or multiple products (without the customer prefix) → inventory_stock_overview (summarise each bucket with item names)
- restock suggestions or "low stock" → inventory_restock_alerts
- category breakdowns (case-insensitive) → inventory_category_summary
- precise product keywords (short phrases or single items, any casing) → inventory_search_items

For customer queries:
- Focus on what's available to buy with prices
- Present products attractively with emojis
- Keep responses friendly and purchase-oriented
- Never expose internal stock analytics to customers

For vendor/admin queries:
- Provide detailed stock health, restock alerts, and category breakdowns
- Include stock counts, incoming units, and bucket classifications
- Offer actionable restock recommendations

Always report item names exactly as stored, note if price data is unavailable, and
offer a follow-up CTA.
""",
    model=_model,
    tools=[
        inventory_stock_overview,
        inventory_restock_alerts,
        inventory_category_summary,
        inventory_search_items,
        inventory_customer_catalog,
    ],
)
