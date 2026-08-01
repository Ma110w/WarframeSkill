# Warframe MCP

FastMCP server for [Warframe.market](https://docs.warframe.market/docs/intro/), [WarframeStat.us](https://docs.warframestat.us/), and [Overframe.gg](https://overframe.gg/) builds.

Author: snakeplisken47

## Remote host (ChatGPT skill) — free options

Honest take: **there is no truly free always-on generic Docker host** that matches Cloudflare Containers without a card / paid plan. For this FastMCP project, the best free path is a **managed MCP host**, not a general PaaS.

### Recommended: Prefect Horizon (free personal tier)

Built by the FastMCP team. Free for personal projects, GitHub deploy, HTTPS URL like `https://<name>.fastmcp.app/mcp`.

1. Open [horizon.prefect.io](https://horizon.prefect.io) and sign in with GitHub.
2. Select repo `Ma110w/WarframeSkill`.
3. Entrypoint: `server.py:mcp` (deps from `requirements.txt`).
4. Deploy → use the resulting `/mcp` URL in ChatGPT (Developer Mode → connector).

Docs: [Prefect Horizon / FastMCP deploy](https://gofastmcp.com/deployment/fastmcp-cloud)

Handshake hardening in this repo (`FASTMCP_STATELESS_HTTP` + immediate `202` on `notifications/*`) still applies on Horizon.

### Other free-ish options (tradeoffs)

| Option | Cost | Fit for ChatGPT MCP |
| --- | --- | --- |
| **Prefect Horizon** | Free personal | Best match — FastMCP-native |
| **mcphosting.io** | Free tier | Already tried; `notifications/initialized` hung → Cloudflare **502** |
| **Google Cloud Run** | Free tier (scale-to-zero) | Works with our `Dockerfile`; cold starts can break picky clients |
| **Render free** | Free | Sleeps after ~15m idle → bad for connectors |
| **Railway** | Trial / limited credits | Not permanently free |
| **Cloudflare Containers** | Workers Paid **$5/mo** | Works well; **canceled** on this account (ends Aug 30, 2026) |

Cloudflare Worker `warframe-mcp` was deleted after cancel. Repo still has optional Container scaffolding (`Dockerfile`, `wrangler.toml`, GH Actions) if you ever re-enable Paid.

### Horizon-style / mcphosting entrypoint

Entrypoint object: `server.py` → `mcp`. Dependencies: `requirements.txt`. Do not add a Procfile or second runner.

## Local (optional, Cursor only)

```bash
pip install -r requirements.txt
python server.py
```

Cursor stdio example:

```json
"warframe": {
  "command": "M:\\WarframeSkill\\.venv\\Scripts\\python.exe",
  "args": ["M:\\WarframeSkill\\server.py"]
}
```

## Tools

`ping`, market tools (`wfm_*`), worldstate tools (`ws_*`), Overframe tools (`of_*`), Platinum CAD tools (`plat_*`).

### Overframe flow

1. `of_search_items` — same idea as the site search box (item → Overframe id)
2. `of_list_builds` — builds for that item (optional `title` filter)
3. `of_get_build` — full build with resolved mod names / ranks / drain
4. `of_top_mods` — most-used mods for an item

If static DB loads start failing after an Overframe frontend deploy, set `OVERFRAME_WEBPACK_URL` to the current `https://static.overframe.gg/_next/static/chunks/webpack-*.js` URL from the site.

### Platinum → CAD (Ontario)

Pack list prices from [WARFRAME Wiki: Platinum](https://wiki.warframe.com/w/Platinum). Tax defaults to **Ontario HST 13%** added at checkout (Steam-style).

1. `plat_list_packs` — available packs + CAD/USD for pc/xbox/playstation
2. `plat_price_pack` — one pack with tax / optional coupon
3. `plat_recommend_packs` — cheapest pack combo to reach a platinum target
4. `plat_to_cad` — estimate CAD cost for N platinum via store packs
