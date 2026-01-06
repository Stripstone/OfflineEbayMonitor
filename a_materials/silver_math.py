# silver_math.py
"""SILVER MATH — melt/payout/recommended-max calculations

This module contains ONLY deterministic math & parsing helpers.
No file I/O. No email. No HTML parsing.

Blueprint alignment:
- price = item_price + shipping (caller provides Listing.total_price)
- Recommended max values are ALWAYS melt-derived, even for numismatic HITs.
"""


from __future__ import annotations

import re
from typing import Optional, Tuple

import config
from model_types import Listing


# Coin silver weights (ASW) used in this project
ASW_HALF_DOLLAR = 0.36169
ASW_SILVER_DOLLAR = 0.77344
ASW_SILVER_EAGLE = 0.99


def extract_quantity_from_title(title: str) -> int:
    """Conservative quantity extraction from listing title."""
    if not title:
        return 1
    t = title.lower()

    patterns = [
        r"\blot\s+of\s+(\d{1,3})(?!\.)\b",
        r"\broll\s+of\s+(\d{1,3})(?!\.)\b",
        r"\b(\d{1,3})(?!\.)\s+coins?\b",
        r"\b(\d{1,3})(?!\.)\s+pieces?\b",
        r"\((\d{1,3})(?!\.)\)",
        r"\b(\d{1,3})(?!\.)\s*[xX]\b",
        r"\b[xX]\s*(\d{1,3})(?!\.)\b",
        r"\bqty[:\s]*(\d{1,3})(?!\.)\b",
        r"\b(\d{1,3})(?!\.)\s*pcs\b",
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            try:
                qty = int(m.group(1))
            except Exception:
                continue
            if 1 < qty <= 600:
                return qty
    return 1

def has_multi_coin_semantics(title: str) -> bool:
    """Heuristic: title suggests multi-coin / lot without explicit numeric qty."""
    t = (title or "").lower()
    semantic = [
        " lot", "lots", " group", "collection", " estate", " hoard",
        " mixed", " bundle", " set", " roll", " bag", " coins",
    ]
    return any(s.strip() in t for s in semantic)

def detect_oz_per_coin_from_title(title: str) -> float:
    """Detect per-coin ASW based on listing title (per-listing, not per-page)."""
    t = (title or "").lower()

    # Explicit half-dollar markers
    half_tokens = ["half dollar", "half-dollar", "50c", "50¢", " 50 c", " 50c"]
    if any(tok in t for tok in half_tokens):
        return ASW_HALF_DOLLAR

    # Eagles (~1 oz ASW)
    if "silver eagle" in t or "american eagle" in t:
        return ASW_SILVER_EAGLE

    # Dollar markers / common dollar series
    dollar_tokens = ["$1", "dollar", "morgan", "peace"]
    if any(tok in t for tok in dollar_tokens):
        return ASW_SILVER_DOLLAR

    # Seated series without explicit denom: conservative half-dollar assumption
    if "seated" in t:
        return ASW_HALF_DOLLAR

    return ASW_HALF_DOLLAR


def compute_melt_value(total_oz: float, spot_price: float) -> float:
    return float(total_oz) * float(spot_price)


def compute_payout(melt_value: float, payout_pct: float) -> float:
    return float(melt_value) * (float(payout_pct) / 100.0)


def compute_profit(payout: float, cost: float) -> float:
    return float(payout) - float(cost)


def compute_margin_pct(profit: float, cost: float) -> float:
    if cost <= 0:
        return 0.0
    return (float(profit) / float(cost)) * 100.0


def compute_recommended_max_total(melt_payout: float, min_margin_pct: float) -> float:
    """Recommended max total (incl ship) to achieve min margin on melt payout."""
    m = max(0.0, float(min_margin_pct) / 100.0)
    if m <= 0:
        return round(float(melt_payout), 2)
    return round(float(melt_payout) / (1.0 + m), 2)


def compute_recommended_max_item_only(rec_max_total: float, shipping: float) -> float:
    return round(max(0.0, float(rec_max_total) - float(shipping)), 2)


def enrich_listing_silver_fields(listing: Listing) -> Listing:
    """Populate listing.quantity and listing.oz_per_coin deterministically."""
    if not listing.quantity or listing.quantity < 1:
        listing.quantity = extract_quantity_from_title(listing.title)
    if not listing.oz_per_coin or listing.oz_per_coin <= 0:
        listing.oz_per_coin = detect_oz_per_coin_from_title(listing.title)
    return listing


def calc_silver(listing: Listing, *, spot_price: Optional[float] = None, payout_pct: Optional[float] = None, bid_offset: Optional[float] = None) -> dict:
    """Compute melt/payout/profit/margins for a listing."""
    enrich_listing_silver_fields(listing)

    spot = float(spot_price) if spot_price is not None else float(config.SPOT_PRICE)
    payout = float(payout_pct) if payout_pct is not None else float(config.PAWN_PAYOUT_PCT)
    offset = float(bid_offset) if bid_offset is not None else float(config.BID_OFFSET)

    qty = int(listing.quantity or 1)
    oz_per = float(listing.oz_per_coin)
    total_oz = qty * oz_per

    melt_value = compute_melt_value(total_oz, spot)
    melt_payout = compute_payout(melt_value, payout)

    cost = float(listing.total_price) + offset
    profit = compute_profit(melt_payout, cost)
    margin_pct = compute_margin_pct(profit, cost)

    rec_max_total = compute_recommended_max_total(melt_payout, float(config.MIN_MARGIN_PCT))
    rec_max_item = compute_recommended_max_item_only(rec_max_total, float(listing.shipping))

    profit_at_rec = melt_payout - rec_max_total
    margin_at_rec = compute_margin_pct(profit_at_rec, rec_max_total if rec_max_total > 0 else 0.0)

    return {
        "quantity": qty,
        "oz_per_coin": oz_per,
        "total_oz": total_oz,
        "melt_value": melt_value,
        "melt_payout": melt_payout,
        "effective_cost": cost,
        "profit": profit,
        "margin_pct": margin_pct,
        "rec_max_total": rec_max_total,
        "rec_max_item": rec_max_item,
        "profit_at_rec_max": profit_at_rec,
        "margin_at_rec_max": margin_at_rec,
    }


# Backwards-compat alias (older modules imported compute_silver_metrics)

def compute_silver_metrics(listing, *args, **kwargs):
    """Legacy name: delegate to calc_silver."""
    return calc_silver(listing)
