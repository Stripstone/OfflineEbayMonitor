# state_store.py
"""STATE STORE — seen_hits.json

Responsibilities:
- Persist which listings have already been alerted
- Ensure "no re-alerts based on time-left alone"

Store format (JSON):
{
  "version": 1,
  "created": 1765618492,
  "hits": [
      "itm:123456789012",
      "fallback:title|12.34|3h 2m left (Today 05:40 PM)"
  ]
}

Notes:
- Keys are opaque strings created by hit_engine.make_dedupe_key().
- This module is the ONLY place that should read/write seen_hits.json.
"""


from __future__ import annotations

import json
import os
from typing import Set, Tuple

import config
from utils import now_ts


def load_seen_hits(path: str = None) -> Set[str]:
    p = path or config.SEEN_HITS_PATH
    if not os.path.exists(p):
        return set()
    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return set()

    if isinstance(raw, dict) and "hits" in raw and isinstance(raw["hits"], list):
        return set(str(x) for x in raw["hits"] if x)
    if isinstance(raw, list):
        # legacy: list of keys
        return set(str(x) for x in raw if x)
    return set()


def save_seen_hits(keys: Set[str], path: str = None) -> None:
    p = path or config.SEEN_HITS_PATH
    payload = {
        "version": 1,
        "created": now_ts(),
        "hits": sorted(keys),
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))


def split_new_hits(candidate_keys: Set[str], seen_keys: Set[str]) -> Tuple[Set[str], Set[str]]:
    """Return (new_keys, merged_keys)."""
    new_keys = set(k for k in candidate_keys if k not in seen_keys)
    merged = set(seen_keys) | set(candidate_keys)
    return new_keys, merged
