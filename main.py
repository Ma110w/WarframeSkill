"""Horizon default entrypoint.

Horizon installs FastMCP itself and starts this server over HTTP.
Keep this file import-light; put tools on `mcp` in `server.py`.
"""

from server import mcp

__all__ = ["mcp"]

if __name__ == "__main__":
    mcp.run()
