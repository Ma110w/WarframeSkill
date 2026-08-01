"""Warframe MCP server — Warframe.market v2 + WarframeStat.us + Overframe.gg.

Platform entrypoint object: `mcp` (file: server.py).
Docs:
  - https://docs.warframe.market/docs/intro/
  - https://docs.warframestat.us/
  - https://overframe.gg/
"""

from __future__ import annotations

import json
from typing import Any, Literal

from fastmcp import FastMCP

from clients import (
    WFM_LANGUAGES,
    WFM_PLATFORMS,
    WS_PLATFORMS,
    ApiError,
    normalize_slug,
    wfm,
    ws,
)
from overframe import of

mcp = FastMCP(
    name="Warframe",
    instructions=(
        "Query live Warframe marketplace prices (warframe.market v2), "
        "worldstate / item / drop data (warframestat.us), and Overframe.gg builds. "
        "Prefer market slugs like 'nikana_prime_blueprint'. "
        "Use wfm_search_items when the slug is unknown. "
        "For community builds: of_search_items (search box) → of_list_builds → "
        "of_get_build (includes resolved mods). "
        "Default platforms: market=pc, worldstate=pc."
    ),
)


@mcp.tool
def ping() -> str:
    """Health check — returns ok if the Warframe MCP server is running."""
    return "ok"

WorldstateField = Literal[
    "alerts",
    "arbitration",
    "archimedeas",
    "archonHunt",
    "buildLabel",
    "calendar",
    "cambionCycle",
    "cetusCycle",
    "conclaveChallenges",
    "constructionProgress",
    "dailyDeals",
    "duviriCycle",
    "earthCycle",
    "events",
    "fissures",
    "flashSales",
    "globalUpgrades",
    "invasions",
    "kuva",
    "news",
    "nightwave",
    "persistentEnemies",
    "sentientOutposts",
    "simaris",
    "sortie",
    "steelPath",
    "syndicateMissions",
    "timestamp",
    "vallisCycle",
    "vaultTrader",
    "voidTrader",
    "voidTraders",
    "weeklyChallenges",
    "zarimanCycle",
]


def _ok(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _err(exc: Exception) -> str:
    if isinstance(exc, ApiError):
        return _ok({"error": True, "source": exc.source, "message": str(exc), "status": exc.status})
    return _ok({"error": True, "message": str(exc)})


def _check_wfm_platform(platform: str) -> str:
    p = platform.lower().strip()
    if p not in WFM_PLATFORMS:
        raise ApiError(
            "warframe.market",
            f"Invalid platform '{platform}'. Use one of: {', '.join(WFM_PLATFORMS)}",
        )
    return p


def _check_ws_platform(platform: str) -> str:
    p = platform.lower().strip()
    if p not in WS_PLATFORMS:
        raise ApiError(
            "warframestat.us",
            f"Invalid platform '{platform}'. Use one of: {', '.join(WS_PLATFORMS)}",
        )
    return p


def _check_language(language: str) -> str:
    lang = language.lower().strip()
    if lang not in WFM_LANGUAGES:
        raise ApiError(
            "warframe.market",
            f"Invalid language '{language}'. Use one of: {', '.join(WFM_LANGUAGES)}",
        )
    return lang


# ---------------------------------------------------------------------------
# Warframe.market tools
# ---------------------------------------------------------------------------


@mcp.tool
async def wfm_search_items(
    query: str,
    platform: str = "pc",
    language: str = "en",
    limit: int = 25,
) -> str:
    """Search tradable items on warframe.market by name or slug.

    Returns matching slugs/names for use with other wfm_* tools.
    Example query: "nikana prime", "primed continuity", "axi a1".
    """
    try:
        platform = _check_wfm_platform(platform)
        language = _check_language(language)
        limit = max(1, min(int(limit), 100))
        results = await wfm.search_items(
            query, platform=platform, language=language, limit=limit
        )
        return _ok(
            {
                "query": query,
                "count": len(results),
                "items": [
                    {
                        "slug": i.get("slug"),
                        "name": i.get("name"),
                        "tags": i.get("tags"),
                        "thumb_url": i.get("thumb_url"),
                    }
                    for i in results
                ],
            }
        )
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def wfm_get_item(
    slug: str,
    platform: str = "pc",
    language: str = "en",
) -> str:
    """Get detailed warframe.market item info by slug.

    Slug example: nikana_prime_blueprint. Spaces are normalized to underscores.
    """
    try:
        platform = _check_wfm_platform(platform)
        language = _check_language(language)
        data = await wfm.get_item(slug, platform=platform, language=language)
        return _ok(data)
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def wfm_get_top_orders(
    slug: str,
    platform: str = "pc",
    language: str = "en",
    crossplay: bool = False,
    rank: int | None = None,
) -> str:
    """Get top buy/sell orders for an item on warframe.market.

    Best for quick price checks. Optional rank filters mod/arcane ranks.
    Slug example: primed_continuity
    """
    try:
        platform = _check_wfm_platform(platform)
        language = _check_language(language)
        data = await wfm.get_top_orders(
            slug,
            platform=platform,
            language=language,
            crossplay=crossplay,
            rank=rank,
        )
        return _ok({"slug": normalize_slug(slug), "top": data})
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def wfm_get_orders(
    slug: str,
    platform: str = "pc",
    language: str = "en",
    crossplay: bool = False,
    order_type: str | None = None,
    status: str | None = None,
    limit: int = 40,
) -> str:
    """List warframe.market orders for an item.

    order_type: 'sell' or 'buy' (optional).
    status: seller status filter — 'ingame', 'online', or 'offline' (optional).
    """
    try:
        platform = _check_wfm_platform(platform)
        language = _check_language(language)
        if order_type and order_type.lower() not in {"sell", "buy"}:
            raise ApiError("warframe.market", "order_type must be 'sell' or 'buy'")
        if status and status.lower() not in {"ingame", "online", "offline"}:
            raise ApiError(
                "warframe.market",
                "status must be 'ingame', 'online', or 'offline'",
            )
        orders = await wfm.get_orders(
            slug,
            platform=platform,
            language=language,
            crossplay=crossplay,
            order_type=order_type,
            status=status,
            limit=limit,
        )
        compact = [
            {
                "type": o.get("type"),
                "platinum": o.get("platinum"),
                "quantity": o.get("quantity"),
                "rank": o.get("rank"),
                "charges": o.get("charges"),
                "user": (o.get("user") or {}).get("ingameName"),
                "status": (o.get("user") or {}).get("status"),
                "reputation": (o.get("user") or {}).get("reputation"),
                "platform": (o.get("user") or {}).get("platform"),
            }
            for o in orders
        ]
        return _ok(
            {
                "slug": normalize_slug(slug),
                "count": len(compact),
                "orders": compact,
            }
        )
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def wfm_price_check(
    query: str,
    platform: str = "pc",
    language: str = "en",
    crossplay: bool = False,
    online_only: bool = True,
) -> str:
    """Search an item and return its top market prices in one step.

    Useful when you only have a human name like "Nikana Prime Blueprint".
    """
    try:
        platform = _check_wfm_platform(platform)
        language = _check_language(language)
        matches = await wfm.search_items(
            query, platform=platform, language=language, limit=5
        )
        if not matches:
            return _ok({"error": True, "message": f"No market items matched '{query}'"})

        best = matches[0]
        slug = str(best.get("slug"))
        top = await wfm.get_top_orders(
            slug, platform=platform, language=language, crossplay=crossplay
        )

        def summarize(side: str) -> list[dict[str, Any]]:
            rows = top.get(side) if isinstance(top, dict) else None
            if not isinstance(rows, list):
                return []
            out: list[dict[str, Any]] = []
            for o in rows:
                user = o.get("user") or {}
                st = str(user.get("status", "")).lower()
                if online_only and st not in {"ingame", "online"}:
                    continue
                out.append(
                    {
                        "platinum": o.get("platinum"),
                        "quantity": o.get("quantity"),
                        "rank": o.get("rank"),
                        "user": user.get("ingameName"),
                        "status": user.get("status"),
                    }
                )
            return out

        return _ok(
            {
                "query": query,
                "matched": {"slug": slug, "name": best.get("name"), "tags": best.get("tags")},
                "alternatives": [
                    {"slug": m.get("slug"), "name": m.get("name")} for m in matches[1:]
                ],
                "sell": summarize("sell"),
                "buy": summarize("buy"),
            }
        )
    except Exception as exc:
        return _err(exc)


# ---------------------------------------------------------------------------
# WarframeStat.us tools
# ---------------------------------------------------------------------------


@mcp.tool
async def ws_heartbeat() -> str:
    """Check that the WarframeStat.us API is healthy."""
    try:
        return _ok(await ws.heartbeat())
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_worldstate(
    platform: str = "pc",
    language: str | None = None,
) -> str:
    """Get the full live worldstate for a platform.

    Large payload — prefer ws_get_field / specialized tools when possible.
    Platforms: pc, ps4, psn, xb1, swi, ns.
    """
    try:
        platform = _check_ws_platform(platform)
        return _ok(await ws.worldstate(platform=platform, language=language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_field(
    field: WorldstateField,
    platform: str = "pc",
    language: str | None = None,
) -> str:
    """Get a single worldstate field (sortie, fissures, nightwave, voidTrader, etc.)."""
    try:
        platform = _check_ws_platform(platform)
        return _ok(
            await ws.worldstate_field(field, platform=platform, language=language)
        )
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_sortie(platform: str = "pc", language: str | None = None) -> str:
    """Get today's Sortie missions, boss, and modifiers."""
    try:
        platform = _check_ws_platform(platform)
        return _ok(await ws.worldstate_field("sortie", platform, language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_archon_hunt(platform: str = "pc", language: str | None = None) -> str:
    """Get the current Archon Hunt."""
    try:
        platform = _check_ws_platform(platform)
        return _ok(await ws.worldstate_field("archonHunt", platform, language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_fissures(
    platform: str = "pc",
    language: str | None = None,
    steel_path_only: bool = False,
    tier: str | None = None,
) -> str:
    """Get active Void Fissures.

    Set steel_path_only=true for Steel Path / hard fissures.
    Optional tier filter examples: Lith, Meso, Neo, Axi, Requiem, Omnia.
    """
    try:
        platform = _check_ws_platform(platform)
        data = await ws.worldstate_field("fissures", platform, language)
        fissures = data if isinstance(data, list) else []
        if steel_path_only:
            fissures = [f for f in fissures if f.get("isHard")]
        if tier:
            t = tier.strip().lower()
            fissures = [f for f in fissures if str(f.get("tier", "")).lower() == t]
        return _ok({"count": len(fissures), "fissures": fissures})
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_invasions(platform: str = "pc", language: str | None = None) -> str:
    """Get active invasions and their rewards."""
    try:
        platform = _check_ws_platform(platform)
        data = await ws.worldstate_field("invasions", platform, language)
        invasions = data if isinstance(data, list) else []
        active = [i for i in invasions if not i.get("completed")]
        return _ok({"count": len(active), "invasions": active})
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_nightwave(platform: str = "pc", language: str | None = None) -> str:
    """Get Nightwave season info and active challenges."""
    try:
        platform = _check_ws_platform(platform)
        return _ok(await ws.worldstate_field("nightwave", platform, language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_void_trader(platform: str = "pc", language: str | None = None) -> str:
    """Get Baro Ki'Teer (Void Trader) location, timer, and inventory."""
    try:
        platform = _check_ws_platform(platform)
        return _ok(await ws.worldstate_field("voidTrader", platform, language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_cycles(platform: str = "pc", language: str | None = None) -> str:
    """Get open-world / zone cycles: Cetus, Vallis, Cambion, Earth, Zariman, Duviri."""
    try:
        platform = _check_ws_platform(platform)
        fields = (
            "cetusCycle",
            "vallisCycle",
            "cambionCycle",
            "earthCycle",
            "zarimanCycle",
            "duviriCycle",
        )
        out: dict[str, Any] = {}
        for field in fields:
            out[field] = await ws.worldstate_field(field, platform, language)
        return _ok(out)
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_alerts(platform: str = "pc", language: str | None = None) -> str:
    """Get active alerts."""
    try:
        platform = _check_ws_platform(platform)
        return _ok(await ws.worldstate_field("alerts", platform, language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_arbitration(platform: str = "pc", language: str | None = None) -> str:
    """Get the current Arbitration mission."""
    try:
        platform = _check_ws_platform(platform)
        return _ok(await ws.worldstate_field("arbitration", platform, language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_steel_path(platform: str = "pc", language: str | None = None) -> str:
    """Get Steel Path rewards rotation and timers."""
    try:
        platform = _check_ws_platform(platform)
        return _ok(await ws.worldstate_field("steelPath", platform, language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_daily_deals(platform: str = "pc", language: str | None = None) -> str:
    """Get Darvo daily deals."""
    try:
        platform = _check_ws_platform(platform)
        return _ok(await ws.worldstate_field("dailyDeals", platform, language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_events(platform: str = "pc", language: str | None = None) -> str:
    """Get active world events / community events."""
    try:
        platform = _check_ws_platform(platform)
        return _ok(await ws.worldstate_field("events", platform, language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_search_items(query: str, language: str | None = None) -> str:
    """Search Warframe item data (stats, components, etc.) via warframestat.us."""
    try:
        data = await ws.search_items(query, language=language)
        if isinstance(data, list):
            compact = [
                {
                    "name": i.get("name"),
                    "uniqueName": i.get("uniqueName"),
                    "category": i.get("category") or i.get("productCategory"),
                    "type": i.get("type"),
                    "masteryReq": i.get("masteryReq"),
                    "wikiaUrl": i.get("wikiaUrl"),
                }
                for i in data[:40]
            ]
            return _ok({"query": query, "count": len(compact), "items": compact})
        return _ok(data)
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_get_item(item: str, language: str | None = None) -> str:
    """Get a specific item by name/uniqueName from warframestat.us item data."""
    try:
        return _ok(await ws.get_item(item, language=language))
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_search_drops(query: str) -> str:
    """Search drop locations/chances for an item (relics, missions, etc.)."""
    try:
        data = await ws.search_drops(query)
        if isinstance(data, list):
            return _ok({"query": query, "count": len(data), "drops": data[:100]})
        return _ok(data)
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def ws_pricecheck(item_type: str, query: str) -> str:
    """WarframeStat.us warframe.market price-check helper.

    item_type is typically a category key used by the API (e.g. relics, warframes).
    Prefer wfm_price_check for direct marketplace pricing.
    """
    try:
        return _ok(await ws.pricecheck(item_type, query))
    except Exception as exc:
        return _err(exc)


# ---------------------------------------------------------------------------
# Overframe.gg tools
# ---------------------------------------------------------------------------


@mcp.tool
async def of_search_items(query: str, limit: int = 20) -> str:
    """Search Overframe's item search box (warframes, weapons, companions, etc.).

    Returns Overframe item ids/names/urls. Use the id with of_list_builds.
    Example queries: "Mesa Prime", "Laetum", "Nataruk".
    """
    try:
        limit = max(1, min(int(limit), 50))
        results = await of.search_items(query, limit=limit)
        return _ok({"query": query, "count": len(results), "items": results})
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def of_list_builds(
    item: str | None = None,
    item_id: int | None = None,
    title: str | None = None,
    ordering: str = "-score",
    limit: int = 20,
    offset: int = 0,
) -> str:
    """List Overframe builds for an item (like the item builds page).

    Provide either item (name, e.g. "Mesa Prime") or item_id (from of_search_items).
    Optional title filters build titles (e.g. "steel path").
    ordering examples: "-score", "-updated", "created".
    """
    try:
        if item is None and item_id is None and not title:
            raise ApiError(
                "overframe.gg",
                "Provide item, item_id, and/or title to list builds.",
            )
        limit = max(1, min(int(limit), 50))
        offset = max(0, int(offset))
        data = await of.list_builds(
            item_id=item_id,
            item=item,
            title=title,
            ordering=ordering,
            limit=limit,
            offset=offset,
        )
        return _ok(data)
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def of_get_build(build_id: int, resolve_mods: bool = True) -> str:
    """Get a full Overframe build, including slot mods (names, ranks, drain).

    build_id comes from of_list_builds. When resolve_mods is true (default),
    numeric mod ids are resolved to names/polarities via Overframe's mod DB.
    """
    try:
        data = await of.get_build(int(build_id), resolve_mods=bool(resolve_mods))
        return _ok(data)
    except Exception as exc:
        return _err(exc)


@mcp.tool
async def of_top_mods(item: str, limit: int = 20) -> str:
    """Get the most-used mods on Overframe for an item.

    item may be a name ("Mesa Prime") or Overframe item id.
    """
    try:
        limit = max(1, min(int(limit), 50))
        return _ok(await of.top_mods(item, limit=limit))
    except Exception as exc:
        return _err(exc)


if __name__ == "__main__":
    # Local/stdio only. Hosts import `mcp` and ignore this block.
    mcp.run()

