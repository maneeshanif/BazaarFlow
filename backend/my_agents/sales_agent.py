
from agents import Agent
from dotenv import load_dotenv, find_dotenv
from agents import AsyncOpenAI, OpenAIChatCompletionsModel
import os
# import tools from separate module
from my_agents.tool.sales_tool import (
    lookup_product,
    list_all_products,
    get_product_by_price_range,
    get_product_by_category,
)

# Import MCP server tools
# import sys
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp_server.server import PRODUCTS_DB,mcp
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams

load_dotenv(find_dotenv())

api_key = os.getenv("GEMINI_API_KEY")

# Use environment variables for external LLM client configuration
external_client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

model = OpenAIChatCompletionsModel(
    model=os.getenv("OPENAI_MODEL", "gemini-2.0-flash"),
    openai_client=external_client,
)
# -------------------------- Sales Agent (MCP Server Integration) ------------------------
sales_agent = Agent(
    name="salesagent",
    instructions="""
You are SalesAgent, a BazaarFlow sales expert. Use the provided tools whenever product information, availability, pricing, or categories are requested.

Always prefer calling an explicit tool over guessing. When a tool is called, return the tool output followed by a concise CTA.

If the user asks about products, availability, price ranges, or categories — CALL the correct tool.

Do not invent product names or prices. If a tool returns no result, ask clarifying questions (e.g., model, use-case, budget).

Keep replies short (<=300 chars) and use some emjojis to make it user friendly.

Examples:
 - What phones do you have? -> call lookup_product('phone')
 - Show me all products -> call list_all_products()
 - Products under 2000 -> call get_product_by_price_range(0,2000)
 - Show mobile devices -> call get_product_by_category('mobile')
""",
    model=model,
    tools=[lookup_product, list_all_products, get_product_by_price_range, get_product_by_category],
)
