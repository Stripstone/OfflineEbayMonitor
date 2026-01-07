# silver_math.py
"""
SILVER MATH Ã¢â‚¬" melt/payout/recommended-max calculations

This module contains ONLY deterministic math & parsing helpers.
No file I/O. No email. No HTML parsing. No classification.

Sprint 05.5 scope: Basic melt calculation engine
"""

from __future__ import annotations

import re
from typing import Any

import config


# Coin silver weights (ASW) used in this project
ASW_HALF_DOLLAR = 0.36169
ASW_SILVER_DOLLAR = 0.77344


def extract_quantity_from_title(title: str) -> int:
    """
    Extract quantity from listing title.
    
    Returns 1 if no clear quantity pattern detected (conservative).
    """
    if not title:
        return 1
    
    t = title.lower()
    
    # Patterns for quantity detection
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


def detect_oz_per_coin_from_title(title: str) -> float:
    """
    Detect per-coin ASW based on listing title.
    
    Returns:
        - 0.77344 for dollars (Morgan, Peace, Seated Dollar)
        - 0.36169 for half dollars (Kennedy, Franklin, Walking Liberty, Barber Half, Seated Half)
        - Default: 0.36169 (conservative half dollar assumption)
    """
    if not title:
        return ASW_HALF_DOLLAR
    
    t = title.lower()
    
    # Explicit half-dollar markers
    half_tokens = ["half dollar", "half-dollar", "50c", "50Â¢", " 50 c", " 50c"]
    if any(tok in t for tok in half_tokens):
        return ASW_HALF_DOLLAR
    
    # Dollar markers / common dollar series
    dollar_tokens = ["$1", " dollar", "morgan", "peace"]
    if any(tok in t for tok in dollar_tokens):
        return ASW_SILVER_DOLLAR
    
    # Seated series without explicit denom: conservative half-dollar assumption
    if "seated" in t:
        return ASW_HALF_DOLLAR
    
    # Default to half dollar (conservative)
    return ASW_HALF_DOLLAR


def calc_silver(listing: Any) -> dict:
    """
    Calculate melt metrics for a listing.
    
    Args:
        listing: Parsed listing object with:
            - title: str
            - total_price: float (item_price + shipping)
            - shipping: float
    
    Returns:
        dict with keys:
            - quantity: int
            - oz_per_coin: float
            - total_oz: float
            - melt_value: float
            - melt_payout: float (melt Ã— pawn_pct)
            - profit: float (payout - total_price)
            - margin_pct: float (cost-basis: profit/cost Ã— 100)
            - rec_max_total: float (max total price for target margin)
            - rec_max_item: float (max item price, excluding shipping)
            - profit_at_rec_max: float
            - margin_at_rec_max: float
    
    Contract: v1.2 Section 3
    """
    title = getattr(listing, "title", "") or ""
    total_price = float(getattr(listing, "total_price", 0.0) or 0.0)
    shipping = float(getattr(listing, "ship_price", 0.0) or 0.0)
    
    # Extract quantity and oz per coin
    qty = extract_quantity_from_title(title)
    oz_per = detect_oz_per_coin_from_title(title)
    
    # Calculate silver content
    total_oz = float(qty) * float(oz_per)
    
    # Calculate melt value
    spot = float(config.SPOT_PRICE)
    melt_value = total_oz * spot
    
    # Calculate pawn payout (pawn_exit per Contract v1.2 Section 3)
    pawn_pct = float(config.PAWN_PAYOUT_PCT)
    melt_payout = melt_value * (pawn_pct / 100.0)
    
    # Calculate profit and margin (cost-basis)
    profit = melt_payout - total_price
    margin_pct = 0.0
    if total_price > 0:
        margin_pct = (profit / total_price) * 100.0
    
    # Calculate recommended max prices
    # Contract v1.2 Section 3, Formula #3
    min_margin_pct = float(config.MIN_MARGIN_PCT)
    m = max(0.0, min_margin_pct / 100.0)
    
    if m <= 0:
        rec_max_unit = melt_payout
    else:
        rec_max_unit = melt_payout / (1.0 + m)
    
    rec_max_total = round(rec_max_unit * float(qty), 2)
    rec_max_item = round(max(0.0, rec_max_total - shipping), 2)
    
    # Profit and margin at recommended max
    profit_at_rec_max = melt_payout - rec_max_total
    margin_at_rec_max = 0.0
    if rec_max_total > 0:
        margin_at_rec_max = (profit_at_rec_max / rec_max_total) * 100.0
    
    return {
        "quantity": qty,
        "oz_per_coin": round(oz_per, 5),
        "total_oz": round(total_oz, 2),
        "melt_value": round(melt_value, 2),
        "melt_payout": round(melt_payout, 2),
        "profit": round(profit, 2),
        "margin_pct": round(margin_pct, 1),
        "rec_max_total": rec_max_total,
        "rec_max_item": rec_max_item,
        "profit_at_rec_max": round(profit_at_rec_max, 2),
        "margin_at_rec_max": round(margin_at_rec_max, 1),
    }


#EndOfFile
