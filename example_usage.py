"""
Example usage of the Enhanced Inventory Agent with Google Drive integration
"""

import asyncio
from agents import Runner
from ai_agents.enhanced_inventory_agent import EnhancedInventoryAgent
from tools.gdrive_mcp_client import get_gdrive_client

# Provide a sample Google Drive file ID for the read example
SAMPLE_FILE_ID = "1KsBOobglRgOEbFqTRpw0zToSvJ_YXkWT"
DOC_TITLE = "Inventory MCP Demo Document"
DOC_CONTENT = (
    "This document was created via the Google Drive MCP client example.\n\n"
    "It demonstrates how to create Google Docs programmatically from the"
    " inventory management agent project."
)


async def main():
    """Main function demonstrating the agent capabilities."""
    
    # Create the agent
    agent = EnhancedInventoryAgent()
    
    print("=" * 60)
    print("Enhanced Inventory Agent - Example Usage")
    print("=" * 60)
    
    # Example 1: Check Inventory
    print("\n1. Checking inventory...")
    try:
        result = await Runner.run(agent, input="Do we have any laptops in stock?")
        print(f"Result: {result.final_output}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 2: Search Google Drive
    print("\n2. Searching Google Drive...")
    try:
        result = await Runner.run(agent, input="Search for files about quarterly reports")
        print(f"Result: {result.final_output}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 3: List Google Drive files
    print("\n3. Listing Google Drive files...")
    try:
        result = await Runner.run(agent, input="List all files from Google Drive")
        print(f"Result: {result.final_output}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 4: Create a Google Doc using the MCP client directly
    print("\n4. Creating a Google Doc via MCP client...")
    try:
        async with get_gdrive_client() as client:
            creation = await client.create_google_doc(
                title=DOC_TITLE,
                content=DOC_CONTENT,
            )
        print("Result: Document created")
        print(f"  ID : {creation['id']}")
        print(f"  URL: {creation['url']}")
    except Exception as e:
        print(f"Error: {e}")

    # Example 5: Read a specific file (requires a valid file ID)
    print("\n5. Reading a Google Drive file...")
    try:
        result = await Runner.run(
            agent,
            input=f"Read the file with ID {SAMPLE_FILE_ID}"
        )
        print(f"Result: {result.final_output}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
