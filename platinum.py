"""Warframe Platinum pack pricing + Ontario/Canada tax calculator.

Pack CAD/USD list prices sourced from the WARFRAME Wiki Platinum page
(https://wiki.warframe.com/w/Platinum), which tracks Steam/regional store prices.

Steam/Canadian sales tax is additive at checkout (not included in the list price).
Ontario default: 13% HST.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

# Wiki / store list prices (pre-tax for CAD on Steam).
# Footnotes from wiki:
#   [1] 4600 not available on PlayStation
#   [2] 3450 not available on PC (console / some platform stores only)
_PACKS: list[dict[str, Any]] = [
    {
        "platinum": 4600,
        "usd": 199.99,
        "cad": 206.49,
        "platforms": ("pc", "xbox"),
        "notes": "Not available on PlayStation",
    },
    {
        "platinum": 3450,
        "usd": 149.99,
        "cad": 149.99,  # Xbox CA store listing; wiki marks CAD N/A for PC/Steam
        "platforms": ("xbox",),
        "notes": "Not available on PC/Steam; CAD from Xbox store listing",
    },
    {
        "platinum": 2200,
        "usd": 99.99,
        "cad": 103.49,
        "platforms": ("pc", "xbox", "playstation"),
        "notes": None,
    },
    {
        "platinum": 1025,
        "usd": 49.99,
        "cad": 51.99,
        "platforms": ("pc", "xbox", "playstation"),
        "notes": None,
    },
    {
        "platinum": 380,
        "usd": 19.99,
        "cad": 21.99,
        "platforms": ("pc", "xbox", "playstation"),
        "notes": None,
    },
    {
        "platinum": 175,
        "usd": 9.99,
        "cad": 10.49,
        "platforms": ("pc", "xbox", "playstation"),
        "notes": None,
    },
    {
        "platinum": 75,
        "usd": 4.99,
        "cad": 5.49,
        "platforms": ("pc", "xbox", "playstation"),
        "notes": None,
    },
]

Platform = Literal["pc", "xbox", "playstation"]

# Canadian sales-tax presets applied on top of list price (Steam-style additive).
_PROVINCE_TAX: dict[str, dict[str, Any]] = {
    "ON": {"rate": 0.13, "name": "HST", "label": "Ontario HST 13%"},
    "NB": {"rate": 0.15, "name": "HST", "label": "New Brunswick HST 15%"},
    "NL": {"rate": 0.15, "name": "HST", "label": "Newfoundland and Labrador HST 15%"},
    "PE": {"rate": 0.15, "name": "HST", "label": "Prince Edward Island HST 15%"},
    "NS": {"rate": 0.14, "name": "HST", "label": "Nova Scotia HST 14%"},
    "AB": {"rate": 0.05, "name": "GST", "label": "Alberta GST 5%"},
    "BC": {"rate": 0.05, "name": "GST", "label": "British Columbia GST 5% (PST usually N/A on Steam digital)"},
    "MB": {"rate": 0.05, "name": "GST", "label": "Manitoba GST 5%"},
    "SK": {"rate": 0.05, "name": "GST", "label": "Saskatchewan GST 5%"},
    "NT": {"rate": 0.05, "name": "GST", "label": "Northwest Territories GST 5%"},
    "NU": {"rate": 0.05, "name": "GST", "label": "Nunavut GST 5%"},
    "YT": {"rate": 0.05, "name": "GST", "label": "Yukon GST 5%"},
    # QST is separate; Steam historically collects GST+QST — approximate combined.
    "QC": {"rate": 0.14975, "name": "GST+QST", "label": "Quebec GST 5% + QST 9.975% (approx)"},
}


def _money(value: float) -> float:
    return round(value + 1e-9, 2)


def _rate(value: float) -> float:
    """CAD-per-platinum style rates (more precision than currency)."""
    return round(value + 1e-12, 4)


def _resolve_tax(
    *,
    province: str = "ON",
    tax_rate: float | None = None,
) -> dict[str, Any]:
    if tax_rate is not None:
        rate = float(tax_rate)
        if rate < 0 or rate > 1:
            raise ValueError("tax_rate must be between 0 and 1 (e.g. 0.13 for 13%)")
        return {
            "province": province.upper() if province else None,
            "rate": rate,
            "name": "custom",
            "label": f"Custom tax {rate * 100:.3g}%",
        }
    code = (province or "ON").strip().upper()
    info = _PROVINCE_TAX.get(code)
    if not info:
        known = ", ".join(sorted(_PROVINCE_TAX))
        raise ValueError(f"Unknown province '{province}'. Use one of: {known}")
    return {"province": code, **info}


def list_packs(platform: Platform = "pc") -> list[dict[str, Any]]:
    plat = platform.lower().strip()  # type: ignore[assignment]
    if plat not in ("pc", "xbox", "playstation"):
        raise ValueError("platform must be pc, xbox, or playstation")
    out = []
    for pack in _PACKS:
        if plat not in pack["platforms"]:
            continue
        cad = float(pack["cad"])
        plat_amt = int(pack["platinum"])
        out.append(
            {
                "platinum": plat_amt,
                "price_cad": cad,
                "price_usd": float(pack["usd"]),
                "cad_per_platinum": _rate(cad / plat_amt),
                "platforms": list(pack["platforms"]),
                "notes": pack["notes"],
            }
        )
    return out


def _apply_coupon(price: float, coupon_percent: float) -> float:
    pct = max(0.0, min(float(coupon_percent), 100.0))
    return price * (1.0 - pct / 100.0)


def price_pack(
    platinum: int,
    *,
    platform: Platform = "pc",
    province: str = "ON",
    tax_rate: float | None = None,
    coupon_percent: float = 0.0,
) -> dict[str, Any]:
    packs = {p["platinum"]: p for p in list_packs(platform)}
    if platinum not in packs:
        available = sorted(packs)
        raise ValueError(f"No {platform} pack for {platinum} platinum. Available: {available}")
    pack = packs[platinum]
    tax = _resolve_tax(province=province, tax_rate=tax_rate)
    base = _apply_coupon(float(pack["price_cad"]), coupon_percent)
    tax_amount = _money(base * tax["rate"])
    total = _money(base + tax_amount)
    return {
        "platinum": platinum,
        "platform": platform,
        "list_price_cad": pack["price_cad"],
        "coupon_percent": coupon_percent,
        "price_after_coupon_cad": _money(base),
        "tax": tax,
        "tax_cad": tax_amount,
        "total_cad": total,
        "cad_per_platinum": _rate(total / platinum),
        "source": "https://wiki.warframe.com/w/Platinum",
    }


@dataclass
class _Combo:
    cost: float
    platinum: int
    counts: dict[int, int]


def recommend_packs(
    target_platinum: int,
    *,
    platform: Platform = "pc",
    province: str = "ON",
    tax_rate: float | None = None,
    coupon_percent: float = 0.0,
    allow_overshoot: bool = True,
) -> dict[str, Any]:
    """Find the cheapest pack combination that covers target_platinum (CAD + tax)."""
    target = int(target_platinum)
    if target <= 0:
        raise ValueError("target_platinum must be > 0")
    if target > 500_000:
        raise ValueError("target_platinum too large (max 500000)")

    tax = _resolve_tax(province=province, tax_rate=tax_rate)
    packs = list_packs(platform)
    if not packs:
        raise ValueError(f"No packs available for platform '{platform}'")

    # Work in pre-tax CAD cents after coupon for exact DP.
    units: list[tuple[int, int]] = []  # (platinum, cost_cents)
    for p in packs:
        base = _apply_coupon(float(p["price_cad"]), coupon_percent)
        cents = int(round(base * 100))
        units.append((int(p["platinum"]), cents))

    max_pack = max(u[0] for u in units)
    # Cap DP range: enough room to overshoot by one largest pack.
    limit = target if not allow_overshoot else target + max_pack

    # dp[p] = (min_cost_cents, prev_plat, pack_plat) for exactly p platinum
    INF = 10**18
    dp_cost = [INF] * (limit + 1)
    dp_prev = [-1] * (limit + 1)
    dp_pack = [-1] * (limit + 1)
    dp_cost[0] = 0

    for p in range(limit + 1):
        if dp_cost[p] == INF:
            continue
        for plat_amt, cost_cents in units:
            nxt = p + plat_amt
            if nxt > limit:
                continue
            new_cost = dp_cost[p] + cost_cents
            if new_cost < dp_cost[nxt]:
                dp_cost[nxt] = new_cost
                dp_prev[nxt] = p
                dp_pack[nxt] = plat_amt

    best_plat = -1
    best_cost = INF
    start = target if allow_overshoot else target
    end = limit if allow_overshoot else target
    for p in range(start, end + 1):
        if not allow_overshoot and p != target:
            continue
        if dp_cost[p] < best_cost or (dp_cost[p] == best_cost and p < best_plat):
            best_cost = dp_cost[p]
            best_plat = p

    if best_plat < 0 or best_cost == INF:
        raise ValueError(
            f"Could not reach {target} platinum with available {platform} packs"
            + ("" if allow_overshoot else " exactly (try allow_overshoot=true)")
        )

    counts: dict[int, int] = {}
    cur = best_plat
    while cur > 0:
        pack_amt = dp_pack[cur]
        counts[pack_amt] = counts.get(pack_amt, 0) + 1
        cur = dp_prev[cur]

    purchases = []
    subtotal = 0.0
    for pack in packs:
        amt = int(pack["platinum"])
        n = counts.get(amt, 0)
        if not n:
            continue
        unit_base = _apply_coupon(float(pack["price_cad"]), coupon_percent)
        line_base = unit_base * n
        line_tax = line_base * tax["rate"]
        line_total = line_base + line_tax
        subtotal += line_base
        purchases.append(
            {
                "pack_platinum": amt,
                "quantity": n,
                "unit_list_cad": pack["price_cad"],
                "unit_after_coupon_cad": _money(unit_base),
                "line_subtotal_cad": _money(line_base),
                "line_tax_cad": _money(line_tax),
                "line_total_cad": _money(line_total),
                "platinum_total": amt * n,
            }
        )

    purchases.sort(key=lambda row: (-row["pack_platinum"],))
    tax_cad = _money(subtotal * tax["rate"])
    total_cad = _money(subtotal + tax_cad)
    efficiency = sorted(
        (
            {
                "platinum": p["platinum"],
                "list_cad": p["price_cad"],
                "cad_per_platinum_pre_tax": p["cad_per_platinum"],
                "cad_per_platinum_with_tax": _rate(
                    (_apply_coupon(p["price_cad"], coupon_percent) * (1 + tax["rate"]))
                    / p["platinum"]
                ),
            }
            for p in packs
        ),
        key=lambda row: row["cad_per_platinum_with_tax"],
    )

    return {
        "target_platinum": target,
        "platinum_purchased": best_plat,
        "platinum_extra": best_plat - target,
        "platform": platform,
        "coupon_percent": coupon_percent,
        "tax": tax,
        "subtotal_cad": _money(subtotal),
        "tax_cad": tax_cad,
        "total_cad": total_cad,
        "cad_per_platinum_effective": _rate(total_cad / best_plat),
        "purchases": purchases,
        "purchase_summary": " + ".join(
            f"{row['quantity']}×{row['pack_platinum']}" for row in purchases
        ),
        "pack_efficiency_best_to_worst": efficiency,
        "notes": [
            "CAD list prices from WARFRAME Wiki Platinum table (Steam/regional).",
            "Tax is additive at checkout (Steam Canada / digital HST-GST style).",
            "Default province ON = Ontario 13% HST.",
            "In-game % coupons reduce the pack price before tax.",
            "Prime Access / bundled discounts are not modeled.",
        ],
        "source": "https://wiki.warframe.com/w/Platinum",
    }


def convert_plat_value(
    platinum: int,
    *,
    platform: Platform = "pc",
    province: str = "ON",
    tax_rate: float | None = None,
    coupon_percent: float = 0.0,
) -> dict[str, Any]:
    """Estimate CAD value of N platinum using best available pack efficiency + tax."""
    rec = recommend_packs(
        platinum,
        platform=platform,
        province=province,
        tax_rate=tax_rate,
        coupon_percent=coupon_percent,
        allow_overshoot=True,
    )
    packs = list_packs(platform)
    best = min(packs, key=lambda p: p["cad_per_platinum"])
    tax = _resolve_tax(province=province, tax_rate=tax_rate)
    best_unit = _apply_coupon(best["price_cad"], coupon_percent) * (1 + tax["rate"])
    marginal = best_unit / best["platinum"]
    return {
        "platinum": platinum,
        "estimated_total_cad_buy_packs": rec["total_cad"],
        "packs_to_buy": rec["purchases"],
        "purchase_summary": rec["purchase_summary"],
        "platinum_purchased": rec["platinum_purchased"],
        "tax": tax,
        "best_pack_efficiency": {
            "pack_platinum": best["platinum"],
            "cad_per_platinum_with_tax": _rate(marginal),
        },
        "naive_value_at_best_rate_cad": _money(platinum * marginal),
        "source": "https://wiki.warframe.com/w/Platinum",
    }
