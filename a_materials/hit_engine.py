# hit_engine.py
"""
HIT ENGINE — SINGLE SOURCE OF TRUTH (ARCHITECTURE-ALIGNED)

Responsibilities:
- Evaluate listings
- Apply numismatic overrides (FMV via EMA or Static Default)
- Decide HIT vs Miss
- Expose ONE normalized silver_calc dict per listing

Invariant:
- e.silver_calc is ALWAYS a dict
- All profit logic remains MELT-based
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Any, Optional

import config
from numismatic_rules import check_numismatic_override
from numismatic_defaults import STATIC_NUMISMATIC_DEFAULTS
from price_store import get_ema_value_and_observers
from silver_math import calc_silver
from prospect_score import score_prospect


# -----------------------------
# Data container
# -----------------------------

@dataclass
class Evaluated:
    listing: Any
    silver_calc: dict
    is_hit: bool
    numismatic_override: Optional[str] = None
    # True when listing is a numismatic "prospect" worth alerting even if not a melt HIT.
    # (Dealer payout-based positive opportunity within the configured margin target.)
    is_prospect: bool = False


# -----------------------------
# Helpers
# -----------------------------

def _make_key(coin_type: str, year: int, mint: str) -> str:
    return f"{coin_type}|{year}|{mint}"


def _coinbook_url(coin_type: str) -> Optional[str]:
    """Build a CoinBook URL that matches the locked UX contract.

    CoinBook is organized by denomination. For this project we care about:
      - Dollars:      /coins/dollars/<type>/
      - Half Dollars: /coins/half-dollars/<type>/

    `coin_type` here is the *canonical* label returned by numismatic_rules,
    e.g. "Morgan Dollar", "Barber Half".
    """
    if not coin_type:
        return None

    # Canonical mappings (safe, explicit, and stable)
    mapping = {
        "Morgan Dollar": ("dollars", "morgan"),
        "Peace Dollar": ("dollars", "peace"),
        "Seated Liberty Dollar": ("dollars", "seated-liberty"),

        "Barber Half": ("half-dollars", "barber"),
        "Seated Liberty Half": ("half-dollars", "seated-liberty"),
        "Franklin Half": ("half-dollars", "franklin"),
        "Kennedy Half": ("half-dollars", "kennedy"),

        # Not currently a core UX requirement, but kept safe for future expansion.
        "Seated Liberty Quarter": ("quarters", "seated-liberty"),
    }

    denom, slug = mapping.get(str(coin_type), (None, None))
    if not denom or not slug:
        # Fallback: try to infer denomination from the label.
        ct = str(coin_type)
        ct_lower = ct.lower()
        if " half" in ct_lower:
            denom = "half-dollars"
        elif " dollar" in ct_lower:
            denom = "dollars"
        else:
            return None

        # Fallback slug: remove denomination words and normalize.
        slug = (
            ct_lower
            .replace(" dollar", "")
            .replace(" half", "")
            .strip()
            .replace(" ", "-")
        )
        if not slug:
            return None

    return f"https://www.usacoinbook.com/coins/{denom}/{slug}/"


def _resolve_fmv(coin_type: str, year: int, mint: str):
    """
    Returns:
      (fmv_floor, fmv_source_label)
    """
    key = _make_key(coin_type, year, mint)

    ema, observers = get_ema_value_and_observers(key)
    if ema is not None:
        # UX: keep compact; append observer total if available.
        if observers is not None:
            return float(ema), f"Offline EMA o.{int(observers)}"
        return float(ema), "Offline EMA"

    static = STATIC_NUMISMATIC_DEFAULTS.get(key)
    if static is not None:
        return float(static), "Static Default"

    return None, None


# -----------------------------
# Core evaluation
# -----------------------------

def evaluate_listings(
    listings: List[Any],
    *,
    max_time_hours: Optional[float] = None,
) -> List[Evaluated]:

    evaluated: List[Evaluated] = []

    for lst in listings:
        # --- Melt-based calculation (ALWAYS)
        silver = calc_silver(lst)

        # --- Numismatic override detection
        override = check_numismatic_override(lst.title)

        fmv_floor = None
        fmv_source = None
        dealer_value = None
        dealer_profit = None
        dealer_margin_pct = None
        coinbook_url = None

        # Dealer-based "prospect" recommendation fields (only meaningful when override resolves)
        dealer_rec_max_total = None
        dealer_rec_max_item = None
        dealer_profit_at_rec = None
        dealer_margin_at_rec = None

        if override:
            coin_type = override.coin_type
            year = override.year
            mint = override.mint

            fmv_floor, fmv_source = _resolve_fmv(coin_type, year, mint)

            if fmv_floor is not None:
                dealer_value = fmv_floor * (config.NUMISMATIC_PAYOUT_PCT / 100.0)
                dealer_profit = dealer_value - lst.total_price
                if lst.total_price > 0:
                    dealer_margin_pct = (dealer_profit / lst.total_price) * 100.0

                # Recommended max for numismatic prospects is anchored to dealer payout, not melt.
                # This matches the locked UX examples.
                m = max(0.0, float(config.MIN_MARGIN_PCT) / 100.0)
                dealer_rec_max_total = round(float(dealer_value) / (1.0 + m), 2) if dealer_value is not None else None
                dealer_rec_max_item = round(max(0.0, float(dealer_rec_max_total) - float(getattr(lst, "shipping", 0.0) or 0.0)), 2) if dealer_rec_max_total is not None else None
                dealer_profit_at_rec = round(float(dealer_value) - float(dealer_rec_max_total), 2) if (dealer_value is not None and dealer_rec_max_total is not None) else None
                dealer_margin_at_rec = ((dealer_profit_at_rec / dealer_rec_max_total) * 100.0) if (dealer_profit_at_rec is not None and dealer_rec_max_total) else None

            coinbook_url = _coinbook_url(coin_type)

        # --- HIT logic
        # Melt HIT: total price <= melt-derived recommended max total.
        rec_max_total = silver.get("rec_max_total")
        is_hit = bool(rec_max_total is not None and lst.total_price <= rec_max_total)

        
        # Numismatic PROS:
        # - Base (Cat-2): requires positive dealer-margin gate.
        # - Cat-3 override: premium/high-grade language priced like raw (<= EMA + tol)
        #   may become PROS even if dealer-margin fails. EMA remains untouched.
        is_prospect = False
        if dealer_value is not None and fmv_floor is not None and float(getattr(lst, "total_price", 0.0) or 0.0) > 0:
            total = float(lst.total_price)

            # Optional total cap for PROS (attention/capital throttle)
            pros_max_total = getattr(config, "PROS_MAX_TOTAL", 150.0)
            if pros_max_total is None or total <= float(pros_max_total):
                dm = float(dealer_margin_pct or 0.0)

                # Always compute score so we can detect Cat-3 override.
                ps = score_prospect(lst, fmv_floor=fmv_floor, dealer_value=dealer_value)
                cat3_override = ("premium-terms-priced-like-raw" in (ps.reasons or []))

                # Base gate: dealer margin threshold (conservative exit)
                base_ok = dm >= float(getattr(config, "PROS_MIN_DEALER_MARGIN_PCT", 50.0))

                # Final gate: base_ok OR cat3_override, then score threshold
                if (base_ok or cat3_override) and int(ps.score) >= int(getattr(config, "PROS_MIN_SCORE", 75)):
                    is_prospect = True
# --- Assemble normalized calc dict (UI-safe)
        # --- Assemble normalized calc dict (UI-safe)
        # IMPORTANT: keys here are part of the module interface contract across the scaffolding.
        # Keep names aligned with silver_math.calc_silver() outputs.
        calc = {
            # Melt metrics
            "quantity": silver.get("quantity"),
            "oz_per_coin": silver.get("oz_per_coin"),
            "total_oz": silver.get("total_oz"),
            "melt_value": silver.get("melt_value"),
            "melt_payout": silver.get("melt_payout"),
            "profit": silver.get("profit"),
            "margin_pct": silver.get("margin_pct"),

            # Melt recommendations
            "rec_max_total": silver.get("rec_max_total"),
            "rec_max_item": silver.get("rec_max_item"),
            "profit_at_rec_max": silver.get("profit_at_rec_max"),
            "margin_at_rec_max": silver.get("margin_at_rec_max"),

            # Numismatic (optional overlay)
            "numismatic_override": override.display_name if override else None,
            "fmv_floor": fmv_floor,
            "fmv_source": fmv_source,
            "dealer_value": dealer_value,
            "dealer_profit": dealer_profit,
            "dealer_margin_pct": dealer_margin_pct,
            "dealer_rec_max_total": dealer_rec_max_total,
            "dealer_rec_max_item": dealer_rec_max_item,
            "dealer_profit_at_rec_max": dealer_profit_at_rec,
            "dealer_margin_at_rec_max": dealer_margin_at_rec,

            # Flags
            "is_prospect": is_prospect,

            # Links
            "coinbook_url": coinbook_url,
        }

        evaluated.append(
            Evaluated(
                listing=lst,
                silver_calc=calc,
                is_hit=is_hit,
                numismatic_override=override.display_name if override else None,
                is_prospect=is_prospect,
            )
        )

    # Sort earliest → latest
    evaluated.sort(key=lambda e: getattr(e.listing, "end_time_ts", 10**18))
    return evaluated


def select_hits(evaluated: List[Evaluated]) -> List[Evaluated]:
    """Select entries for email.

    UX contract: Email is comprehensive and includes:
      - melt HITs (e.is_hit)
      - numismatic prospects (numismatic_override present), even if not a melt HIT
    """
    out: List[Evaluated] = []
    for e in evaluated:
        if bool(getattr(e, "is_hit", False)):
            out.append(e)
            continue

        # Only include numismatic prospects when they pass the dealer-based prospect test.
        # Prefer the explicit flag to avoid interface drift between the dataclass and dict.
        if bool(getattr(e, "is_prospect", False)):
            out.append(e)
            continue

        sc = e.silver_calc if isinstance(getattr(e, "silver_calc", None), dict) else {}
        if bool(sc.get("is_prospect")):
            out.append(e)

    return out
