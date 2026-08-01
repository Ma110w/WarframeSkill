"""HTTP clients for Warframe.market v2 and WarframeStat.us."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

WFM_BASE = "https://api.warframe.market/v2"
WFM_ASSETS = "https://warframe.market/static/assets"
WS_BASE = "https://api.warframestat.us"

WFM_PLATFORMS = ("pc", "ps4", "xbox", "switch", "mobile")
WS_PLATFORMS = ("pc", "ps4", "psn", "xb1", "swi", "ns")
WFM_LANGUAGES = (
    "en",
    "ko",
    "ru",
    "de",
    "fr",
    "pt",
    "zh-hans",
    "zh-hant",
    "es",
    "it",
    "pl",
    "uk",
    "tr",
    "ja",
)

# Warframe.market public limit: 3 requests/second
_WFM_MIN_INTERVAL = 0.34


class ApiError(Exception):
    def __init__(self, source: str, message: str, status: int | None = None):
        self.source = source
        self.status = status
        super().__init__(f"[{source}] {message}")


class RateLimiter:
    def __init__(self, min_interval: float):
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delay = self._min_interval - (now - self._last)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last = time.monotonic()


def normalize_slug(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("'", "")
        .replace(":", "")
    )


def asset_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{WFM_ASSETS}/{path.lstrip('/')}"


class WarframeMarketClient:
    def __init__(self) -> None:
        self._limiter = RateLimiter(_WFM_MIN_INTERVAL)
        self._items_cache: list[dict[str, Any]] | None = None
        self._items_cached_at = 0.0
        self._client = httpx.AsyncClient(
            base_url=WFM_BASE,
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "User-Agent": "WarframeMCP/1.0 (snakeplisken47; mcphosting)",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        path: str,
        *,
        platform: str = "pc",
        language: str = "en",
        crossplay: bool = False,
        params: dict[str, Any] | None = None,
    ) -> Any:
        await self._limiter.wait()
        headers = {
            "Platform": platform,
            "Language": language,
            "Crossplay": "true" if crossplay else "false",
        }
        response = await self._client.get(path, headers=headers, params=params)
        try:
            payload = response.json()
        except Exception as exc:
            raise ApiError(
                "warframe.market",
                f"Non-JSON response ({response.status_code}) for {path}",
                response.status_code,
            ) from exc

        if response.status_code >= 400:
            err = payload.get("error") if isinstance(payload, dict) else None
            raise ApiError(
                "warframe.market",
                f"{response.status_code}: {err or payload}",
                response.status_code,
            )

        if isinstance(payload, dict) and payload.get("error"):
            raise ApiError("warframe.market", str(payload["error"]))

        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    async def list_items(
        self, *, platform: str = "pc", language: str = "en", force: bool = False
    ) -> list[dict[str, Any]]:
        now = time.monotonic()
        if (
            not force
            and self._items_cache is not None
            and now - self._items_cached_at < 3600
        ):
            return self._items_cache

        data = await self._request("/items", platform=platform, language=language)
        items = data if isinstance(data, list) else []
        self._items_cache = items
        self._items_cached_at = now
        return items

    async def search_items(
        self,
        query: str,
        *,
        platform: str = "pc",
        language: str = "en",
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        items = await self.list_items(platform=platform, language=language)
        q = query.strip().lower()
        slug_q = normalize_slug(query)
        matches: list[dict[str, Any]] = []

        for item in items:
            slug = str(item.get("slug", ""))
            i18n = item.get("i18n") or {}
            name = ""
            if isinstance(i18n, dict):
                lang_block = i18n.get(language) or i18n.get("en") or {}
                if isinstance(lang_block, dict):
                    name = str(lang_block.get("name", ""))

            hay = f"{slug} {name}".lower()
            if q in hay or slug_q in slug:
                enriched = dict(item)
                enriched["name"] = name or slug
                thumb = None
                if isinstance(i18n, dict):
                    lang_block = i18n.get(language) or i18n.get("en") or {}
                    if isinstance(lang_block, dict):
                        thumb = asset_url(lang_block.get("thumb") or lang_block.get("icon"))
                enriched["thumb_url"] = thumb
                matches.append(enriched)
                if len(matches) >= limit:
                    break

        return matches

    async def get_item(
        self, slug: str, *, platform: str = "pc", language: str = "en"
    ) -> dict[str, Any]:
        data = await self._request(
            f"/items/{normalize_slug(slug)}", platform=platform, language=language
        )
        if isinstance(data, dict):
            i18n = data.get("i18n") or {}
            if isinstance(i18n, dict):
                lang_block = i18n.get(language) or i18n.get("en") or {}
                if isinstance(lang_block, dict):
                    data = dict(data)
                    data["name"] = lang_block.get("name")
                    data["icon_url"] = asset_url(lang_block.get("icon"))
                    data["thumb_url"] = asset_url(lang_block.get("thumb"))
                    data["wiki_link"] = lang_block.get("wikiLink")
        return data

    async def get_orders(
        self,
        slug: str,
        *,
        platform: str = "pc",
        language: str = "en",
        crossplay: bool = False,
        order_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        data = await self._request(
            f"/orders/item/{normalize_slug(slug)}",
            platform=platform,
            language=language,
            crossplay=crossplay,
        )
        orders = data if isinstance(data, list) else []
        if order_type:
            ot = order_type.lower()
            orders = [o for o in orders if str(o.get("type", "")).lower() == ot]
        if status:
            st = status.lower()
            orders = [
                o
                for o in orders
                if str((o.get("user") or {}).get("status", "")).lower() == st
            ]
        return orders[: max(1, min(limit, 200))]

    async def get_top_orders(
        self,
        slug: str,
        *,
        platform: str = "pc",
        language: str = "en",
        crossplay: bool = False,
        rank: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if rank is not None:
            params["rank"] = rank
        data = await self._request(
            f"/orders/item/{normalize_slug(slug)}/top",
            platform=platform,
            language=language,
            crossplay=crossplay,
            params=params or None,
        )
        return data if isinstance(data, dict) else {"raw": data}


class WarframeStatClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=WS_BASE,
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "User-Agent": "WarframeMCP/1.0 (snakeplisken47; mcphosting)",
            },
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = await self._client.get(path, params=params)
        if response.status_code >= 400:
            raise ApiError(
                "warframestat.us",
                f"{response.status_code}: {response.text[:300]}",
                response.status_code,
            )
        try:
            return response.json()
        except Exception as exc:
            raise ApiError(
                "warframestat.us",
                f"Non-JSON response for {path}",
                response.status_code,
            ) from exc

    async def heartbeat(self) -> Any:
        return await self._get("/heartbeat")

    async def worldstate(self, platform: str = "pc", language: str | None = None) -> Any:
        params = {"language": language} if language else None
        return await self._get(f"/{platform}", params=params)

    async def worldstate_field(
        self, field: str, platform: str = "pc", language: str | None = None
    ) -> Any:
        params = {"language": language} if language else None
        return await self._get(f"/{platform}/{field}", params=params)

    async def search_items(self, query: str, language: str | None = None) -> Any:
        params = {"language": language} if language else None
        return await self._get(f"/items/search/{query}", params=params)

    async def get_item(self, item: str, language: str | None = None) -> Any:
        params = {"language": language} if language else None
        return await self._get(f"/items/{item}", params=params)

    async def search_drops(self, query: str) -> Any:
        return await self._get(f"/drops/search/{query}")

    async def pricecheck(self, item_type: str, query: str) -> Any:
        return await self._get(f"/pricecheck/{item_type}/{query}")


wfm = WarframeMarketClient()
ws = WarframeStatClient()
