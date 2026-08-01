"""ASGI entry for container / uvicorn hosts (not used by mcphosting mcp import)."""

from server import mcp

app = mcp.http_app()
