"""
Agents module for inventory management and Google Drive integration.

Note: This is a local package. The 'agents' library from pip (openai-agents)
should be imported directly, not from this package.
"""

# Only import our custom agents, not the openai-agents library
__all__ = []

# Make imports lazy to avoid circular dependencies
def get_inventory_agent():
    from agents.inventory_agent import InventoryAgent
    return InventoryAgent

def get_enhanced_inventory_agent():
    from agents.enhanced_inventory_agent import EnhancedInventoryAgent
    return EnhancedInventoryAgent
