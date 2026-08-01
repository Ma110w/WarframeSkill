# Warframe MCP Server

FastMCP server for [Warframe.market](https://docs.warframe.market/docs/intro/) and [WarframeStat.us](https://docs.warframestat.us/).

Author: snakeplisken47

## Horizon deploy

1. Repo: [Ma110w/WarframeSkill](https://github.com/Ma110w/WarframeSkill), branch **`main`**
2. Entrypoint: **`main.py`** (or `main.py:mcp`)
3. Dependency file: `requirements.txt` (Horizon installs FastMCP for you)
4. After deploy, open **Deployments** and confirm status is **Live**

### Connect (this is usually the timeout cause)

Horizon authentication is **on by default**. A bare URL with no credential often hangs until the client times out.

In the Horizon dashboard: open the server → **Connect** → **Cursor**, and use the generated snippet.

Or manually (API key from Horizon, prefix `fmcp_`):

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

For interactive clients that support MCP OAuth, the URL alone is enough after you complete Horizon sign-in.

To make the endpoint public (no Horizon auth), disable Horizon authentication on the server (plan-dependent).

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install fastmcp httpx
python main.py
```

## Tools

Market (`wfm_*`): search items, item details, top orders, order list, price check.

Worldstate (`ws_*`): sortie, archon hunt, fissures, invasions, nightwave, Baro, cycles, alerts, arbitration, steel path, daily deals, events, item/drop search, plus `ping`.
