# agents/inventory_agent.py

from agents import Agent, Runner, function_tool
from tools.inventory_tool import check_inventory
from guardrails.input_guardrails import product_name_input_guardrail
from guardrails.output_guardrail import inventory_output_guardrail
from pydantic import BaseModel
from typing import Optional
from main import model

# Define the structured output type
class InventoryOutput(BaseModel):
    product: str
    available: bool
    quantity: Optional[int] = None

@function_tool
def tool_check_inventory(product_name: str) -> InventoryOutput:
    """
    Tool that checks the inventory for the given product name.
    If found: returns product name, availability True/False, quantity.
    If not found: available=False, quantity=None.
    """
    item = check_inventory(product_name)
    if item is None:
        return InventoryOutput(product=product_name, available=False, quantity=None)
    else:
        return InventoryOutput(
            product=product_name,
            available=(item["quantity"] > 0),
            quantity=item["quantity"]
        )

class InventoryAgent(Agent[InventoryOutput]):
    def __init__(self):
        super().__init__(
            name="InventoryAgent",
            instructions=(
                "You are an inventory-checking assistant. "
                "When a user asks about a product, you should check the inventory using your tool, "
                "and then respond clearly whether it is available or not, and if available show the quantity."
            ),
            tools=[tool_check_inventory],
            input_guardrails=[product_name_input_guardrail],
            output_guardrails=[inventory_output_guardrail],
            output_type=InventoryOutput,
            model=model
        )

    async def run(self, input: str | list) -> InventoryOutput:
        # The Agent SDK's run might auto-handle tool invocation,
        # but if you want custom logic you could override here.
        result = await super().run(input)
        return result.final_output
