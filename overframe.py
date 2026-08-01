"""Overframe.gg client — builds API + static item/mod DBs.

Public JSON API (no Cloudflare): https://overframe.gg/api/v1/
Static DB chunks (no Cloudflare): https://static.overframe.gg/_next/static/chunks/db/*
Homepage HTML is Cloudflare-protected; webpack chunk hash is discovered from a
known entry (overridable via OVERFRAME_WEBPACK_URL).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any

import httpx

from clients import ApiError, RateLimiter

OF_API = "https://overframe.gg/api/v1"
OF_SITE = "https://overframe.gg"
OF_STATIC = "https://static.overframe.gg/_next/static/chunks"
OF_MEDIA = "https://media.overframe.gg/v2/256x"

# Current Next.js webpack runtime (update if DB chunk fetches start 404ing).
_DEFAULT_WEBPACK = f"{OF_STATIC}/webpack-980fcd93113fb90d.js"

_OF_MIN_INTERVAL = 0.35

# Categories shown by Overframe's arsenal / search box (exclude blueprints/resources).
_ARSENAL_CATEGORIES = frozenset(
    {
        "warframe",
        "weapon",
        "primary",
        "primary-rifle",
        "primary-shotgun",
        "primary-bow",
        "primary-sniper",
        "secondary",
        "melee",
        "thrown",
        "archwing",
        "archgun",
        "mech",
        "kitgun",
        "zaw",
        "tome",
        "speargun",
        "pet",
        "pet-kavat",
        "pet-kubrow",
        "pet-moa",
        "pet-hound",
        "pet-sentinel",
        "sentinel-weapon",
        "unique",
    }
)

_POLARITY_NAMES = {
    "AP_ATTACK": "Madurai",
    "AP_DEFENSE": "Vazarin",
    "AP_TACTIC": "Naramon",
    "AP_WARD": "Unairu",
    "AP_POWER": "Zenurik",
    "AP_PRECEPT": "Penjaga",
    "AP_UNIVERSAL": "Universal",
    "AP_UMBRA": "Umbra",
}


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[''`]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _media_url(texture: str | None) -> str | None:
    if not texture:
        return None
    path = texture if texture.endswith((".png", ".jpg", ".jpeg", ".webp")) else f"{texture}.png"
    return f"{OF_MEDIA}{path}.webp"


def _item_url(item_id: int, name: str) -> str:
    return f"{OF_SITE}/items/arsenal/{item_id}/{_slugify(name)}/"


def _build_url(path: str | None, build_id: int | None = None) -> str | None:
    if path:
        if path.startswith("http"):
            return path
        return f"{OF_SITE}{path}"
    if build_id is not None:
        return f"{OF_SITE}/build/{build_id}/"
    return None


def _extract_json_export(js: str) -> Any:
    marker = ".exports=JSON.parse('"
    start = js.find(marker)
    if start < 0:
        raise ApiError("overframe.gg", "Could not parse static DB chunk (JSON.parse marker missing)")
    start += len(marker)
    end = js.rfind("')}")
    if end < 0 or end <= start:
        raise ApiError("overframe.gg", "Could not parse static DB chunk (unterminated JSON string)")
    raw = js[start:end]
    try:
        decoded = raw.encode("utf-8").decode("unicode_escape")
        return json.loads(decoded)
    except Exception as exc:
        raise ApiError("overframe.gg", f"Failed to decode static DB JSON: {exc}") from exc


def _summarize_item(entry: dict[str, Any]) -> dict[str, Any]:
    cats = entry.get("categories") or []
    name = entry.get("name") or ""
    item_id = entry.get("id")
    texture = entry.get("texture_new") or entry.get("texture")
    return {
        "id": item_id,
        "name": name,
        "categories": cats,
        "path": entry.get("path"),
        "url": _item_url(int(item_id), name) if item_id and name else None,
        "icon_url": _media_url(texture),
    }


def _summarize_mod(entry: dict[str, Any] | None, mod_id: int | None) -> dict[str, Any] | None:
    if mod_id is None:
        return None
    if not entry:
        return {"id": mod_id, "name": None, "path": None}
    data = entry.get("data") or {}
    polarity_code = data.get("ArtifactPolarity")
    return {
        "id": entry.get("id", mod_id),
        "name": entry.get("name"),
        "path": entry.get("path"),
        "rarity": data.get("Rarity"),
        "polarity": _POLARITY_NAMES.get(polarity_code, polarity_code),
        "compatibility": data.get("ItemCompatibilityLocTag"),
        "is_exilus": bool(data.get("IsUtility")),
        "is_aura": bool(data.get("TargetMode") or data.get("TargetType")),
        "icon_url": _media_url(entry.get("texture_new") or entry.get("texture") or data.get("Icon")),
    }


class OverframeClient:
    def __init__(self) -> None:
        self._limiter = RateLimiter(_OF_MIN_INTERVAL)
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Accept": "application/json, text/javascript, */*",
                "User-Agent": "WarframeMCP/1.0 (snakeplisken47; overframe; mcphosting)",
            },
            follow_redirects=True,
        )
        self._webpack_url = os.environ.get("OVERFRAME_WEBPACK_URL", _DEFAULT_WEBPACK)
        self._db_urls: dict[str, str] | None = None
        self._items_by_id: dict[int, dict[str, Any]] | None = None
        self._mods_by_id: dict[int, dict[str, Any]] | None = None
        self._items_list: list[dict[str, Any]] | None = None
        self._db_loaded_at = 0.0
        self._db_ttl = 6 * 3600
        self._db_lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _api_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        await self._limiter.wait()
        url = path if path.startswith("http") else f"{OF_API}{path}"
        response = await self._client.get(url, params=params)
        if response.status_code >= 400:
            raise ApiError(
                "overframe.gg",
                f"{response.status_code}: {response.text[:300]}",
                response.status_code,
            )
        try:
            return response.json()
        except Exception as exc:
            raise ApiError(
                "overframe.gg",
                f"Non-JSON response for {path}",
                response.status_code,
            ) from exc

    async def _fetch_text(self, url: str) -> str:
        await self._limiter.wait()
        response = await self._client.get(url)
        if response.status_code >= 400:
            raise ApiError(
                "overframe.gg",
                f"{response.status_code} fetching {url}",
                response.status_code,
            )
        return response.text

    async def _resolve_db_urls(self, *, force: bool = False) -> dict[str, str]:
        if self._db_urls is not None and not force:
            return self._db_urls

        webpack_js = await self._fetch_text(self._webpack_url)
        names = dict(re.findall(r'(\d+):"(db/[^"]+)"', webpack_js))
        hashes = dict(re.findall(r'(\d+):"([a-f0-9]{16})"', webpack_js))
        urls: dict[str, str] = {}
        for mid, name in names.items():
            hsh = hashes.get(mid)
            if not hsh:
                continue
            urls[name] = f"{OF_STATIC}/{name}.{hsh}.js"
        if "db/items" not in urls or "db/mods" not in urls:
            raise ApiError(
                "overframe.gg",
                "Webpack map missing db/items or db/mods. Set OVERFRAME_WEBPACK_URL "
                "to the current /_next/static/chunks/webpack-*.js URL from overframe.gg.",
            )
        self._db_urls = urls
        return urls

    async def _ensure_dbs(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if (
            not force
            and self._items_by_id is not None
            and self._mods_by_id is not None
            and now - self._db_loaded_at < self._db_ttl
        ):
            return

        async with self._db_lock:
            now = time.monotonic()
            if (
                not force
                and self._items_by_id is not None
                and self._mods_by_id is not None
                and now - self._db_loaded_at < self._db_ttl
            ):
                return

            urls = await self._resolve_db_urls(force=force)
            items_js, mods_js = await asyncio.gather(
                self._fetch_text(urls["db/items"]),
                self._fetch_text(urls["db/mods"]),
            )
            items_raw = _extract_json_export(items_js)
            mods_raw = _extract_json_export(mods_js)
            if not isinstance(items_raw, dict) or not isinstance(mods_raw, dict):
                raise ApiError("overframe.gg", "Unexpected static DB shape")

            items_by_id: dict[int, dict[str, Any]] = {}
            items_list: list[dict[str, Any]] = []
            for entry in items_raw.values():
                if not isinstance(entry, dict) or entry.get("id") is None:
                    continue
                if not entry.get("name"):
                    continue
                items_by_id[int(entry["id"])] = entry
                items_list.append(entry)

            mods_by_id: dict[int, dict[str, Any]] = {}
            for entry in mods_raw.values():
                if not isinstance(entry, dict) or entry.get("id") is None:
                    continue
                mods_by_id[int(entry["id"])] = entry

            self._items_by_id = items_by_id
            self._items_list = items_list
            self._mods_by_id = mods_by_id
            self._db_loaded_at = time.monotonic()

    async def search_items(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Mirror Overframe's search box: match arsenal items by name."""
        await self._ensure_dbs()
        assert self._items_list is not None
        q = query.strip().lower()
        if not q:
            return []

        scored: list[tuple[int, bool, dict[str, Any]]] = []
        for entry in self._items_list:
            name = str(entry.get("name") or "")
            name_l = name.lower()
            cats = set(entry.get("categories") or [])
            arsenal = bool(cats & _ARSENAL_CATEGORIES)
            if q not in name_l and q not in str(entry.get("path") or "").lower():
                continue

            if name_l == q:
                score = 0
            elif name_l.startswith(q):
                score = 1
            elif f" {q}" in f" {name_l}":
                score = 2
            else:
                score = 3
            scored.append((score, arsenal, entry))

        # Prefer arsenal hits (warframes/weapons/pets) like the site search box.
        arsenal_hits = [row for row in scored if row[1]]
        pool = arsenal_hits if arsenal_hits else scored
        pool.sort(key=lambda row: (row[0], str(row[2].get("name") or "").lower()))
        return [_summarize_item(e) for _, _, e in pool[: max(1, min(limit, 50))]]

    async def get_item(self, item_id: int) -> dict[str, Any] | None:
        await self._ensure_dbs()
        assert self._items_by_id is not None
        entry = self._items_by_id.get(int(item_id))
        return _summarize_item(entry) if entry else None

    async def resolve_item_id(self, item: str | int) -> int:
        if isinstance(item, int) or (isinstance(item, str) and item.strip().isdigit()):
            return int(item)
        matches = await self.search_items(str(item), limit=1)
        if not matches:
            raise ApiError("overframe.gg", f"No Overframe item matched '{item}'")
        return int(matches[0]["id"])

    async def list_builds(
        self,
        *,
        item_id: int | None = None,
        item: str | int | None = None,
        title: str | None = None,
        ordering: str = "-score",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        resolved_id = item_id
        resolved_item = None
        if resolved_id is None and item is not None:
            resolved_id = await self.resolve_item_id(item)
        if resolved_id is not None:
            resolved_item = await self.get_item(resolved_id)

        params: dict[str, Any] = {
            "limit": max(1, min(int(limit), 50)),
            "offset": max(0, int(offset)),
            "ordering": ordering or "-score",
        }
        if resolved_id is not None:
            params["item_id"] = resolved_id
        if title:
            params["title"] = title.strip()

        data = await self._api_get("/builds/", params=params)
        results = []
        for row in data.get("results") or []:
            item_data = row.get("item_data") or {}
            results.append(
                {
                    "id": row.get("id"),
                    "title": row.get("title"),
                    "score": row.get("score"),
                    "formas": row.get("formas"),
                    "created": row.get("created"),
                    "updated": row.get("updated"),
                    "url": _build_url(row.get("url"), row.get("id")),
                    "author": (row.get("author") or {}).get("username"),
                    "author_url": _build_url((row.get("author") or {}).get("url")),
                    "item": {
                        "id": item_data.get("id"),
                        "locTag": item_data.get("locTag"),
                        "icon_url": _media_url(
                            item_data.get("texture_new") or item_data.get("texture")
                        ),
                    },
                }
            )
        return {
            "count": data.get("count"),
            "offset": params["offset"],
            "limit": params["limit"],
            "ordering": params["ordering"],
            "item": resolved_item,
            "title_filter": title,
            "results": results,
        }

    async def get_build(self, build_id: int, *, resolve_mods: bool = True) -> dict[str, Any]:
        data = await self._api_get(f"/builds/{int(build_id)}/")
        await self._ensure_dbs()
        mods_by_id = self._mods_by_id or {}
        slots_out = []
        for slot in data.get("slots") or []:
            mid = slot.get("mod")
            mod_entry = (
                mods_by_id.get(int(mid)) if mid is not None and resolve_mods else None
            )
            slots_out.append(
                {
                    "slot_id": slot.get("slot_id"),
                    "rank": slot.get("rank"),
                    "drain": slot.get("drain"),
                    "polarity": slot.get("polarity"),
                    "polarity_match": slot.get("polarity_match"),
                    "mod": _summarize_mod(
                        mod_entry, int(mid) if mid is not None else None
                    )
                    if mid is not None
                    else None,
                }
            )

        item_data = data.get("item_data") or {}
        item_id = data.get("item") or item_data.get("id")
        item_summary = await self.get_item(int(item_id)) if item_id is not None else None

        children = []
        for child in data.get("child_builds") or []:
            children.append(
                {
                    "id": child.get("id"),
                    "title": child.get("title"),
                    "url": _build_url(child.get("url"), child.get("id")),
                    "item_id": (child.get("item_data") or {}).get("id") or child.get("item"),
                }
            )

        return {
            "id": data.get("id"),
            "title": data.get("title"),
            "description": data.get("description"),
            "score": data.get("score"),
            "formas": data.get("formas"),
            "mastery_rank": data.get("mastery_rank"),
            "item_rank": data.get("item_rank"),
            "endo_cost": data.get("endo_cost"),
            "platinum_cost": data.get("platinum_cost"),
            "comment_count": data.get("comment_count"),
            "created": data.get("created"),
            "updated": data.get("updated"),
            "url": _build_url(data.get("url"), data.get("id")),
            "author": (data.get("author") or {}).get("username"),
            "author_url": _build_url((data.get("author") or {}).get("url")),
            "item": item_summary
            or {
                "id": item_id,
                "locTag": item_data.get("locTag"),
                "icon_url": _media_url(item_data.get("texture_new") or item_data.get("texture")),
            },
            "slots": slots_out,
            "mods": [s["mod"] for s in slots_out if s.get("mod") and s["mod"].get("name")],
            "child_builds": children,
            "stats": data.get("stats"),
            "guide_url": data.get("url"),
        }

    async def top_mods(self, item: str | int, *, limit: int = 20) -> dict[str, Any]:
        item_id = await self.resolve_item_id(item)
        await self._ensure_dbs()
        assert self._mods_by_id is not None
        data = await self._api_get(
            f"/topmods/{item_id}/",
            params={"limit": max(1, min(int(limit), 50))},
        )
        # Index mods by path for resolution
        by_path = {
            str(m.get("path")): m
            for m in self._mods_by_id.values()
            if isinstance(m, dict) and m.get("path")
        }
        results = []
        for row in data.get("results") or []:
            path = row.get("path")
            entry = by_path.get(path) if path else None
            results.append(
                {
                    "path": path,
                    "count": row.get("count"),
                    "mod": _summarize_mod(entry, entry.get("id") if entry else None),
                }
            )
        return {
            "item": await self.get_item(item_id),
            "count": data.get("count"),
            "results": results,
        }


of = OverframeClient()
