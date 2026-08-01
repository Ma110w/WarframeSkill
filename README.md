# Warframe MCP Server

FastMCP server for [Warframe.market](https://docs.warframe.market/docs/intro/) and [WarframeStat.us](https://docs.warframestat.us/).

Author: snakeplisken47

## mcphosting.io

Use **one** start command only (two starters → `address already in use` on `:3000`):

```bash
sh start.sh
```

or:

```bash
fastmcp run server.py:mcp --transport http --host 0.0.0.0 --port $PORT --stateless
```

- Install: `pip install -r requirements.txt`
- Do **not** also set `python server.py` if the platform auto-runs FastMCP
- `server.py` no longer self-starts on import/`__main__` for that reason

## Horizon

1. Branch **`main`**, entrypoint **`main.py:mcp`** or **`server.py:mcp`**
2. Deps: `requirements.txt`
3. Auth is on by default — use dashboard **Connect → Cursor**, or:

```json
{
  "mcpServers": {
    "warframe": {
      "url": "https://YOUR-SERVER.fastmcp.app/mcp",
      "headers": {
        "Authorization": "Bearer fmcp_YOUR_KEY"
      }
    }
  }
}
```

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set PORT=8000
python main.py
```

## Tools

Market (`wfm_*`): search items, item details, top orders, order list, price check.

Worldstate (`ws_*`): sortie, archon hunt, fissures, invasions, nightwave, Baro, cycles, alerts, arbitration, steel path, daily deals, events, item/drop search, plus `ping`.
