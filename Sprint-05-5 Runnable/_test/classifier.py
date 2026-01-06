# classifier.py
"""
CLASSIFIER — HIT/MISS Classification Engine

Sprint 05.5 scope: Basic melt HIT/MISS only
Sprint 06.1+: Diagnostics, filters, PROS

Responsibility:
- Accept list of parsed listings
- For each listing, determine HIT or MISS based on melt economics
- Return list of Evaluated objects
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

import silver_math


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


def classify_listings(listings: List[Any]) -> List[Evaluated]:
    """
    Classify listings as HIT or MISS based on melt economics.
    
    Args:
        listings: Parsed listing objects from parser_listings
    
    Returns:
        List of Evaluated objects, sorted by end_time_ts (earliest first)
    
    Sprint 05.5 logic:
        - HIT if total_price <= rec_max_total
        - MISS otherwise
        - is_prospect always False (Sprint 06.3)
    """
    evaluated: List[Evaluated] = []
    
    for listing in listings:
        # Get melt calculations
        silver_calc = silver_math.calc_silver(listing)
        
        # Classify: HIT if total_price <= rec_max_total
        rec_max = silver_calc.get("rec_max_total")
        total_price = float(getattr(listing, "total_price", 0.0) or 0.0)
        
        is_hit = False
        if rec_max is not None and total_price > 0:
            is_hit = (total_price <= rec_max)
        
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
