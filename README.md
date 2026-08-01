# Warframe MCP

FastMCP server for [Warframe.market](https://docs.warframe.market/docs/intro/), [WarframeStat.us](https://docs.warframestat.us/), and [Overframe.gg](https://overframe.gg/) builds.

Author: snakeplisken47

## Remote host (ChatGPT skill)

**Live connector URL:**

`https://warframe-mcp.snakeplisken47.workers.dev/mcp`

Hosted on **Cloudflare Containers** (not self-hosted). Handshake is hardened for streamable HTTP (`FASTMCP_STATELESS_HTTP` + immediate `202` on `notifications/*`).

- **ChatGPT:** Settings → Developer Mode → add connector → that URL (Auth: None unless you add auth later).

Requires a **Workers Paid** account ($5/mo) for Containers.

### Redeploy from GitHub

Repo secrets (already configured for Ma110w/WarframeSkill):

- `CLOUDFLARE_API_TOKEN` — Workers Scripts Edit + Workers Containers Edit
- `CLOUDFLARE_ACCOUNT_ID` — `18226a73a8a43f667d3ed3bd3fbbdd39`

Push to `main`, or run **Actions → Deploy Cloudflare Container → Run workflow**.

Scaffolding: `Dockerfile`, `http_app.py`, `src/index.ts`, `wrangler.toml`, `.github/workflows/deploy-cloudflare.yml`.

### Legacy: mcphosting

`https://warframeskill.mcphosting.app/mcp` still serves tools, but `notifications/initialized` has been hanging into Cloudflare **502**s from that gateway — unreliable for ChatGPT / mcp-remote. Prefer Cloudflare Containers above.

Horizon-style hosts (if you use one): entrypoint object `server.py` → `mcp`, deps `requirements.txt`. Do not add a Procfile or second runner.

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
