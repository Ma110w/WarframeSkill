# Warframe MCP

FastMCP server for [Warframe.market](https://docs.warframe.market/docs/intro/) and [WarframeStat.us](https://docs.warframestat.us/).

Author: snakeplisken47

## Deploy (mcphosting / Horizon)

Point the host at this GitHub repo. That is all.

- Repo: https://github.com/Ma110w/WarframeSkill
- Branch: `main`
- Entrypoint object: `server.py` → `mcp`
- Dependencies: `requirements.txt`

Do not add a Procfile, start script, or second entrypoint file. Hosts auto-detect FastMCP and start `mcp` themselves.

## Local

```bash
pip install -r requirements.txt
python server.py
```

## Tools

`ping`, market tools (`wfm_*`), worldstate tools (`ws_*`).
