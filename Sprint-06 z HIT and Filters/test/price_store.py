# price_store.py
"""PRICE STORE (price_store.json)

Compact schema (authoritative):
{
  "<normalized_key>": [ema_value, samples, last_total_price, last_updated_ts, observers_total]
}

Index meanings:
  0 EMA_PRICE
  1 SAMPLES
  2 LAST_TOTAL_PRICE
  3 LAST_UPDATED (unix ts)
  4 OBSERVERS_TOTAL (cumulative bid-count total contributing to EMA)

Sprint 04 corrective pass:
- FULL EMA eligibility enforcement at write-time (Contract_Packet_v1.1)
- STRICT + SILENT: ineligible => no-op, no mutation, no observer accumulation
- No logging, no printing, no UX side effects

Eligibility (all must be true):
- qty == 1
- bids >= 1
- NOT lot / roll / set / face value
- NOT album / folder / book / "NO COINS"
- NOT accessory (money clip, keychain, pendant, jewelry, cutout, etc.)
- NOT damaged (holed/hole, pierced, drilled)

#EndOfFile
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, Optional, Tuple

import config
from utils import now_ts

# ---- schema indices ----
EMA_PRICE = 0
SAMPLES = 1
LAST_TOTAL_PRICE = 2
LAST_UPDATED = 3
OBSERVERS_TOTAL = 4

Store = Dict[str, list]

# -----------------------------
# EMA eligibility (write-time)
# -----------------------------

# NOTE: These patterns are intentionally conservative and title-only.
# They must remain SILENT and produce strict no-ops.
_DISQUALIFY_PATTERNS = (
    # lot / roll / set / face value
    re.compile(r"\blot\b", re.IGNORECASE),
    re.compile(r"\broll\b", re.IGNORECASE),
    re.compile(r"\bset\b", re.IGNORECASE),
    re.compile(r"\bface\s*value\b", re.IGNORECASE),
    re.compile(r"\bface\s*\$\s*\d", re.IGNORECASE),

    # album / folder / book / no coins
    re.compile(r"\balbum\b", re.IGNORECASE),
    re.compile(r"\bfolder\b", re.IGNORECASE),
    re.compile(r"\bbook\b", re.IGNORECASE),
    re.compile(r"\bno\s*coins?\b", re.IGNORECASE),

    # accessories
    re.compile(r"\bmoney\s*clip\b", re.IGNORECASE),
    re.compile(r"\bkey\s*chain\b|\bkeychain\b", re.IGNORECASE),
    re.compile(r"\bpendant\b", re.IGNORECASE),
    re.compile(r"\bjewelry\b", re.IGNORECASE),
    re.compile(r"\bnecklace\b", re.IGNORECASE),
    re.compile(r"\bbracelet\b", re.IGNORECASE),
    re.compile(r"\bring\b", re.IGNORECASE),
    re.compile(r"\bcutout\b", re.IGNORECASE),

    # damaged
    re.compile(r"\bholed\b|\bhole\b", re.IGNORECASE),
    re.compile(r"\bpierced\b|\bpierce\b", re.IGNORECASE),
    re.compile(r"\bdrilled\b|\bdrill\b", re.IGNORECASE),
)


def _is_ema_eligible(*, qty: int, bid_count: int, title: str) -> bool:
    """
    Contract_Packet_v1.1 eligibility gate.
    Strict and silent: returns False if any requirement fails.
    """
    try:
        if int(qty) != 1:
            return False
    except Exception:
        return False

    try:
        if int(bid_count) < 1:
            return False
    except Exception:
        return False

    if not isinstance(title, str) or not title.strip():
        # Without a title, we cannot enforce the disqualifier rules safely.
        return False

    t = title.strip()
    for rx in _DISQUALIFY_PATTERNS:
        if rx.search(t):
            return False

    return True


# -----------------------------
# IO
# -----------------------------

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
                    float(v[EMA_PRICE]),
                    int(v[SAMPLES]),
                    float(v[LAST_TOTAL_PRICE]),
                    int(v[LAST_UPDATED]),
                    int(v[OBSERVERS_TOTAL]),
                ]
            except Exception:
                continue
        elif isinstance(v, dict):
            # legacy dict migration (best-effort)
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
    Write stable, human-readable JSON:
    - one key/value per line
    - compact one-line arrays
    - sorted keys
    - newline at EOF
    """
    p = path or config.PRICE_STORE_PATH
    keys = sorted(store.keys())

    with open(p, "w", encoding="utf-8") as f:
        f.write("{\n")
        for i, k in enumerate(keys):
            key_json = json.dumps(str(k), ensure_ascii=False)
            val_json = json.dumps(store[k], ensure_ascii=False)
            line = f"  {key_json}: {val_json}"
            if i < len(keys) - 1:
                line += ","
            f.write(line + "\n")
        f.write("}\n")


# -----------------------------
# EMA core (pure math)
# -----------------------------

def _update_ema_entry(
    existing: Optional[list],
    new_total_price: float,
    bid_count: int,
    alpha: float,
) -> list:
    """
    Pure EMA update:
      ema = alpha*new + (1-alpha)*old
    Storage rounds to 2dp for schema stability.
    """
    ts = now_ts()

    # initialize
    if existing is None:
        return [
            round(new_total_price, 2),
            1,
            round(new_total_price, 2),
            ts,
            int(bid_count),
        ]

    try:
        prev_ema = float(existing[EMA_PRICE])
        samples = int(existing[SAMPLES])
        observers = int(existing[OBSERVERS_TOTAL])
    except Exception:
        prev_ema = float(new_total_price)
        samples = 0
        observers = 0

    ema = (alpha * float(new_total_price)) + ((1.0 - alpha) * float(prev_ema))
    samples = samples + 1
    observers = observers + int(bid_count)

    return [
        round(ema, 2),
        int(samples),
        round(new_total_price, 2),
        ts,
        int(observers),
    ]


# -----------------------------
# Public callable API (Sprint 04)
# -----------------------------

def update_price(
    store: Store,
    key: str,
    total_price: float,
    bid_count: int,
    *,
    qty: Optional[int] = None,
    title: Optional[str] = None,
) -> bool:
    """
    Callable EMA update with FULL eligibility enforcement.

    STRICT, SILENT no-op unless eligible:
    - qty must be provided and == 1
    - title must be provided (non-empty) and must NOT match disqualifiers
    - bids >= 1
    - total_price numeric > 0

    Returns:
      True  -> update applied (store mutated, observers accumulated)
      False -> strict no-op (no mutation)
    """
    if not key:
        return False

    # Require these inputs for full eligibility enforcement (strict).
    if qty is None or title is None:
        return False

    if not _is_ema_eligible(qty=int(qty), bid_count=int(bid_count), title=str(title)):
        return False

    # eligibility: price gate
    try:
        if total_price is None or float(total_price) <= 0:
            return False
    except Exception:
        return False

    # capture-time bump (applied once, write-time only)
    bump_pct = float(getattr(config, "PRICE_CAPTURE_BUMP_PCT", 0.0) or 0.0)
    bumped_total = float(total_price) * (1.0 + bump_pct)

    existing = store.get(key)
    store[key] = _update_ema_entry(
        existing=existing,
        new_total_price=float(bumped_total),
        bid_count=int(bid_count),
        alpha=float(config.EMA_ALPHA),
    )
    return True


# -----------------------------
# Lookups (read-only helpers)
# -----------------------------

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


def get_ema_value(key: str, store: Store | None = None) -> Optional[float]:
    """Return offline EMA price for a benchmark key."""
    if store is None:
        store = load_store()
    return lookup_ema(store, key)


def get_ema_value_and_observers(
    key: str, store: Store | None = None
) -> Tuple[Optional[float], Optional[int]]:
    """Return (ema_value, observers_total) for a benchmark key."""
    if store is None:
        store = load_store()
    return lookup_ema(store, key), lookup_observers(store, key)


def get_offline_ema_value(
    coin_type: str, year: int | str, mint: str, store: Store | None = None
) -> Optional[float]:
    """Build normalized key from coin_type/year/mint."""
    key = f"{coin_type}|{year}|{mint}"
    return get_ema_value(key, store)


#EndOfFile
