# silver_monitor.py
"""
SILVER MONITOR — Runtime Orchestrator

Sprint 05.5 scope: Basic melt HIT/MISS foundation
Sprint 06.1+: Diagnostics, filters, PROS

Responsibilities:
- File discovery and loading
- Parser orchestration
- Filtering (time/qty/blacklist) — parser only provides data, not filtering
- EMA capture coordination
- Deduplication (intra-run and cross-run)
- Classification orchestration
- Console output
- Email coordination

Contract: v1.2 Section 1 (Console UX), Section 2 (Email UX)
SRM: v1.5
"""

from __future__ import annotations

import glob
import json
import os
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Set

import classifier
import config
import email_builder
import parser_listings
import price_store


# =============================================================================
# LISTINGADAPTER — Bridge parser dicts to classifier objects
# =============================================================================

class ListingAdapter:
    """
    Adapter: dict → object with attribute access.
    
    Required because:
    - parser_listings.py returns List[Dict[str, Any]] (Sprint 03 output)
    - classifier.py expects objects with .attribute access (Sprint 05.5 design)
    
    Contract: v1.2 + Clarifications (Issue #4)
    """
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def __getattr__(self, name: str):
        return self._data.get(name)


# =============================================================================
# FILE DISCOVERY
# =============================================================================

def discover_html_files() -> List[str]:
    """
    Discover HTML files in watch folder.
    
    Returns:
        List of absolute file paths matching silver keywords
    
    Contract: v1.2 Section 6 (HTML_FOLDER_PATH)
    """
    folder = config.HTML_FOLDER_PATH
    if not os.path.exists(folder):
        return []
    
    all_files = glob.glob(os.path.join(folder, "*.html"))
    
    # Filter by silver keywords
    silver_files = []
    for filepath in all_files:
        filename = os.path.basename(filepath).lower()
        if any(kw in filename for kw in config.SILVER_FILENAME_KEYWORDS):
            silver_files.append(filepath)
    
    return silver_files


# =============================================================================
# PARSING
# =============================================================================

def read_file(filepath: str) -> str:
    """Read HTML file content."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def parse_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Parse a single HTML file and return listings.
    
    SRM v1.5: Parser only accepts html_text parameter.
    Returns dicts with all fields, no filtering applied.
    """
    html = read_file(filepath)
    listings = parser_listings.parse_listings_from_html(html_text=html)
    return listings


# =============================================================================
# FILTERING
# =============================================================================

def apply_filters(listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply eligibility filters.
    
    SRM v1.5: Parser does NOT filter - caller must filter based on dict fields.
    
    Filters:
    - Time: Only listings ending within MAX_TIME_HOURS (if configured)
    - Qty: Only listings with qty >= DEFAULT_MIN_QUANTITY (if configured)
    - Blacklist: Check filter_flags dict for blocked terms
    
    Returns only eligible listings.
    """
    eligible = []
    
    for listing in listings:
        # Time filter (if configured)
        if config.MAX_TIME_HOURS is not None:
            time_left = listing.get("time_left")
            if not time_left:
                continue  # No time data, skip
            
            # Parse time_left (e.g., "2h 15m")
            hours = parse_time_left_hours(time_left)
            if hours is None or hours > config.MAX_TIME_HOURS:
                continue
        
        # Qty filter (if configured)
        if config.DEFAULT_MIN_QUANTITY is not None:
            qty = listing.get("qty", 1)
            if qty < config.DEFAULT_MIN_QUANTITY:
                continue
        
        # Blacklist filter (check filter_flags)
        filter_flags = listing.get("filter_flags", {})
        if filter_flags:
            # If any filter flag is True, listing has a blocked term
            if any(filter_flags.values()):
                continue
        
        eligible.append(listing)
    
    return eligible


def parse_time_left_hours(time_left: str) -> float | None:
    """
    Parse time_left string to hours.
    
    Args:
        time_left: String like "2h 15m", "45m", "3d 2h", etc.
    
    Returns:
        Total hours as float, or None if unparseable
    """
    if not time_left:
        return None
    
    import re
    
    total_hours = 0.0
    
    # Match days
    days_match = re.search(r'(\d+)d', time_left)
    if days_match:
        total_hours += int(days_match.group(1)) * 24
    
    # Match hours
    hours_match = re.search(r'(\d+)h', time_left)
    if hours_match:
        total_hours += int(hours_match.group(1))
    
    # Match minutes
    minutes_match = re.search(r'(\d+)m', time_left)
    if minutes_match:
        total_hours += int(minutes_match.group(1)) / 60.0
    
    # Match seconds (if present)
    seconds_match = re.search(r'(\d+)s', time_left)
    if seconds_match:
        total_hours += int(seconds_match.group(1)) / 3600.0
    
    return total_hours if total_hours > 0 else None


# =============================================================================
# DEDUPLICATION
# =============================================================================

def dedupe_listings(listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate listings within a single scan cycle.
    
    Uses item_id as primary key, falls back to URL.
    """
    seen: Set[str] = set()
    unique = []
    
    for listing in listings:
        # Get dedup key
        key = listing.get("item_id") or listing.get("url") or listing.get("title")
        
        if key and key not in seen:
            seen.add(key)
            unique.append(listing)
    
    return unique


def load_seen_hits() -> Set[str]:
    """Load previously seen HIT item IDs."""
    if not os.path.exists(config.SEEN_HITS_PATH):
        return set()
    
    try:
        with open(config.SEEN_HITS_PATH, "r") as f:
            data = json.load(f)
            return set(data.get("seen_item_ids", []))
    except Exception:
        return set()


def save_seen_hits(seen: Set[str]):
    """Save seen HIT item IDs."""
    try:
        with open(config.SEEN_HITS_PATH, "w") as f:
            json.dump({"seen_item_ids": list(seen)}, f, indent=2)
    except Exception:
        pass


def filter_new_hits(hits: List[classifier.Evaluated], seen: Set[str]) -> List[classifier.Evaluated]:
    """
    Filter to only NEW hits (not previously seen).
    
    Returns:
        (new_hits, updated_seen_set)
    """
    new_hits = []
    
    for hit in hits:
        # Get item ID
        item_id = getattr(hit.listing, "item_id", None) or getattr(hit.listing, "url", None)
        
        if item_id and item_id not in seen:
            new_hits.append(hit)
            seen.add(item_id)
    
    return new_hits


# =============================================================================
# EMA CAPTURE
# =============================================================================

def capture_ema_updates(eligible: List[Dict[str, Any]], store: dict) -> int:
    """
    Capture EMA updates from eligible listings.
    
    Args:
        eligible: Listings that passed all filters
        store: Current price store state
    
    Returns:
        Number of listings captured
    
    SRM v1.5: Uses price_store.update_price() which enforces eligibility internally
    """
    captured = 0
    
    for listing in eligible:
        # Get listing data
        item_id = listing.get("item_id")
        if not item_id:
            continue
        
        total_price = listing.get("total_price")
        if total_price is None:
            continue
        
        bid_count = listing.get("bids", 0)
        qty = listing.get("qty", 1)
        title = listing.get("title", "")
        
        # Construct key (simple: use item_id for now)
        key = item_id
        
        # Update price store (eligibility checked internally)
        success = price_store.update_price(
            store=store,
            key=key,
            total_price=total_price,
            bid_count=bid_count,
            qty=qty,
            title=title
        )
        
        if success:
            captured += 1
    
    return captured


# =============================================================================
# CONSOLE OUTPUT
# =============================================================================

def format_timestamp() -> str:
    """Format current time as [HH:MM:SS]."""
    return datetime.now().strftime("[%H:%M:%S]")


def format_end_time(end_clock: str) -> str:
    """
    Format end time as H:MMa/p.
    
    Args:
        end_clock: Time string like "3:45 PM" or "11:30 AM"
    
    Returns:
        Formatted string like "3:45p" or "11:30a"
    """
    if not end_clock:
        return "???"
    
    # Remove spaces and convert to lowercase
    cleaned = end_clock.replace(" ", "").lower()
    
    return cleaned


def format_time_left(time_left: str, end_clock: str) -> str:
    """
    Format time remaining as "Xh Ym (ends H:MMa/p)".
    
    Args:
        time_left: Duration like "2h 15m"
        end_clock: End time like "3:45 PM"
    
    Returns:
        Formatted string per Contract v1.2 Section 1
    """
    if not time_left:
        time_left = "???"
    
    end_str = format_end_time(end_clock)
    
    return f"{time_left} (ends {end_str})"


def truncate_title(title: str, max_len: int = 50) -> str:
    """Truncate title to max length."""
    if len(title) <= max_len:
        return title
    return title[:max_len - 3] + "..."


def print_banner():
    """Print startup banner."""
    print("\n" + "=" * 70)
    print("EBAY OFFLINE SILVER MONITOR")
    print("=" * 70)
    print(f"Watch folder: {config.HTML_FOLDER_PATH}")
    print(f"Spot price: ${config.SPOT_PRICE:.2f}/oz")
    print(f"Pawn payout: {config.PAWN_PAYOUT_PCT}%")
    print(f"Min margin: {config.MIN_MARGIN_PCT}%")
    print(f"Max time: {config.MAX_TIME_HOURS}h" if config.MAX_TIME_HOURS else "Max time: None")
    print("=" * 70 + "\n")


def print_cycle_start(cycle_num: int):
    """Print cycle start message."""
    print(f"{format_timestamp()} Starting scan cycle #{cycle_num}...")


def print_config_block():
    """Print configuration block per Contract v1.2 Section 1."""
    print(f"  Spot price: ${config.SPOT_PRICE:.2f}/oz")
    print(f"  Pawn payout: {config.PAWN_PAYOUT_PCT}%")
    print(f"  Margin gates: {config.MIN_MARGIN_PCT}%-{config.MAX_MARGIN_PCT}%")
    
    if config.MAX_TIME_HOURS:
        print(f"  Time filter: {config.MAX_TIME_HOURS}h")
    else:
        print(f"  Time filter: None")


def print_counts(total_found: int, eligible_count: int, hit_count: int, new_hit_count: int):
    """
    Print counts line per Contract v1.2 Section 1 + Clarification #1.
    
    Format: Found: X | Eligible: Y | HITs: Z | New: W
    """
    print(f"Found: {total_found} | Eligible: {eligible_count} | HITs: {hit_count} | New: {new_hit_count}")


def print_file_table(filename: str, file_listings: List[classifier.Evaluated]):
    """
    Print per-file table per Contract v1.2 Section 1.
    
    Columns: Target | Found | Hit? | Price | QTY | Time Left | Title
    """
    if not file_listings:
        return
    
    file_count = len(file_listings)
    
    print(f"\n--- {filename} ({file_count} found) ---")
    
    # Header
    print(f"{'Target':<8}| {'Found':<6}| {'Hit?':<5}| {'Price':<10}| {'QTY':<4}| {'Time Left':<22}| {'Title'}")
    print("-" * 100)
    
    # Rows
    for evaluated in file_listings:
        listing = evaluated.listing
        
        # Target column (first) - static value "Silver"
        target_str = "Silver "
        
        # Found column (second) - total listings in this file  
        found_str = f"{file_count:5}"
        
        # Hit? column
        hit_str = "HIT " if evaluated.is_hit else "MISS"
        
        # Price column
        total_price = getattr(listing, "total_price", 0.0) or 0.0
        price_str = f"${total_price:>7.2f} "
        
        # QTY column
        silver_calc = evaluated.silver_calc
        qty = silver_calc.get("quantity", 1)
        qty_str = f"{qty:3} "
        
        # Time Left column
        time_left = getattr(listing, "time_left", "") or ""
        end_clock = getattr(listing, "end_clock", "") or ""
        time_str = format_time_left(time_left, end_clock)
        time_str = f"{time_str:<22}"
        
        # Title column
        title = getattr(listing, "title", "") or ""
        title_str = truncate_title(title, 50)
        
        print(f"{target_str}| {found_str}| {hit_str}| {price_str}| {qty_str}| {time_str}| {title_str}")


def print_email_status(sent: bool, new_count: int, subject: str = ""):
    """Print email status line."""
    if sent:
        print(f"\nEMAIL: sent ({new_count} new)")
        if subject:
            print(f"  Subject: {subject}")
    else:
        print(f"\nEMAIL: none (no new HITs)")


def print_cycle_separator():
    """Print blank line between cycles."""
    print()


# =============================================================================
# EMAIL
# =============================================================================

def get_earliest_end_time(hits: List[classifier.Evaluated]) -> str:
    """
    Get earliest end time from hits for email subject.
    
    Returns:
        Formatted time like "3:45p" or "11:30a"
    """
    if not hits:
        return "???"
    
    # Hits are already sorted by end_time_ts (earliest first)
    earliest = hits[0]
    end_clock = getattr(earliest.listing, "end_clock", "") or ""
    
    return format_end_time(end_clock)


def send_email_if_new_hits(new_hits: List[classifier.Evaluated]) -> bool:
    """
    Send email if new HITs exist.
    
    Returns:
        True if email sent, False otherwise
    
    Contract: v1.2 Section 2
    SRM v1.5: email_builder only has skeleton, must build body inline
    """
    if not new_hits:
        return False
    
    if not config.EMAIL_ENABLED:
        return False
    
    # Build subject (can use email_builder helper)
    earliest_time = get_earliest_end_time(new_hits)
    subject = email_builder.build_email_subject(
        earliest_time=earliest_time,
        new_count=len(new_hits)
    )
    
    # Build body (inline - email_builder only has skeleton)
    body = build_email_body_production(new_hits)
    
    # Send (implement inline SMTP)
    try:
        success = send_email_smtp(subject, body)
        return success
    except Exception as e:
        print(f"Email error: {e}")
        return False


def build_email_body_production(hits: List[classifier.Evaluated]) -> str:
    """
    Build production email body with actual HIT data.
    
    Format per Contract v1.2 Section 2:
    
    New HITs found: N
    [Entry 1]
    [Entry 2]
    ...
    Sent from eBay Offline Silver Monitor
    
    SRM v1.5: Must implement inline (email_builder only has skeleton)
    """
    lines = []
    
    # Header
    lines.append(f"New HITs found: {len(hits)}\n")
    
    # Entries
    for hit in hits:
        listing = hit.listing
        calc = hit.silver_calc
        
        # Title
        title = getattr(listing, "title", "") or "Unknown"
        lines.append(f"[HIT] {title}")
        
        # Price line
        total_price = getattr(listing, "total_price", 0.0) or 0.0
        qty = calc.get("quantity", 1)
        melt = calc.get("melt_value", 0.0)
        rec_max = calc.get("rec_max_total", 0.0)
        margin = calc.get("margin_pct", 0.0)
        
        lines.append(f"Price: ${total_price:.2f} | QTY: {qty} | Melt: ${melt:.2f} | Rec Max: ${rec_max:.2f} | Margin: {margin:.0f}%")
        
        # Time line
        time_left = getattr(listing, "time_left", "") or ""
        end_clock = getattr(listing, "end_clock", "") or ""
        end_str = format_end_time(end_clock)
        lines.append(f"Time: {time_left} (ends {end_str})")
        
        # Link
        url = getattr(listing, "url", "") or ""
        lines.append(f"Link: {url}")
        
        lines.append("")  # Blank line between entries
    
    # Footer
    lines.append("Sent from eBay Offline Silver Monitor")
    
    return "\n".join(lines)


def send_email_smtp(subject: str, body: str) -> bool:
    """
    Send email via SMTP.
    
    Contract: v1.2 Section 6 (SMTP settings)
    SRM v1.5: Must implement inline
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = config.FROM_EMAIL
        msg["To"] = ", ".join(config.TO_EMAILS)
        msg["Subject"] = subject
        
        msg.attach(MIMEText(body, "plain"))
        
        # Send
        with smtplib.SMTP(config.MAILGUN_SMTP_SERVER, config.MAILGUN_SMTP_PORT) as server:
            server.starttls()
            server.login(config.MAILGUN_SMTP_LOGIN, config.MAILGUN_SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"SMTP error: {e}")
        return False


# =============================================================================
# MAIN SCAN CYCLE
# =============================================================================

def run_once() -> dict:
    """
    Single scan cycle.
    
    Returns:
        dict with keys:
            - total_found: int
            - eligible_count: int
            - hit_count: int
            - new_hit_count: int
            - files_processed: int
            - all_evaluated: List[Evaluated] (all listings, grouped by file)
            - new_hits: List[Evaluated] (new HITs only)
    """
    # Discover HTML files
    html_files = discover_html_files()
    
    if not html_files:
        return {
            "total_found": 0,
            "eligible_count": 0,
            "hit_count": 0,
            "new_hit_count": 0,
            "files_processed": 0,
            "all_evaluated": [],
            "new_hits": []
        }
    
    # Parse all files
    all_listings = []
    file_groups = {}  # filename -> list of listings
    
    for filepath in html_files:
        filename = os.path.basename(filepath)
        
        try:
            listings = parse_file(filepath)
            all_listings.extend(listings)
            file_groups[filename] = listings
        except Exception as e:
            print(f"Error parsing {filename}: {e}")
            continue
    
    total_found = len(all_listings)
    
    # Apply filters
    eligible = apply_filters(all_listings)
    eligible_count = len(eligible)
    
    # Deduplicate
    eligible = dedupe_listings(eligible)
    
    # EMA capture (before classification)
    store = price_store.load_store()
    captured = capture_ema_updates(eligible, store)
    if captured > 0:
        price_store.save_store(store)
    
    # Convert dicts to objects (ListingAdapter)
    obj_listings = [ListingAdapter(d) for d in eligible]
    
    # Classify
    evaluated = classifier.classify_listings(obj_listings)
    
    # Extract HITs
    all_hits = [e for e in evaluated if e.is_hit]
    hit_count = len(all_hits)
    
    # Filter to NEW hits only (cross-run deduplication)
    seen = load_seen_hits()
    new_hits = filter_new_hits(all_hits, seen)
    new_hit_count = len(new_hits)
    
    # Save updated seen set
    save_seen_hits(seen)
    
    # Group evaluated by file for console output
    file_evaluated = {}
    for filename, file_listings in file_groups.items():
        # Find evaluated objects for this file's listings
        file_item_ids = {d.get("item_id") or d.get("url") for d in file_listings}
        file_eval = [e for e in evaluated if (getattr(e.listing, "item_id", None) or getattr(e.listing, "url", None)) in file_item_ids]
        file_evaluated[filename] = file_eval
    
    # Delete processed HTML files if configured
    if config.DELETE_PROCESSED_HTML:
        for filepath in html_files:
            try:
                os.remove(filepath)
            except Exception:
                pass
    
    return {
        "total_found": total_found,
        "eligible_count": eligible_count,
        "hit_count": hit_count,
        "new_hit_count": new_hit_count,
        "files_processed": len(html_files),
        "file_evaluated": file_evaluated,
        "new_hits": new_hits
    }


# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    """
    Main loop - continuous monitoring.
    
    Contract: v1.2 Section 1 (Console UX)
    """
    print_banner()
    
    cycle_num = 0
    
    while True:
        cycle_num += 1
        
        # Print cycle start
        print_cycle_start(cycle_num)
        print_config_block()
        
        # Run scan cycle
        result = run_once()
        
        # Print counts
        print_counts(
            total_found=result["total_found"],
            eligible_count=result["eligible_count"],
            hit_count=result["hit_count"],
            new_hit_count=result["new_hit_count"]
        )
        
        # Print per-file tables
        for filename, file_listings in result.get("file_evaluated", {}).items():
            print_file_table(filename, file_listings)
        
        # Send email if new HITs
        email_sent = send_email_if_new_hits(result["new_hits"])
        
        # Print email status
        if email_sent:
            earliest_time = get_earliest_end_time(result["new_hits"])
            subject = email_builder.build_email_subject(
                earliest_time=earliest_time,
                new_count=result["new_hit_count"]
            )
            print_email_status(True, result["new_hit_count"], subject)
        else:
            print_email_status(False, result["new_hit_count"])
        
        # Print cycle separator
        print_cycle_separator()
        
        # Sleep
        sleep_time = config.DEFAULT_CHECK_INTERVAL_MIN * 60
        jitter = random.uniform(0, config.SLEEP_JITTER_SEC)
        total_sleep = sleep_time + jitter
        
        print(f"Sleep: {total_sleep:.0f}s\n")
        time.sleep(total_sleep)


if __name__ == "__main__":
    main()


#EndOfFile
