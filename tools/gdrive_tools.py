"""
Google Drive Tools for Agent
These tools allow the agent to interact with Google Drive through the MCP server.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from tools.gdrive_mcp_client import get_gdrive_client
import os


class FileSearchResult(BaseModel):
    """Result from searching Google Drive files."""
    files_found: int
    file_list: str
    query: str


class FileContent(BaseModel):
    """Content read from a Google Drive file."""
    file_id: str
    mime_type: str
    content: str
    is_text: bool


class FileListResult(BaseModel):
    """Result from listing Google Drive files."""
    files: List[Dict[str, str]]
    has_more: bool
    next_cursor: Optional[str] = None


class DocumentCreateResult(BaseModel):
    """Result from creating a Google Doc."""
    document_id: str
    document_url: str
    title: str
    parent_folder_id: Optional[str] = None


# Global client instance (will be initialized when needed)
_gdrive_client = None


async def _ensure_client():
    """Ensure the Google Drive MCP client is initialized."""
    global _gdrive_client
    if _gdrive_client is None:
        credentials_path = os.getenv(
            "GDRIVE_CREDENTIALS_PATH",
            ".gdrive-server-credentials.json"
        )
        # Note: In production, you might want to handle this differently
        # For now, we'll create a new client each time
        pass
    return _gdrive_client


async def search_gdrive_files(query: str) -> FileSearchResult:
    """
    Search for files in Google Drive.
    
    Args:
        query: Search query string (e.g., "quarterly report", "budget 2024")
    
    Returns:
        FileSearchResult with number of files found and their details
    
    Example:
        result = await search_gdrive_files("annual report")
        print(f"Found {result.files_found} files")
    """
    async with get_gdrive_client() as client:
        response = await client.search_files(query)
        
        # Parse the response
        content = response.get("content", [{}])[0]
        text = content.get("text", "No results found")
        
        # Extract count from text like "Found 5 files:\n..."
        lines = text.split("\n")
        first_line = lines[0] if lines else ""
        
        # Simple parsing
        files_found = 0
        if "Found" in first_line:
            try:
                files_found = int(first_line.split("Found")[1].split("files")[0].strip())
            except:
                pass
        
        file_list = "\n".join(lines[1:]) if len(lines) > 1 else "No files listed"
        
        return FileSearchResult(
            files_found=files_found,
            file_list=file_list,
            query=query
        )


async def read_gdrive_file(file_id: str) -> FileContent:
    """
    Read the contents of a specific Google Drive file.
    
    Args:
        file_id: The Google Drive file ID
    
    Returns:
        FileContent with the file's content and metadata
    
    Example:
        content = await read_gdrive_file("1ABC...XYZ")
        print(content.content)
    """
    async with get_gdrive_client() as client:
        uri = f"gdrive:///{file_id}"
        response = await client.read_resource(uri)
        
        contents = response.get("contents", [{}])[0]
        mime_type = contents.get("mimeType", "unknown")
        
        # Check if it's text or binary
        is_text = "text" in mime_type or "markdown" in mime_type
        
        if is_text:
            content = contents.get("text", "")
        else:
            # For binary files, we get base64 encoded data
            blob = contents.get("blob", "")
            content = f"[Binary file - {mime_type}] Base64 length: {len(blob)}"
        
        return FileContent(
            file_id=file_id,
            mime_type=mime_type,
            content=content,
            is_text=is_text
        )


async def list_gdrive_files(cursor: Optional[str] = None) -> FileListResult:
    """
    List files from Google Drive (paginated).
    
    Args:
        cursor: Optional pagination cursor to get next page of results
    
    Returns:
        FileListResult with list of files and pagination info
    
    Example:
        result = await list_gdrive_files()
        for file in result.files:
            print(f"{file['name']} ({file['mimeType']})")
    """
    async with get_gdrive_client() as client:
        response = await client.list_resources(cursor)
        
        resources = response.get("resources", [])
        next_cursor = response.get("nextCursor")
        
        files = []
        for resource in resources:
            files.append({
                "id": resource.get("uri", "").replace("gdrive:///", ""),
                "name": resource.get("name", "Unknown"),
                "mimeType": resource.get("mimeType", "unknown")
            })
        
        return FileListResult(
            files=files,
            has_more=next_cursor is not None,
            next_cursor=next_cursor
        )


async def create_gdrive_document(
    title: str,
    content: str,
    parent_folder_id: Optional[str] = None,
) -> DocumentCreateResult:
    """Create a Google Doc using the MCP client's credentials."""
    async with get_gdrive_client() as client:
        metadata = await client.create_google_doc(title, content, parent_folder_id)
        return DocumentCreateResult(
            document_id=metadata["id"],
            document_url=metadata["url"],
            title=title,
            parent_folder_id=parent_folder_id,
        )


# Function tool wrappers for the agent
async def tool_search_gdrive(query: str) -> dict:
    """
    Tool function to search Google Drive files.
    Can be used by the agent to find files based on a query.
    
    Args:
        query: The search query
        
    Returns:
        Dictionary with search results
    """
    result = await search_gdrive_files(query)
    return {
        "success": True,
        "files_found": result.files_found,
        "files": result.file_list,
        "query": result.query
    }


async def tool_read_gdrive_file(file_id: str) -> dict:
    """
    Tool function to read a Google Drive file.
    Can be used by the agent to retrieve file contents.
    
    Args:
        file_id: The Google Drive file ID
        
    Returns:
        Dictionary with file content and metadata
    """
    try:
        result = await read_gdrive_file(file_id)
        return {
            "success": True,
            "file_id": result.file_id,
            "mime_type": result.mime_type,
            "content": result.content,
            "is_text": result.is_text
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "file_id": file_id
        }


async def tool_list_gdrive_files() -> dict:
    """
    Tool function to list Google Drive files.
    Can be used by the agent to browse available files.
    
    Returns:
        Dictionary with list of files
    """
    result = await list_gdrive_files()
    return {
        "success": True,
        "files": result.files,
        "has_more": result.has_more,
        "count": len(result.files)
    }


async def tool_create_gdrive_document(
    title: str,
    content: str,
    parent_folder_id: Optional[str] = None,
) -> dict:
    """Tool to create a Google Doc.

    Returns a dictionary with document metadata or an error message.
    """
    try:
        result = await create_gdrive_document(title, content, parent_folder_id)
        return {
            "success": True,
            "document_id": result.document_id,
            "document_url": result.document_url,
            "title": result.title,
            "parent_folder_id": result.parent_folder_id,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "title": title,
        }
