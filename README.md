# Warframe MCP Server

Remote MCP server for live Warframe data, built for [mcphosting.io](https://www.mcphosting.io/).

Sources:

- [Warframe.market developer docs](https://docs.warframe.market/docs/intro/) (`https://api.warframe.market/v2/`)
- [WarframeStat.us API](https://docs.warframestat.us/) (`https://api.warframestat.us/`)

Author: snakeplisken47

## Tools

### Warframe.market

| Tool | Purpose |
| --- | --- |
| `wfm_search_items` | Find tradable item slugs by name |
| `wfm_get_item` | Item details (ducats, set parts, icons) |
| `wfm_get_top_orders` | Top buy/sell orders (fast price check) |
| `wfm_get_orders` | Filtered order list |
| `wfm_price_check` | Search + top prices in one call |

Respects the public **3 req/s** market rate limit. Supports `Platform`, `Language`, and `Crossplay` headers via tool args.

### WarframeStat.us

| Tool | Purpose |
| --- | --- |
| `ws_heartbeat` | API health |
| `ws_get_worldstate` | Full worldstate (large) |
| `ws_get_field` | Any single worldstate field |
| `ws_get_sortie` / `ws_get_archon_hunt` | Daily / weekly hunts |
| `ws_get_fissures` | Void fissures (+ Steel Path / tier filters) |
| `ws_get_invasions` | Active invasions |
| `ws_get_nightwave` | Nightwave challenges |
| `ws_get_void_trader` | Baro Ki'Teer |
| `ws_get_cycles` | Cetus / Vallis / Cambion / Earth / Zariman / Duviri |
| `ws_get_alerts` / `ws_get_arbitration` | Alerts + arbitration |
| `ws_get_steel_path` / `ws_get_daily_deals` / `ws_get_events` | Rotations / Darvo / events |
| `ws_search_items` / `ws_get_item` | Item stats database |
| `ws_search_drops` | Drop locations |
| `ws_pricecheck` | Stat.us price-check helper |

## Local run

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python server.py
```

Server listens on `http://0.0.0.0:8000/mcp` (override with `HOST` / `PORT`).

### Cursor / Claude remote config

```json
{
  "mcpServers": {
    "warframe": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## Deploy to mcphosting.io

1. Push this repo to GitHub (under [Ma110w](https://github.com/Ma110w) or your account).
2. Sign in at [mcphosting.io](https://www.mcphosting.io/) with GitHub.
3. Select this repository and deploy.
4. Use **exactly one** start path (two starters = `address already in use` on `:3000`):

```bash
python server.py
# or
fastmcp run server.py:mcp --transport http --host 0.0.0.0 --port $PORT --stateless
```

Do **not** also run `uvicorn server:app` — this repo intentionally does not export a module-level ASGI `app` for that reason.

5. Install deps from `requirements.txt`.
6. Connect clients to the issued HTTPS URL ending in `/mcp`.

If you still see `address already in use`, the server retries the port for 30s (rolling deploys). After that, clear the stuck process / redeploy with a single entrypoint.

CLI option:

```bash
npm install -g mcphosting-cli
mcphosting login
mcphosting deploy
```

The server uses **Streamable HTTP** (`transport="http"`), which remote hosts require. No API keys are needed for the public endpoints used here.

### Horizon / `fastmcp run`

Entrypoint: **`server.py:mcp`** only (Horizon ignores `__main__`).  
Do not add a second start command.  
Env when `PORT` is present: `FASTMCP_HOST=0.0.0.0`, `FASTMCP_STATELESS_HTTP=true`.  
See also `fastmcp.json`.

## Notes

- Market item identifiers are **slugs** (`nikana_prime_blueprint`), not display names.
- `wfm_price_check` / `wfm_search_items` resolve human names to slugs for you.
- Full `ws_get_worldstate` responses are large; prefer field-specific tools.
- Auth-required market actions (posting orders, OAuth) are intentionally omitted — OAuth 2.0 is not public yet per Warframe.market docs.
