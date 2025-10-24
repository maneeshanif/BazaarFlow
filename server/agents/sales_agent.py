from config import model
from agents import Agent


sale_agent = Agent(
    name="sales_agent",
    instructions="You are a sales agent. Your goal is to sell the product to the customer.",
    model=model,
)

