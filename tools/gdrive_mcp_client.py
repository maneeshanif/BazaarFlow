"""
Google Drive MCP Client
This module provides a client to interact with the Google Drive MCP server.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GDriveMCPClient:
    """Client for interacting with Google Drive MCP server via stdio."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the Google Drive MCP client.
        
        Args:
            credentials_path: Path to the .gdrive-server-credentials.json file.
                            If not provided, will use GDRIVE_CREDENTIALS_PATH env var.
        """
        self.credentials_path = credentials_path or os.getenv(
            "GDRIVE_CREDENTIALS_PATH",
            ".gdrive-server-credentials.json"
        )
        self.process = None
        self.request_id = 0

    # ------------------------------------------------------------------
    # Credential helpers
    # ------------------------------------------------------------------

    def _ensure_credentials_file(self) -> None:
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(
                "Google Drive credentials not found. Run `python setup_gdrive.py` "
                "and complete authentication first."
            )

    def _load_user_credentials(self, scopes: List[str]) -> Credentials:
        """Load OAuth credentials saved by the MCP authentication flow."""
        self._ensure_credentials_file()

        creds = Credentials.from_authorized_user_file(self.credentials_path, scopes)

        # Ensure the stored credentials already contain the required scopes.
        stored_scopes = set(creds.scopes or [])
        missing_scopes = [scope for scope in scopes if scope not in stored_scopes]
        if missing_scopes:
            raise PermissionError(
                "The saved Google Drive credentials do not include the required scopes: "
                f"{', '.join(missing_scopes)}. Re-run `python setup_gdrive.py` and when "
                "prompted, authorize the application with full Drive access (drive.file) "
                "and the Google Docs API scope."
            )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Persist refreshed credentials
            with open(self.credentials_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())

        return creds

    # ------------------------------------------------------------------
    
    async def start(self):
        """Start the Google Drive MCP server process."""
        # Check if npx is available
        try:
            # Start the MCP server process with npx
            self.process = await asyncio.create_subprocess_exec(
                "npx",
                "-y",
                "@modelcontextprotocol/server-gdrive",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={
                    **os.environ,
                    "GDRIVE_CREDENTIALS_PATH": self.credentials_path
                }
            )
        except FileNotFoundError:
            raise RuntimeError(
                "npx not found. Please install Node.js and npm first.\n"
                "Visit: https://nodejs.org/"
            )
    
    async def stop(self):
        """Stop the Google Drive MCP server process."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
    
    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to the MCP server.
        
        Args:
            method: The method to call
            params: Parameters for the method
            
        Returns:
            The response from the server
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server not started")
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        if self.process.stdout:
            response_line = await self.process.stdout.readline()
            response = json.loads(response_line.decode())
            
            if "error" in response:
                raise RuntimeError(f"MCP Error: {response['error']}")
            
            return response.get("result", {})
        
        raise RuntimeError("No stdout available from MCP server")
    
    async def list_resources(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        List available Google Drive files.
        
        Args:
            cursor: Pagination cursor for next page
            
        Returns:
            Dictionary with resources list and optional nextCursor
        """
        params = {}
        if cursor:
            params["cursor"] = cursor
        
        return await self._send_request("resources/list", params)
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a specific Google Drive file.
        
        Args:
            uri: The resource URI (e.g., "gdrive:///file_id")
            
        Returns:
            Dictionary with file contents
        """
        return await self._send_request("resources/read", {"uri": uri})
    
    async def search_files(self, query: str) -> Dict[str, Any]:
        """
        Search for files in Google Drive.
        
        Args:
            query: Search query string
            
        Returns:
            Dictionary with search results
        """
        return await self._send_request("tools/call", {
            "name": "search",
            "arguments": {"query": query}
        })
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.
        
        Returns:
            List of available tools
        """
        result = await self._send_request("tools/list")
        return result.get("tools", [])

    # ------------------------------------------------------------------
    # Google Drive write helpers (outside standard MCP surface)
    # ------------------------------------------------------------------

    async def create_google_doc(
        self,
        title: str,
        content: str,
        parent_folder_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Create a Google Doc with the provided content and return its metadata."""

        scopes = [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/documents",
        ]

        creds = await asyncio.to_thread(self._load_user_credentials, scopes)

        def _create() -> Dict[str, str]:
            try:
                drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

                file_metadata: Dict[str, Any] = {
                    "name": title,
                    "mimeType": "application/vnd.google-apps.document",
                }
                if parent_folder_id:
                    file_metadata["parents"] = [parent_folder_id]

                file = drive_service.files().create(body=file_metadata, fields="id").execute()
                document_id = file["id"]

                docs_service = build("docs", "v1", credentials=creds, cache_discovery=False)
                requests = [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": content,
                        }
                    }
                ]

                docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={"requests": requests},
                ).execute()

                return {
                    "id": document_id,
                    "url": f"https://docs.google.com/document/d/{document_id}/edit",
                }
            except HttpError as exc:
                raise RuntimeError(
                    "Failed to create Google Doc. Ensure your credentials were authorized "
                    "with Drive write access and the Docs API."
                ) from exc

        return await asyncio.to_thread(_create)


@asynccontextmanager
async def get_gdrive_client(credentials_path: Optional[str] = None):
    """
    Context manager for Google Drive MCP client.
    
    Usage:
        async with get_gdrive_client() as client:
            results = await client.search_files("quarterly report")
    """
    client = GDriveMCPClient(credentials_path)
    await client.start()
    try:
        yield client
    finally:
        await client.stop()
