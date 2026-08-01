"""Default entrypoint for Horizon / mcphosting.

Imports the FastMCP server object from `server.py`.
"""

from __future__ import annotations

import os

from server import mcp

__all__ = ["mcp"]


def main() -> None:
    # Managed hosts set PORT and expect Streamable HTTP on 0.0.0.0.
    if os.environ.get("PORT") or os.environ.get("FASTMCP_PORT"):
        host = os.environ.get("FASTMCP_HOST") or os.environ.get("HOST") or "0.0.0.0"
        if host in {"127.0.0.1", "localhost"}:
            host = "0.0.0.0"
        port = int(os.environ.get("PORT") or os.environ.get("FASTMCP_PORT") or "8000")
        mcp.run(
            transport="http",
            host=host,
            port=port,
            stateless_http=True,
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
