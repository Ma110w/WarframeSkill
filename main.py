"""Horizon default entrypoint alias (`main.py` → same server as `server.py:mcp`)."""

from server import mcp

__all__ = ["mcp"]
