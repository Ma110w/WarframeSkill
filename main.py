"""Explicit runner for local / mcphosting start commands.

Prefer start command:
  fastmcp run server.py:mcp --transport http --host 0.0.0.0 --port $PORT --stateless
or:
  sh start.sh
"""

from __future__ import annotations

import os
import socket
import sys
import time

from server import mcp

__all__ = ["mcp"]


def _port_open(host: str, port: int) -> bool:
    probe_host = "127.0.0.1" if host in {"0.0.0.0", "::", ""} else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((probe_host, port)) == 0


def main() -> None:
    port_set = bool(os.environ.get("PORT") or os.environ.get("FASTMCP_PORT"))
    host = os.environ.get("FASTMCP_HOST") or os.environ.get("HOST") or (
        "0.0.0.0" if port_set else "127.0.0.1"
    )
    if port_set and host in {"127.0.0.1", "localhost"}:
        host = "0.0.0.0"
    port = int(os.environ.get("PORT") or os.environ.get("FASTMCP_PORT") or "8000")

    if not port_set:
        mcp.run()
        return

    # If a sibling starter (platform auto-run) already owns PORT, do not bind again.
    # Stay alive so process supervisors that expect a long-running PID are happy.
    if _port_open(host, port):
        print(
            f"Port {port} already has a listener; skipping duplicate FastMCP bind.",
            flush=True,
        )
        while True:
            time.sleep(3600)

    # Short retry for rolling deploys where the old process is dying.
    for attempt in range(1, 16):
        if attempt > 1 and _port_open(host, port):
            print(
                f"Port {port} taken during retry; assuming primary listener is up.",
                flush=True,
            )
            while True:
                time.sleep(3600)
        try:
            mcp.run(
                transport="http",
                host=host,
                port=port,
                stateless_http=True,
            )
            return
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            if code == 0:
                raise
            print(
                f"MCP bind/startup failed (attempt {attempt}/15, exit={code}); retrying...",
                flush=True,
            )
            time.sleep(1)

    print(f"Failed to bind MCP on {host}:{port}", flush=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
