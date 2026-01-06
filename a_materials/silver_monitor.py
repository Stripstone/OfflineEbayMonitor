# silver_monitor.py
"""
EBAY OFFLINE SILVER MONITOR

User-facing guarantees:
- Clean console output
- Hit!/Miss table for listings within time window
- Relevant cycles X / Y
- Compact, standardized email output
"""

from __future__ import annotations

import time
import random
from datetime import datetime
from typing import List

import config

from html_loader import discover_html_files, load_html_file, delete_processed_files
from ebay_search_parser import parse_ebay_search_html
from price_store import load_store, save_store, capture_updates
from numismatic_rules import detect_coin_identity, make_benchmark_key
from hit_engine import evaluate_listings, select_hits
from state_store import load_seen_hits, save_seen_hits, split_new_hits
from email_format import build_email_subject, build_email_body
from emailer import send_email
from console_tables import print_hit_miss_table
from silver_math import extract_quantity_from_title

import re


# Hard disqualifiers: problem/damage terms that should not be valued as melt or numismatic.
# Policy: skip entirely (no EMA capture, no HIT/PROS, no melt valuation).
_HARD_DISQUALIFY_RE = re.compile(
    r"(?i)\b(?:holed|hole|pierced|drilled|copy|replica|clad|plated)\b"
)



# -----------------------------
# Helpers
# -----------------------------

def _now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _filename_is_silver(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in config.SILVER_FILENAME_KEYWORDS)


def _passes_blacklist(title: str, blacklist: List[str]) -> bool:
    t = (title or "").lower()
    for kw in blacklist:
        if kw.lower() in t:
            return False
    return True


def _earliest_time_str(hits) -> str:
    """
    Returns earliest end time formatted as: '02:39 PM'
    """
    times = [
        getattr(e.listing, "end_time_ts", None)
        for e in hits
        if getattr(e.listing, "end_time_ts", None) is not None
    ]
    if not times:
        return datetime.now().strftime("%I:%M %p")
    ts = min(times)
    return datetime.fromtimestamp(ts).strftime("%I:%M %p")

def _dedupe_key_from_listing(lst) -> str:
    """
    Stable dedupe key.
    Prefer item_id, then normalized URL (no query), then title.
    """
    item_id = getattr(lst, "item_id", None)
    if item_id:
        return f"itm:{item_id}"

    url = getattr(lst, "url", "") or ""
    title = getattr(lst, "title", "") or ""
    if url:
        # strip tracking/query noise to keep stable across saves
        base = url.split("?", 1)[0].split("#", 1)[0]
        return f"url:{base}"
    return f"title:{title.strip().lower()}"


def _dedupe_listings_in_run(listings: List) -> List:
    """Remove duplicate listing cards within a single scan.

    eBay search pages often repeat the same item in multiple modules.
    We dedupe before valuation and EMA capture to prevent inflation.
    """
    seen = set()
    out = []
    for lst in listings:
        k = _dedupe_key_from_listing(lst)
        if k in seen:
            continue
        seen.add(k)
        out.append(lst)
    return out

def _passes_positive_required_terms(source_file: str, title: str) -> bool:
    rules = getattr(config, "POSITIVE_REQUIRED_TERMS_RULES", []) or []
    if not rules:
        return True

    matched = None
    for rule in rules:
        rx = rule.get("source_regex")
        if not rx:
            continue
        try:
            if re.search(rx, source_file or ""):
                matched = rule
                break
        except re.error:
            continue

    if not matched:
        return True  # no rule for this file => allow

    t = (title or "").lower()
    for group in matched.get("groups", []) or []:  # AND of OR-groups
        if not any((term or "").lower() in t for term in (group or [])):
            return False
    return True

def _capture_disqualified(title: str) -> bool:
    t = (title or "").lower()
    for kw in getattr(config, "PRICE_CAPTURE_DISQUALIFY_KEYWORDS", []) or []:
        if kw and kw.lower() in t:
            return True
    for pat in getattr(config, "PRICE_CAPTURE_DISQUALIFY_REGEX", []) or []:
        try:
            if re.search(pat, title or ""):
                return True
        except re.error:
            continue
    return False

# -----------------------------
# Core cycle
# -----------------------------

def run_once(min_qty: int | None, blacklist: List[str]):
    html_paths = discover_html_files(config.HTML_FOLDER_PATH, _filename_is_silver)
    files_found = len(html_paths)

    if files_found == 0:
        return {
            "had_files": False,
            "evaluated": [],
            "hits": [],
            "new_hits": [],
            "files_found": 0,
            "parsed": 0,
        }

    listings_all = []
    processed_paths = []
    parsed = 0

    # Parse HTML
    for path in html_paths:
        fname, html = load_html_file(path)
        listings = parse_ebay_search_html(fname, html)

        kept = []
        for lst in listings:
            lst.source_file = fname

            # POSITIVE PAGE-SANITY FILTER
            if not _passes_positive_required_terms(lst.source_file, lst.title):
                # debug / sanity logging
                # print(f"[DROP][POSITIVE] {fname} :: {lst.title}")
                continue

            kept.append(lst)

        if kept:
            processed_paths.append(path)

        listings_all.extend(kept)
        parsed += len(kept)


    # Intra-run dedupe (same item repeated in page modules)
    listings_all = _dedupe_listings_in_run(listings_all)

    # Filter listings (INCLUDING time window)
    filtered = []
    for lst in listings_all:
        # Hard disqualify damaged/problem coins per policy (skip entirely)
        if _HARD_DISQUALIFY_RE.search(lst.title or ""):
            continue

        if min_qty is not None:
            qty = extract_quantity_from_title(lst.title)
            if qty is not None and qty < min_qty:
                continue
        if not _passes_blacklist(lst.title, blacklist):
            continue

        # time window filter (so table shows only within max time)
        if config.MAX_TIME_HOURS is not None:
            end_ts = getattr(lst, "end_time_ts", None)
            if end_ts is None:
                continue
            seconds_left = float(end_ts) - time.time()
            if seconds_left < 0:
                continue
            if seconds_left > float(config.MAX_TIME_HOURS) * 3600.0:
                continue

        filtered.append(lst)

    # Price capture (bids > 0 enforced in price_store)
    store = load_store()
    updates = {}

    # Guardrail: do not allow the same listing (item_id/url) to contribute more than once per scan.
    capture_seen = set()

    for lst in filtered:
        # intra-run guardrail (defensive even after dedupe)
        lk = _dedupe_key_from_listing(lst)
        if lk in capture_seen:
            continue

        # Hard disqualify damaged/problem coins per policy (never record into EMA)
        if _HARD_DISQUALIFY_RE.search(lst.title or ""):
            continue

        # Do not capture obvious non-coin accessories into EMA.
        t = (lst.title or "").lower()
        if any(x in t for x in ["no coins", "coin book", "folder", "album", "money clip",
                                "keychain", "cutout", "pendant", "necklace"]):
            continue

        # --- EMA eligibility gates (capture-only) ---
        if _capture_disqualified(lst.title):
            continue

        qty = extract_quantity_from_title(lst.title)
        if qty != 1:
            continue

        cap_minutes = getattr(config, "PRICE_CAPTURE_MAX_MINUTES", None)
        if cap_minutes is not None:
            end_ts = getattr(lst, "end_time_ts", None)
            if end_ts is None:
                continue
            seconds_left = float(end_ts) - time.time()
            if seconds_left < 0 or seconds_left > float(cap_minutes) * 60.0:
                continue

        if getattr(config, "PRICE_CAPTURE_ONLY_IF_BIDS", False):
            if int(getattr(lst, "bids", 0) or 0) < 1:
                continue
        # --- end EMA eligibility gates ---

        ident = detect_coin_identity(lst.title)
        if not ident:
            continue
        coin_type, year, mint = ident
        key = make_benchmark_key(coin_type, year, mint)

        # Choose best candidate per benchmark key per scan:
        # prefer higher bids; if tie, prefer lower total (better deal signal).
        capture_price = getattr(lst, "price", None)
        if capture_price is None:
            capture_price = getattr(lst, "item_price", None)
        if capture_price is None:
            capture_price = getattr(lst, "total_price", None)
        try:
            capture_price = float(capture_price)
        except Exception:
            continue

        cur = (float(capture_price), int(lst.bids))

        prev = updates.get(key)
        if prev is None:
            updates[key] = cur
            capture_seen.add(lk)
        else:
            prev_total, prev_bids = float(prev[0]), int(prev[1])
            total, bids = cur
            if bids > prev_bids or (bids == prev_bids and total < prev_total):
                updates[key] = cur
                capture_seen.add(lk)

    if updates:
        capture_updates(store, updates)
        save_store(store)

    # Intra-run listing dedupe (prevents duplicate rows and EMA inflation)
    filtered = _dedupe_listings_in_run(filtered)

    # Evaluate (ARCHITECTURE-ALIGNED signature)
    evaluated = evaluate_listings(
        filtered,
        max_time_hours=config.MAX_TIME_HOURS,
    )

    hits = select_hits(evaluated)

    # Deduping
    seen = load_seen_hits()
    keys = {_dedupe_key_from_listing(e.listing) for e in hits}
    new_keys, merged = split_new_hits(keys, seen)
    new_hits = [e for e in hits if _dedupe_key_from_listing(e.listing) in new_keys]

    save_seen_hits(merged)

    # Delete processed HTML
    if getattr(config, "DELETE_PROCESSED_HTML", False):
        delete_processed_files(processed_paths)

    return {
        "had_files": True,
        "evaluated": evaluated,
        "hits": hits,
        "new_hits": new_hits,
        "files_found": files_found,
        "parsed": parsed,
    }


# -----------------------------
# Main loop
# -----------------------------

def main():
    print("\n============================================================")
    print("  EBAY OFFLINE SILVER MONITOR")
    print("============================================================\n")

    min_qty = config.DEFAULT_MIN_QUANTITY
    blacklist = list(config.DEFAULT_BLACKLIST or [])

    total_cycles = 0
    relevant_cycles = 0

    while True:
        total_cycles += 1

        try:
            result = run_once(min_qty, blacklist)

            if result["had_files"]:
                relevant_cycles += 1

            evaluated = result["evaluated"]
            hits = result["hits"]
            new_hits = result["new_hits"]

            print(
                f"[{_now_ts()}] Relevant cycles: "
                f"{relevant_cycles}/{total_cycles} | "
                f"Files: {result['files_found']} | "
                f"Listings: {result['parsed']} | "
                f"HITs: {len(hits)} | "
                f"New: {len(new_hits)}"
            )

            # Console table (Hit!/Miss) — accepts list OR dict now
            print_hit_miss_table(evaluated)

            # Email
            if new_hits and config.EMAIL_ENABLED:
                earliest = _earliest_time_str(new_hits)
                subject = build_email_subject(
                    earliest_time_str=earliest,
                    n_new=len(new_hits),
                    market_name="Silver",
                )
                body_html = build_email_body(new_hits)
                sent = send_email(subject, body_html)
                if sent:
                    print(f"EMAIL: sent ({len(new_hits)} new) | Subject: {subject}")
                else:
                    print(f"EMAIL: FAILED ({len(new_hits)} new) | Subject: {subject}")
            else:
                print("EMAIL: (no new HITs)")

        except KeyboardInterrupt:
            print("\n[EXIT] Monitor stopped by user.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")

        sleep_sec = (
            config.DEFAULT_CHECK_INTERVAL_MIN * 60
            + random.uniform(-config.SLEEP_JITTER_SEC, config.SLEEP_JITTER_SEC)
        )
        print(f"Sleep: {sleep_sec:.0f}s\n")
        time.sleep(max(10.0, sleep_sec))


if __name__ == "__main__":
    main()
