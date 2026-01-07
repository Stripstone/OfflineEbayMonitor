# classifier.py
"""
CLASSIFIER — HIT/MISS Classification Engine

Sprint 05.5 scope: Basic melt HIT/MISS only
Sprint 06.1: Add diagnostic tracking

Responsibility:
- Accept list of parsed listings
- For each listing, determine HIT or MISS based on melt economics
- Return list of Evaluated objects
- Track diagnostics (if enabled)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

import silver_math


# =============================================================================
# MODULE-LEVEL DIAGNOSTIC STATE (Sprint 06.1)
# =============================================================================

_diagnostics = {
    "total_listings_seen": 0,
    "eligible_count": 0,
    "hit_count": 0,
    "miss_count": 0,
    "ineligible_count": 0,
    "pros_count": 0,
    "rejection_buckets": {},
    "samples_by_reason": {}
}


def get_diagnostics() -> dict:
    """
    Return current diagnostic data (does NOT reset).
    
    Sprint 06.1: Export accumulated diagnostic state.
    """
    global _diagnostics
    return _diagnostics.copy()


def reset_diagnostics_state():
    """
    Reset diagnostic state.
    
    Sprint 06.1: Called by silver_monitor between cycles if needed.
    Note: Per Master Sprint Plan, diagnostics persist across cycles within one run.
    """
    global _diagnostics
    _diagnostics = {
        "total_listings_seen": 0,
        "eligible_count": 0,
        "hit_count": 0,
        "miss_count": 0,
        "ineligible_count": 0,
        "pros_count": 0,
        "rejection_buckets": {},
        "samples_by_reason": {}
    }


def _track_rejection(reason: str, title: str, reason_detail: str):
    """
    Track rejection reason with sample title.
    
    Args:
        reason: Rejection reason key
        title: Listing title
        reason_detail: Human-readable detail
    """
    global _diagnostics
    
    # Increment bucket count
    if reason not in _diagnostics["rejection_buckets"]:
        _diagnostics["rejection_buckets"][reason] = 0
    _diagnostics["rejection_buckets"][reason] += 1
    
    # Add sample (max 3 per reason)
    if reason not in _diagnostics["samples_by_reason"]:
        _diagnostics["samples_by_reason"][reason] = []
    
    if len(_diagnostics["samples_by_reason"][reason]) < 3:
        _diagnostics["samples_by_reason"][reason].append({
            "title": title,
            "reason_detail": reason_detail
        })


def _check_blocked_terms(title: str) -> tuple[bool, str]:
    """
    Check if title contains blocked terms.
    
    Returns:
        (is_blocked, reason_detail)
    
    Sprint 06: Filter gate
    """
    import config
    
    if not title:
        return False, ""
    
    title_lower = title.lower()
    
    for term in config.BLOCKED_TERMS:
        if term.lower() in title_lower:
            return True, f"Contains blocked term: {term}"
    
    return False, ""


# =============================================================================
# CLASSIFICATION
# =============================================================================

@dataclass
class Evaluated:
    """
    Classification result container.
    
    Sprint 05.5 fields:
        listing: Parsed listing object
        silver_calc: Melt calculation dict from silver_math.calc_silver()
        is_hit: HIT if total_price <= rec_max_total
        is_prospect: Always False in Sprint 05.5 (Sprint 06.3+)
    """
    listing: Any
    silver_calc: dict
    is_hit: bool
    is_prospect: bool = False


def classify_listings(listings: List[Any], diagnostics_enabled: bool = False) -> List[Evaluated]:
    """
    Classify listings as HIT or MISS based on melt economics.
    
    Args:
        listings: Parsed listing objects from parser_listings
        diagnostics_enabled: Enable diagnostic tracking (Sprint 06.1)
    
    Returns:
        List of Evaluated objects, sorted by end_time_ts (earliest first)
    
    Sprint 05.5 logic:
        - HIT if total_price <= rec_max_total
        - MISS otherwise
        - is_prospect always False (Sprint 06.3)
    
    Sprint 06.1: Track diagnostics if enabled
    """
    global _diagnostics
    
    evaluated: List[Evaluated] = []
    
    # Track eligible count (total_listings_seen set by silver_monitor)
    if diagnostics_enabled:
        _diagnostics["eligible_count"] += len(listings)
    
    for listing in listings:
        title = getattr(listing, "title", "Unknown")
        
        # Sprint 06: Filter gates (INELIGIBLE checks)
        if diagnostics_enabled:
            # Check blocked terms
            is_blocked, block_reason = _check_blocked_terms(title)
            if is_blocked:
                _diagnostics["ineligible_count"] += 1
                _track_rejection("blocked_terms", title, block_reason)
                continue
            
            # Check missing data
            total_price = getattr(listing, "total_price", None)
            time_left = getattr(listing, "time_left", None)
            qty = getattr(listing, "qty", 1)
            
            if total_price is None or total_price <= 0:
                _diagnostics["ineligible_count"] += 1
                _track_rejection("missing_price", title, "No valid total_price")
                continue
            
            if time_left is None:
                _diagnostics["ineligible_count"] += 1
                _track_rejection("missing_time", title, "No time_left data")
                continue
            
            if qty < 1:
                _diagnostics["ineligible_count"] += 1
                _track_rejection("invalid_qty", title, f"Invalid quantity: {qty}")
                continue
        
        # Get melt calculations
        silver_calc = silver_math.calc_silver(listing)
        
        # Extract values for classification
        rec_max = silver_calc.get("rec_max_total")
        total_price = float(getattr(listing, "total_price", 0.0) or 0.0)
        margin_pct = silver_calc.get("margin_pct", 0.0)
        
        # Classify: HIT if total_price <= rec_max_total
        is_hit = False
        
        if rec_max is None or total_price <= 0:
            # Missing price data
            if diagnostics_enabled:
                title = getattr(listing, "title", "Unknown")
                if total_price <= 0:
                    _track_rejection("missing_price", title, "No total_price available")
                else:
                    _track_rejection("missing_price", title, "No rec_max calculated")
        elif total_price <= rec_max:
            # HIT
            is_hit = True
            if diagnostics_enabled:
                _diagnostics["hit_count"] += 1
        else:
            # MISS - insufficient margin
            if diagnostics_enabled:
                _diagnostics["miss_count"] += 1
                title = getattr(listing, "title", "Unknown")
                import config
                threshold = config.MIN_MARGIN_PCT
                _track_rejection(
                    "insufficient_margin",
                    title,
                    f"Margin {margin_pct:.1f}% < {threshold:.1f}% threshold"
                )
        
        # Create Evaluated object
        evaluated.append(Evaluated(
            listing=listing,
            silver_calc=silver_calc,
            is_hit=is_hit,
            is_prospect=False  # Sprint 06.3
        ))
    
    # Sort by earliest ending time (defensive None-checking)
    # Parser may not provide end_time_ts or it may be None
    evaluated.sort(key=lambda e: getattr(e.listing, "end_time_ts", None) or 10**18)
    
    return evaluated


#EndOfFile
