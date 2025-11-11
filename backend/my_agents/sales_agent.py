
import logging
import os

from agents import Agent
from agents import AsyncOpenAI, OpenAIChatCompletionsModel
from dotenv import find_dotenv, load_dotenv

from my_agents.finance_agent import finance_agent
from my_agents.inventory_agent import inventory_agent

# Import MCP server tools
# import sys
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.warning(
        "GEMINI_API_KEY not set; using placeholder key. Real agent calls will fail until a valid key is configured."
    )
    api_key = "placeholder-test-key"

# Use environment variables for external LLM client configuration
external_client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

model = OpenAIChatCompletionsModel(
    model=os.getenv("OPENAI_MODEL", "gemini-2.0-flash"),
    openai_client=external_client,
)
# -------------------------- Sales Agent (Multi-Agent Orchestration) ----------------------
finance_tool = finance_agent.as_tool(
    tool_name="consult_finance_agent",
    tool_description="Delegate questions about payments, revenue trends, or outstanding invoices to the FinanceAgent.",
)

inventory_tool = inventory_agent.as_tool(
    tool_name="consult_inventory_agent",
    tool_description="Delegate stock levels, restock planning, and catalog breakdowns to the InventoryAgent.",
)

sales_agent = Agent(
    name="salesagent",
    instructions="""
You are SalesAgent, BazaarFlow's friendly sales orchestrator.

How to respond:

**Greetings ONLY (hi/hello/salaam/hey without other requests):**
- Respond warmly WITHOUT calling any tools: "👋 Hi! I'm here to help with BazaarFlow products. What can I show you today?"
- Do NOT call tools for simple greetings

**Product discovery:**
- Catalog questions ("all products", "what do you have", "show inventory") → consult_inventory_agent with "customer:catalog overview"
- Specific product search (any casing) → consult_inventory_agent with "customer:search [product]"
- Both return product names and prices (NO stock counts)

**Order placement:**
- When users want to buy/order/purchase → consult_finance_agent with "user wants to order [product name]"
- Finance agent handles all order details collection (name, phone, quantity, address)

**Payment queries:**
- Payment status, invoices, revenue → consult_finance_agent

Rules:
- Simple greetings = direct response, NO tool calls
- All other requests = MUST call exactly one tool before replying
- Keep responses ≤320 characters, show prices, never mention stock counts
- NEVER suggest /sales form or routes - handle everything through agents
- For orders, delegate completely to finance agent
""",
    model=model,
    tools=[finance_tool, inventory_tool],
)
