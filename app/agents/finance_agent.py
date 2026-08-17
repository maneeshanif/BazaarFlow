from app.core.settings import settings
"""Finance agent orchestrated via the OpenAI Agents SDK."""
import logging
import os

from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel
from dotenv import find_dotenv, load_dotenv

from app.agents.tools.finance_tool import (
    payment_status_overview,
    payment_method_breakdown,
    recent_pending_payments,
    create_customer_order,
)
from agents import set_tracing_disabled

logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())
set_tracing_disabled(True)

_api_key = settings.GEMINI_API_KEY
if not _api_key:
    logger.warning(
        "GEMINI_API_KEY not set; using placeholder key. Finance agent will not reach the model until configured."
    )
    _api_key = "placeholder-test-key"

_external_client = AsyncOpenAI(
    api_key=_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
_model = OpenAIChatCompletionsModel(
    model=settings.GEMINI_MODEL,
    openai_client=_external_client,
)

finance_agent = Agent(
    name="financeagent",
    instructions="""
You are FinanceAgent, a payments analyst and order manager for BazaarFlow.

Always rely on the provided tools for numbers before answering. Be concise (<350 characters),
use friendly emojis, and prefer PKR formatted totals.

When users ask about:
- status or outstanding payments → call payment_status_overview or recent_pending_payments
- method breakdowns → call payment_method_breakdown
- placing orders, buying products, or checkout → use create_customer_order

For order placement:
1. Collect required info conversationally: customer_name, customer_phone, product_name, quantity, delivery_address
2. Optional fields: budget, notes
3. Once you have all required info, call create_customer_order to save the order
4. Confirm the order ID and details to the customer

Never invent amounts, counts, or order details if the tools return empty data.
""",
    model=_model,
    tools=[
        payment_status_overview,
        payment_method_breakdown,
        recent_pending_payments,
        create_customer_order,
    ],
)
