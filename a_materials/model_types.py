# model_types.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Listing:
    title: str
    link: str
    item_price: float
    shipping: float
    total_price: float
    bids: int
    time_left: str

    item_id: Optional[str] = None
    quantity: int = 1
    oz_per_coin: float = 0.0

    # populated later
    numismatic_override: Optional[Dict[str, Any]] = None
    silver_calc: Optional[Dict[str, float]] = None


@dataclass
class PricePoint:
    # Compact schema: [ema_price, samples, last_total_price, last_updated, last_bid_count]
    ema_price: float
    samples: int
    last_total_price: float
    last_updated: int
    last_bid_count: int
