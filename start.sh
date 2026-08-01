#!/usr/bin/env sh
# Single start path for mcphosting.io — do not also run python server.py.
set -eu
HOST="${FASTMCP_HOST:-${HOST:-0.0.0.0}}"
PORT="${PORT:-${FASTMCP_PORT:-8000}}"
export FASTMCP_STATELESS_HTTP="${FASTMCP_STATELESS_HTTP:-true}"
export FASTMCP_JSON_RESPONSE="${FASTMCP_JSON_RESPONSE:-true}"
exec fastmcp run server.py:mcp --transport http --host "$HOST" --port "$PORT" --stateless
