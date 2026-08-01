# Warframe MCP

FastMCP server for [Warframe.market](https://docs.warframe.market/docs/intro/), [WarframeStat.us](https://docs.warframestat.us/), and [Overframe.gg](https://overframe.gg/) builds.

Author: snakeplisken47

## Deploy (mcphosting / Horizon)

Point the host at this GitHub repo. That is all.

- Repo: https://github.com/Ma110w/WarframeSkill
- Branch: `main`
- Entrypoint object: `server.py` → `mcp`
- Dependencies: `requirements.txt`

Do not add a Procfile, start script, or second entrypoint file. Hosts auto-detect FastMCP and start `mcp` themselves.

### Remote URL (ChatGPT / Cursor)

Public endpoint: `https://warframeskill.mcphosting.app/mcp`

- **ChatGPT:** Settings → enable Developer Mode → add connector with that URL (Auth: None unless you add auth later).
- **Cursor:** either paste the same `url`, or bridge with:

```json
"warframe": {
  "command": "npx",
  "args": ["-y", "mcp-remote", "https://warframeskill.mcphosting.app/mcp", "--transport", "http-only"]
}
```
## Local

```bash
pip install -r requirements.txt
python server.py
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
