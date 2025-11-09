"""
Enhanced Inventory Agent with Google Drive Integration
This agent can check inventory AND access Google Drive files.
"""

from agents import Agent, function_tool, AsyncOpenAI, OpenAIChatCompletionsModel
from tools.inventory_tool import check_inventory
from tools.gdrive_tools import (
    tool_search_gdrive,
    tool_read_gdrive_file,
    tool_list_gdrive_files,
    tool_create_gdrive_document,
)
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


def _normalize_env_value(value: Optional[str]) -> Optional[str]:
    """Return a clean environment variable value or None if unset/placeholder."""
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    lowered = trimmed.lower()
    if lowered.startswith("your_") or lowered.startswith("enter_"):
        return None
    return trimmed


# Prefer Gemini; fall back to OpenAI only if a valid key is provided.
gemini_key = _normalize_env_value(os.environ.get("GEMINI_API_KEY"))
openai_key = _normalize_env_value(os.environ.get("OPENAI_API_KEY"))

model = None

if gemini_key:
    client = AsyncOpenAI(
        api_key=gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai"
    )
    model = OpenAIChatCompletionsModel(
        openai_client=client,
        model="gemini-2.0-flash-exp"
    )
elif openai_key and openai_key.startswith("sk-"):
    client = AsyncOpenAI(api_key=openai_key)
    model = OpenAIChatCompletionsModel(openai_client=client, model="gpt-4")
elif openai_key:
    print(
        "Warning: OPENAI_API_KEY is set but does not look valid (expected to start with 'sk-'). "
        "Ignoring it."
    )

if model is None:
    print(
        "Warning: No valid API key found. Set GEMINI_API_KEY for Google Gemini or OPENAI_API_KEY "
        "(starting with 'sk-') if you prefer OpenAI."
    )


# Define the structured output type for inventory
class InventoryOutput(BaseModel):
    product: str
    available: bool
    quantity: Optional[int] = None


# Define output type for Google Drive operations
class GDriveOutput(BaseModel):
    operation: str
    success: bool
    data: Dict[str, Any]


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


@function_tool
async def tool_gdrive_search(query: str) -> dict:
    """
    Search for files in Google Drive.
    Use this when the user asks to search, find, or locate files in Google Drive.
    
    Args:
        query: Search query (e.g., "budget report", "Q4 analysis")
    
    Returns:
        Dictionary with search results including files found
    """
    return await tool_search_gdrive(query)


@function_tool
async def tool_gdrive_read(file_id: str) -> dict:
    """
    Read the contents of a Google Drive file.
    Use this when the user asks to read, open, or view a specific file.
    
    Args:
        file_id: The Google Drive file ID
    
    Returns:
        Dictionary with file content and metadata
    """
    return await tool_read_gdrive_file(file_id)


@function_tool
async def tool_gdrive_list() -> dict:
    """
    List files from Google Drive.
    Use this when the user asks to list, show, or browse available files.
    
    Returns:
        Dictionary with list of files
    """
    return await tool_list_gdrive_files()


class EnhancedInventoryAgent(Agent[InventoryOutput | GDriveOutput]):
    """
    An enhanced inventory agent that can:
    1. Check product inventory
    2. Search Google Drive files
    3. Read Google Drive files
    4. List Google Drive files
    """
    
    def __init__(self, agent_model=None):
        # Use provided model or global model
        use_model = agent_model if agent_model is not None else model
        
        if use_model is None:
            raise RuntimeError(
                "No model provided. Please set GEMINI_API_KEY or OPENAI_API_KEY "
                "environment variable, or pass a model to the constructor."
            )
        
        super().__init__(
            name="EnhancedInventoryAgent",
            instructions=(
                "You are an advanced inventory and document assistant. "
                "You can:\n"
                "1. Check product inventory using the inventory tool\n"
                "2. Search for files in Google Drive\n"
                "3. Read content from Google Drive files\n"
                "4. List available Google Drive files\n"
                "5. Create new Google Docs when asked\n\n"
                "When a user asks about:\n"
                "- Product availability or quantity: Use the inventory tool\n"
                "- Finding documents or files: Use Google Drive search\n"
                "- Reading a specific file: Use Google Drive read with the file ID\n"
                "- Creating a document: Use the Google Drive create document tool\n"
                "- Listing files: Use Google Drive list\n\n"
                "Always provide clear, helpful responses based on the tool results."
            ),
            tools=[
                tool_check_inventory,
                tool_gdrive_search,
                tool_gdrive_read,
                tool_gdrive_list,
                tool_create_gdrive_document,
            ],
            model=use_model
        )

        # Allow caller to optionally specify a default output type to help the
        # SDK validate structured responses. We default to InventoryOutput, but
        # the agent may also return Google Drive payloads depending on which
        # tool executes.
        self.output_type = InventoryOutput
