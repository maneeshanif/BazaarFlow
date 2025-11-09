"""
Test script for Google Drive MCP integration
This script tests the connection and basic functionality of the Google Drive MCP client.
"""

import asyncio
import sys
from pathlib import Path


async def test_gdrive_connection():
    """Test basic connection to Google Drive MCP server."""
    print("\n" + "=" * 60)
    print("Testing Google Drive MCP Connection")
    print("=" * 60)
    
    try:
        from tools.gdrive_mcp_client import get_gdrive_client
        
        print("\n1. Testing client initialization...")
        async with get_gdrive_client() as client:
            print("   ✓ Client initialized successfully")
            
            print("\n2. Testing list_tools...")
            tools = await client.list_tools()
            print(f"   ✓ Found {len(tools)} tools:")
            for tool in tools:
                print(f"     - {tool.get('name', 'Unknown')}")
            
            print("\n3. Testing list_resources (first page)...")
            resources = await client.list_resources()
            files = resources.get("resources", [])
            print(f"   ✓ Found {len(files)} files:")
            for i, file in enumerate(files[:5], 1):  # Show first 5
                print(f"     {i}. {file.get('name', 'Unknown')} ({file.get('mimeType', 'unknown')})")
            if len(files) > 5:
                print(f"     ... and {len(files) - 5} more")
            
            print("\n4. Testing search...")
            search_query = "test"
            print(f"   Searching for: '{search_query}'")
            search_results = await client.search_files(search_query)
            content = search_results.get("content", [{}])[0]
            text = content.get("text", "No results")
            print(f"   ✓ Search completed:")
            for line in text.split("\n")[:3]:  # Show first 3 lines
                print(f"     {line}")
            
            print("\n" + "=" * 60)
            print("✓ All tests passed!")
            print("=" * 60)
            return True
            
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False


async def test_gdrive_tools():
    """Test the Google Drive tool functions."""
    print("\n" + "=" * 60)
    print("Testing Google Drive Tool Functions")
    print("=" * 60)
    
    try:
        from tools.gdrive_tools import (
            tool_search_gdrive,
            tool_list_gdrive_files
        )
        
        print("\n1. Testing tool_search_gdrive...")
        result = await tool_search_gdrive("document")
        if result.get("success"):
            print(f"   ✓ Search successful: Found {result.get('files_found', 0)} files")
        else:
            print(f"   ✗ Search failed: {result.get('error', 'Unknown error')}")
        
        print("\n2. Testing tool_list_gdrive_files...")
        result = await tool_list_gdrive_files()
        if result.get("success"):
            print(f"   ✓ List successful: Found {result.get('count', 0)} files")
            files = result.get("files", [])
            for i, file in enumerate(files[:3], 1):  # Show first 3
                print(f"     {i}. {file.get('name', 'Unknown')}")
        else:
            print(f"   ✗ List failed: {result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 60)
        print("✓ Tool function tests completed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Tool function tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  Google Drive MCP Integration Test Suite")
    print("=" * 70)
    
    # Check prerequisites
    print("\nChecking prerequisites...")
    
    # Check credentials
    creds_path = Path(".gdrive-server-credentials.json")
    if not creds_path.exists():
        print("\n✗ ERROR: Credentials file not found!")
        print("  Please run: python setup_gdrive.py")
        sys.exit(1)
    print("✓ Credentials file found")
    
    # Check Node.js
    import subprocess
    try:
        subprocess.run(
            ["node", "--version"],
            capture_output=True,
            check=True
        )
        print("✓ Node.js is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n✗ ERROR: Node.js not found!")
        print("  Please install Node.js from: https://nodejs.org/")
        sys.exit(1)
    
    # Run tests
    print("\nRunning tests...\n")
    
    test1_passed = await test_gdrive_connection()
    
    if test1_passed:
        test2_passed = await test_gdrive_tools()
    else:
        print("\nSkipping tool function tests due to connection test failure.")
        test2_passed = False
    
    # Summary
    print("\n" + "=" * 70)
    print("  Test Summary")
    print("=" * 70)
    print(f"Connection Test: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"Tool Function Test: {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print("=" * 70)
    
    if test1_passed and test2_passed:
        print("\n✓ All tests passed! Your Google Drive integration is working correctly.")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests cancelled by user.")
        sys.exit(1)
