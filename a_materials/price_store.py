# price_store.py
"""PRICE STORE (price_store.json)

Compact schema (per user requirement):
{
  "Morgan Dollar|1883|O": [63.0, 17, 63.0, 1765618492, 30]
}

Index meanings:
  0 EMA_PRICE
  1 SAMPLES
  2 LAST_TOTAL_PRICE
  3 LAST_UPDATED (unix ts)
  4 OBSERVERS_TOTAL (cumulative bid-count total contributing to EMA)

Rules:
- Updates are only applied when bid_count >= 1 (blueprint) when PRICE_CAPTURE_ONLY_IF_BIDS is True.
- Uses active listing item prices (shipping excluded).
- Capture can be called every scan regardless of HIT/seen status.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional, Tuple

import config
from utils import now_ts

EMA_PRICE = 0
SAMPLES = 1
LAST_TOTAL_PRICE = 2
LAST_UPDATED = 3
OBSERVERS_TOTAL = 4

Store = Dict[str, list]


def load_store(path: Optional[str] = None) -> Store:
    p = path or config.PRICE_STORE_PATH
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}

    out: Store = {}
    for k, v in raw.items():
        if isinstance(v, list) and len(v) >= 5:
            try:
                out[str(k)] = [
                    float(v[0]),
                    int(v[1]),
                    float(v[2]),
                    int(v[3]),
                    int(v[4]),
                ]
            except Exception:
                continue
        elif isinstance(v, dict):
            # allow legacy dict format for migration
            try:
                out[str(k)] = [
                    float(v.get("ema_price", 0.0)),
                    int(v.get("samples", 0)),
                    float(v.get("last_total_price", v.get("last_price", 0.0))),
                    int(v.get("last_updated", 0)),
                    int(v.get("observers_total", v.get("last_bid_count", 0))),
                ]
            except Exception:
                continue
    return out


def save_store(store: Store, path: Optional[str] = None) -> None:
    """
    Write valid JSON that is human-readable:
    - one key/value per line
    - value arrays kept on ONE line
    - sorted keys
    - newline at EOF
    """
    p = path or config.PRICE_STORE_PATH
    keys = sorted(store.keys())

    with open(p, "w", encoding="utf-8") as f:
        f.write("{\n")
        for i, k in enumerate(keys):
            # ensure JSON-safe key string and compact one-line value list
            key_json = json.dumps(str(k), ensure_ascii=False)
            val_json = json.dumps(store[k], ensure_ascii=False)
            line = f"  {key_json}: {val_json}"
            if i < len(keys) - 1:
                line += ","
            f.write(line + "\n")
        f.write("}\n")


def update_ema_entry(existing: Optional[list], new_total_price: float, bid_count: int, alpha: float) -> list:
    ts = now_ts()

    # Initialize
    if existing is None:
        return [round(new_total_price, 2), 1, round(new_total_price, 2), ts, int(bid_count)]

    try:
        ema = float(existing[EMA_PRICE])
        samples = int(existing[SAMPLES])
    except Exception:
        ema = float(new_total_price)
        samples = 0

    ema = (alpha * float(new_total_price)) + ((1.0 - alpha) * float(ema))
    samples = samples + 1

    # Observers: accumulate bid_count contributions over time.
    try:
        observers = int(existing[OBSERVERS_TOTAL])
    except Exception:
        observers = 0
    observers = observers + int(bid_count)

    return [round(ema, 2), int(samples), round(new_total_price, 2), ts, int(observers)]


def update_price(store: Store, key: str, total_price: float, bid_count: int) -> bool:
    """Update one key. Returns True if updated."""
    if not key:
        return False

    # HARD RULE (Batch 2): only capture if bids >= 1 when enabled
    if config.PRICE_CAPTURE_ONLY_IF_BIDS and int(bid_count) < 1:
        return False

    if total_price is None or float(total_price) <= 0:
        return False

    # Apply capture bump to simulate late auction bidding.
    bump = float(getattr(config, "PRICE_CAPTURE_BUMP_PCT", 0.0) or 0.0)
    bumped_total = float(total_price) * (1.0 + bump)

    existing = store.get(key)
    store[key] = update_ema_entry(existing, float(bumped_total), int(bid_count), float(config.EMA_ALPHA))
    return True


def lookup_ema(store: Store, key: str) -> Optional[float]:
    entry = store.get(key)
    if not entry or len(entry) < 1:
        return None
    try:
        return float(entry[EMA_PRICE])
    except Exception:
        return None


def lookup_observers(store: Store, key: str) -> Optional[int]:
    entry = store.get(key)
    if not entry or len(entry) < 5:
        return None
    try:
        return int(entry[OBSERVERS_TOTAL])
    except Exception:
        return None


def capture_updates(store: Store, updates: Dict[str, Tuple[float, int]]) -> int:
    """Bulk update: {key: (total_price, bid_count)} -> count updated."""
    n = 0
    for k, (total_price, bid_count) in updates.items():
        if update_price(store, k, total_price, bid_count):
            n += 1
    return n


# -----------------------------
# Convenience getters (legacy compatibility)
# -----------------------------

def get_ema_value(key: str, store: Store | None = None) -> Optional[float]:
    """Return the offline EMA price for a benchmark key (or None)."""
    if store is None:
        store = load_store()
    return lookup_ema(store, key)


def get_ema_value_and_observers(key: str, store: Store | None = None) -> Tuple[Optional[float], Optional[int]]:
    """Return (ema_value, observers_total) for a benchmark key."""
    if store is None:
        store = load_store()
    return lookup_ema(store, key), lookup_observers(store, key)


def get_offline_ema_value(coin_type: str, year: int | str, mint: str, store: Store | None = None) -> Optional[float]:
    """Legacy helper: build key from coin_type/year/mint."""
    key = f"{coin_type}|{year}|{mint}"
    return get_ema_value(key, store)
