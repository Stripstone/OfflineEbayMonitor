# prospect_score.py
"""
PROSPECT SCORE (PCX) — Prospect Scoring (Numismatic Only)

Sprint 05 guarantees:
- Deterministic score + reasons from TITLE-DRIVEN signals only
- Linear additive scoring
- Hard disqualifiers short-circuit (score=0, emit reasons, stop)
- No EMA writes, no price_store imports, no UX side effects
- Pure function style

#EndOfFile
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Any
import re

import config


# -----------------------------
# Public data structure
# -----------------------------

@dataclass(frozen=True)
class ProspectScore:
    score: int
    reasons: List[str]


# -----------------------------
# Helpers (pure, deterministic)
# -----------------------------

def _has_any(title: str, needles: List[str]) -> bool:
    t = (title or "").lower()
    for n in needles or []:
        n2 = str(n).strip().lower()
        if n2 and n2 in t:
            return True
    return False


def _matches_any_regex(title: str, patterns: List[str]) -> bool:
    s = title or ""
    for pat in patterns or []:
        try:
            if re.search(str(pat), s, flags=re.I):
                return True
        except Exception:
            continue
    return False


def _minutes_left(listing: Any) -> Optional[int]:
    """
    Best-effort minutes-left.
    Uses end_time_ts if present; otherwise parses simple 'Xm left' / 'X min' strings.
    """
    end_ts = getattr(listing, "end_time_ts", None)
    if end_ts is not None:
        try:
            import time as _time
            sec = float(end_ts) - _time.time()
            if sec >= 0:
                return int(sec // 60)
        except Exception:
            pass

    tleft = getattr(listing, "time_left", "") or ""
    s = tleft.lower()

    m = re.search(r"(\d{1,4})\s*m\b", s)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None

    m = re.search(r"(\d{1,3})\s*min\b", s)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None

    return None


# -----------------------------
# Scoring function (Sprint 05)
# -----------------------------

def score_prospect(
    listing: Any,
    *,
    fmv_floor: Optional[float],
    dealer_value: Optional[float],
) -> ProspectScore:
    """
    Deterministic prospect score for numismatic upside.

    Inputs:
      listing.title (str)
      listing.total_price (float)
      listing.bids (int)
      listing.time_left (str, optional)
      listing.end_time_ts (optional)

    Anchors:
      fmv_floor     — authoritative FMV floor
      dealer_value — fmv_floor * dealer payout pct (passed in)

    Returns:
      ProspectScore(score=0..100, reasons=[...])
    """

    title = getattr(listing, "title", "") or ""
    total = float(getattr(listing, "total_price", 0.0) or 0.0)
    bids = int(getattr(listing, "bids", 0) or 0)

    # ---- Anchor gate (hard)
    if fmv_floor is None or dealer_value is None or total <= 0:
        return ProspectScore(score=0, reasons=["missing-anchors"])

    # ---- Hard disqualifiers (short-circuit)
    hard_kw = []
    hard_kw.extend(getattr(config, "PROS_HARD_DISQUALIFY_KEYWORDS", []) or [])
    hard_kw.extend(getattr(config, "PROS_DISQUALIFY_KEYWORDS", []) or [])

    if _has_any(title, hard_kw):
        return ProspectScore(score=0, reasons=["pros-hard-disqualify-keyword"])

    if _matches_any_regex(title, getattr(config, "PROS_DISQUALIFY_REGEX", []) or []):
        return ProspectScore(score=0, reasons=["pros-hard-disqualify-regex"])

    # ---- Base score
    score = 50
    reasons: List[str] = []

    # ---- Dealer margin (primary signal)
    dealer_margin_pct = ((dealer_value - total) / total) * 100.0
    if dealer_margin_pct >= 75:
        score += 25
        reasons.append("huge-dealer-margin")
    elif dealer_margin_pct >= 50:
        score += 18
        reasons.append("dealer-margin>=50")
    elif dealer_margin_pct >= 35:
        score += 10
        reasons.append("dealer-margin>=35")
    elif dealer_margin_pct >= 20:
        score += 4
        reasons.append("dealer-margin>=20")
    else:
        score -= 20
        reasons.append("thin-dealer-margin")

    # ---- FMV gap (secondary)
    fmv_gap_pct = ((fmv_floor - total) / total) * 100.0
    if fmv_gap_pct >= 100:
        score += 10
        reasons.append("fmv-gap>=100")
    elif fmv_gap_pct >= 50:
        score += 6
        reasons.append("fmv-gap>=50")

    # ---- Bid count (confidence / unnoticed)
    if bids <= 0:
        score += 4
        reasons.append("unnoticed(0-bids)")
    elif bids <= 2:
        score += 7
        reasons.append("few-bids")
    elif bids <= 10:
        score += 4
        reasons.append("some-bids")
    else:
        score += 1
        reasons.append("many-bids")

    # ---- Title quality signals
    if _has_any(title, getattr(config, "PROS_HYPE_KEYWORDS", [])):
        score -= 18
        reasons.append("hype-language")

    if _has_any(title, getattr(config, "PROS_UNDERDESCRIBED_KEYWORDS", [])):
        score += 12
        reasons.append("under-described")

    if _has_any(title, getattr(config, "PROS_HIGH_GRADE_KEYWORDS", [])):
        score -= 14
        reasons.append("high-grade-signals")

    # ---- Premium terms priced like raw (Category-3 PROS)
    if _has_any(title, getattr(config, "PROS_HIGH_GRADE_KEYWORDS", [])):
        tol_pct = float(getattr(config, "PROS_CAT3_MISPRICE_TOL_PCT", 0.0) or 0.0) / 100.0
        if total <= float(fmv_floor) * (1.0 + max(0.0, tol_pct)):
            require_soon = bool(getattr(config, "PROS_CAT3_REQUIRE_ENDING_SOON", False))
            soon_ok = True
            if require_soon:
                mins = _minutes_left(listing)
                max_min = int(getattr(config, "PROS_CAT3_MAX_MINUTES", 30))
                soon_ok = mins is not None and mins <= max_min

            if soon_ok:
                bonus = int(getattr(config, "PROS_CAT3_MISPRICE_BONUS", 20))
                score += max(0, bonus)
                reasons.append("premium-terms-priced-like-raw")

    # ---- Time-left urgency (minor)
    tleft = (getattr(listing, "time_left", "") or "").lower()
    if "m left" in tleft or "min" in tleft:
        score += 3
        reasons.append("ending-soon")

    # ---- Clamp + finalize
    score = int(max(0, min(100, round(score))))
    return ProspectScore(score=score, reasons=reasons)

#EndOfFile
