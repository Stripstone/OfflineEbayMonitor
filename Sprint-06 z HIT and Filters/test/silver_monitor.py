# silver_monitor.py
"""
SILVER MONITOR — Runtime Orchestrator

Sprint 05.5 scope: Basic end-to-end monitor
- HTML discovery and parsing
- EMA capture
- Melt classification
- Email sending
- Console output

Deferred to Sprint 06.x:
- Diagnostics (06.1)
- Filter words (06.2)
- PROS classification (06.3)
"""

from __future__ import annotations

import json
import os
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Set, Tuple

import config
import classifier
import parser_listings
import price_store


# =============================================================================
# State Management
# =============================================================================

def load_seen_hits() -> Set[str]:
    """Load seen HIT keys from disk for cross-run deduplication."""
    if not os.path.exists(config.SEEN_HITS_PATH):
        return set()
    try:
        with open(config.SEEN_HITS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except Exception:
        return set()


def save_seen_hits(seen: Set[str]) -> None:
    """Save seen HIT keys to disk."""
    try:
        with open(config.SEEN_HITS_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(list(seen)), f, indent=2)
    except Exception:
        pass


def get_listing_key(listing: Any) -> str:
    """Generate unique key for a listing (item_id > url > title)."""
    item_id = getattr(listing, "item_id", None)
    if item_id:
        return f"id:{item_id}"
    
    url = getattr(listing, "url", None)
    if url:
        return f"url:{url}"
    
    title = getattr(listing, "title", "")
    return f"title:{title}"


# =============================================================================
# HTML Discovery
# =============================================================================

def discover_html_files() -> List[str]:
    """
    Discover HTML files in configured folder.
    
    Returns list of (filename, full_path) tuples for files matching
    SILVER_FILENAME_KEYWORDS.
    """
    if not os.path.exists(config.HTML_FOLDER_PATH):
        return []
    
    files = []
    keywords = [k.lower() for k in config.SILVER_FILENAME_KEYWORDS]
    
    for filename in os.listdir(config.HTML_FOLDER_PATH):
        if not filename.lower().endswith(".html"):
            continue
        
        # Check if filename contains any silver keyword
        fn_lower = filename.lower()
        if any(kw in fn_lower for kw in keywords):
            full_path = os.path.join(config.HTML_FOLDER_PATH, filename)
            files.append((filename, full_path))
    
    return files


# =============================================================================
# Parsing
# =============================================================================

def parse_file(filename: str, filepath: str) -> List[Dict]:
    """Parse single HTML file and return listing dicts."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        
        # Use parser_listings directly (returns list of dicts)
        listings = parser_listings.parse_listings_from_html(html)
        return listings
    except Exception as e:
        print(f"  ERROR parsing {filename}: {e}")
        return []


# =============================================================================
# Filtering
# =============================================================================

def apply_filters(listings: List[Dict]) -> List[Dict]:
    """
    Apply filters: qty, blacklist, time window.
    
    Sprint 05.5 scope: Basic filters only
    Sprint 06.2: Filter word gates
    """
    filtered = []
    
    for listing in listings:
        # Quantity filter
        qty = listing.get("qty", 1)
        if config.DEFAULT_MIN_QUANTITY is not None:
            if qty < config.DEFAULT_MIN_QUANTITY:
                continue
        
        # Blacklist filter
        if config.DEFAULT_BLACKLIST:
            title = (listing.get("title", "") or "").lower()
            if any(term.lower() in title for term in config.DEFAULT_BLACKLIST):
                continue
        
        # Time window filter
        if config.MAX_TIME_HOURS is not None:
            end_ts = listing.get("end_time_ts")
            if end_ts is not None:
                hours_left = (float(end_ts) - time.time()) / 3600.0
                if hours_left > config.MAX_TIME_HOURS or hours_left < 0:
                    continue
        
        filtered.append(listing)
    
    return filtered


# =============================================================================
# EMA Capture
# =============================================================================

def capture_ema_updates(listings: List[Dict], store: Dict) -> int:
    """
    Capture EMA updates for eligible listings.
    
    Per Contract v1.2 Section 7:
    - Write-time only
    - +8% bump applied once at capture
    - One capture per listing per scan
    - One capture per benchmark key per scan
    
    Eligibility:
    - qty == 1
    - bids >= 1
    - NOT lot/roll/set/face value
    - NOT album/folder/book/"NO COINS"
    - NOT accessory (money clip, keychain, pendant, jewelry, cutout)
    - NOT damaged (holed, hole, pierced, drilled)
    
    Returns: count of updates applied
    """
    if not config.PRICE_CAPTURE_ONLY_IF_BIDS:
        return 0
    
    captured_keys = set()
    update_count = 0
    
    for listing in listings:
        # Basic gates
        qty = listing.get("qty", 1)
        bids = listing.get("bids", 0)
        total_price = listing.get("total_price")
        title = listing.get("title", "")
        
        if qty != 1:
            continue
        if bids < 1:
            continue
        if total_price is None or total_price <= 0:
            continue
        
        # Time gate (capture only if ending soon)
        if config.PRICE_CAPTURE_MAX_MINUTES is not None:
            end_ts = listing.get("end_time_ts")
            if end_ts is not None:
                mins_left = (float(end_ts) - time.time()) / 60.0
                if mins_left > config.PRICE_CAPTURE_MAX_MINUTES or mins_left < 0:
                    continue
        
        # Generate benchmark key (simplified for Sprint 05.5)
        # Full implementation would extract coin_type|year|mint
        # For now, use title as key (Sprint 06.3 will enhance)
        key = title.strip()[:100]  # Truncate for safety
        
        # One capture per key per scan
        if key in captured_keys:
            continue
        
        # Attempt update
        success = price_store.update_price(
            store=store,
            key=key,
            total_price=float(total_price),
            bid_count=int(bids),
            qty=int(qty),
            title=str(title),
        )
        
        if success:
            captured_keys.add(key)
            update_count += 1
    
    return update_count


# =============================================================================
# Deduplication
# =============================================================================

def deduplicate_by_key(listings: List[Dict]) -> List[Dict]:
    """Intra-run deduplication: remove duplicate listings in same scan."""
    seen = set()
    unique = []
    
    for listing in listings:
        # Generate key using dict access
        item_id = listing.get("item_id")
        if item_id:
            key = f"id:{item_id}"
        else:
            url = listing.get("url")
            if url:
                key = f"url:{url}"
            else:
                title = listing.get("title", "")
                key = f"title:{title}"
        
        if key not in seen:
            seen.add(key)
            unique.append(listing)
    
    return unique


def select_new_hits(evaluated: List[classifier.Evaluated], seen_hits: Set[str]) -> List[classifier.Evaluated]:
    """Cross-run deduplication: select only new HITs not seen before."""
    new_hits = []
    
    for e in evaluated:
        if not e.is_hit:
            continue
        
        key = get_listing_key(e.listing)
        if key not in seen_hits:
            new_hits.append(e)
            seen_hits.add(key)
    
    return new_hits


# =============================================================================
# Dict to Object Adapter (for classifier interface)
# =============================================================================

class ListingAdapter:
    """Simple adapter to convert dict to object for classifier interface."""
    def __init__(self, data: Dict):
        self._data = data
    
    def __getattr__(self, name):
        return self._data.get(name)


# =============================================================================
# Email
# =============================================================================

def build_email_body_simple(hits: List[classifier.Evaluated]) -> str:
    """
    Build simple email body for Sprint 05.5.
    
    Note: email_builder.py exists but may expect different structure.
    Implement basic version here; Sprint 06.x will enhance.
    """
    lines = []
    lines.append("EBAY OFFLINE SILVER HITS")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Spot | Pawn: ${config.SPOT_PRICE:.2f} | {config.PAWN_PAYOUT_PCT:.1f}%")
    lines.append(f"Target margin: {config.MIN_MARGIN_PCT:.1f}%–{config.MAX_MARGIN_PCT:.1f}%")
    lines.append("")
    lines.append(f"Total HITs: {len(hits)}")
    lines.append("-" * 60)
    lines.append("")
    
    for i, e in enumerate(hits, 1):
        listing = e.listing
        calc = e.silver_calc
        
        title = getattr(listing, "title", None)
        title_str = title if title else "NO TITLE"
        lines.append(f"#{i} {title_str}")
        lines.append("")
        
        # Defensive None-checking for all values
        profit = calc.get("profit")
        profit_str = f"${profit:.2f}" if profit is not None else "$--.--"
        
        margin = calc.get("margin_pct")
        margin_str = f"{margin:.1f}%" if margin is not None else "--.-%"
        
        lines.append(f"Current Profit (pawn): {profit_str} ({margin_str} margin vs pawn)")
        
        rec_item = calc.get("rec_max_item")
        rec_item_str = f"${rec_item:.2f}" if rec_item is not None else "$--.--"
        
        rec_total = calc.get("rec_max_total")
        rec_total_str = f"${rec_total:.2f}" if rec_total is not None else "$--.--"
        
        lines.append(f"RecMaxBid: {rec_item_str} ({rec_total_str} total incl. ship)")
        
        total_price = getattr(listing, "total_price", None)
        total_str = f"${total_price:.2f}" if total_price is not None else "$--.--"
        
        lines.append(f"Current Total: {total_str}")
        lines.append("")
        
        qty = calc.get("quantity", 1)
        oz_per = calc.get("oz_per_coin")
        oz_per_str = f"{oz_per:.5f}" if oz_per is not None else "0.00000"
        
        total_oz = calc.get("total_oz")
        total_oz_str = f"{total_oz:.2f}" if total_oz is not None else "--.--"
        
        lines.append(f"Qty: {qty} | oz/coin: {oz_per_str} | Total oz: {total_oz_str}")
        
        melt_val = calc.get("melt_value")
        melt_val_str = f"${melt_val:.2f}" if melt_val is not None else "$--.--"
        
        melt_payout = calc.get("melt_payout")
        melt_payout_str = f"${melt_payout:.2f}" if melt_payout is not None else "$--.--"
        
        lines.append(f"Melt | Pawn payout: {melt_val_str} | {melt_payout_str}")
        
        time_left = getattr(listing, "time_left", None)
        time_left_str = time_left if time_left else "--:--"
        
        end_clock = getattr(listing, "end_clock", None)
        end_clock_str = end_clock if end_clock else ""
        
        if end_clock_str:
            lines.append(f"Time left: {time_left_str} ({end_clock_str})")
        else:
            lines.append(f"Time left: {time_left_str}")
        
        lines.append("")
        
        url = getattr(listing, "url", None)
        if url:
            lines.append(f"Link to Listing: {url}")
        
        lines.append("-" * 60)
    
    lines.append("")
    lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return "\n".join(lines)


def get_earliest_time_str(hits: List[classifier.Evaluated]) -> str:
    """Get earliest end time as HH:MM AM/PM string."""
    if not hits:
        return "--:--"
    
    earliest = hits[0]  # Already sorted by end_time_ts
    end_ts = getattr(earliest.listing, "end_time_ts", None)
    
    if end_ts is None:
        return "--:--"
    
    try:
        dt = datetime.fromtimestamp(float(end_ts))
        return dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return "--:--"


def send_email(subject: str, body: str) -> bool:
    """Send email via SMTP."""
    if not config.EMAIL_ENABLED:
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = config.FROM_EMAIL
        msg["To"] = ", ".join(config.TO_EMAILS)
        msg["Subject"] = subject
        
        msg.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP(config.MAILGUN_SMTP_SERVER, config.MAILGUN_SMTP_PORT) as server:
            server.starttls()
            server.login(config.MAILGUN_SMTP_LOGIN, config.MAILGUN_SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"  EMAIL ERROR: {e}")
        return False


# =============================================================================
# Console Output
# =============================================================================

def format_time_left_contract(listing_data: Dict) -> str:
    """
    Format time left per Contract v1.2 Section 1.
    
    Required format: "3h42m (Today 11:18 PM)"
    NOT: "3h42m left ((Today 11:18 PM))"
    
    Remove "left" suffix and extra parentheses.
    """
    time_left = listing_data.get("time_left")
    time_left_str = time_left if time_left else "--:--"
    
    # Remove " left" suffix if present
    if time_left_str.endswith(" left"):
        time_left_str = time_left_str[:-5]
    
    end_clock = listing_data.get("end_clock")
    end_clock_str = end_clock if end_clock else ""
    
    # Remove extra parentheses from end_clock if present
    if end_clock_str.startswith("(") and end_clock_str.endswith(")"):
        end_clock_str = end_clock_str[1:-1]
    
    if end_clock_str:
        return f"{time_left_str} ({end_clock_str})"
    return time_left_str


def print_cycle_header(cycle_num: int):
    """Print cycle start (Sprint 05.5 format)."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting scan cycle #{cycle_num}...")
    print(f"  Spot price: ${config.SPOT_PRICE:.2f}/oz")
    print(f"  Pawn payout: {config.PAWN_PAYOUT_PCT}%")
    print(f"  Margin gates: {config.MIN_MARGIN_PCT}%-{config.MAX_MARGIN_PCT}%")
    if config.MAX_TIME_HOURS:
        print(f"  Time filter: {config.MAX_TIME_HOURS}h")
    else:
        print(f"  Time filter: None")


def print_cycle_results(
    cycle_num: int,
    files_processed: int,
    total_found: int,
    eligible_count: int,
    hit_count: int,
    new_hit_count: int,
    file_results: List[Tuple[str, List[classifier.Evaluated], int]],
):
    """Print cycle results per Contract v1.2 Section 1."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"Found: {total_found} | Eligible: {eligible_count} | HITs: {hit_count} | New: {new_hit_count}")
    print()
    
    for filename, evaluated, file_count in file_results:
        if not evaluated:
            continue
        
        print(f"=== {filename} ===")
        
        # Print table header per Contract v1.2 Section 1
        # Columns: Target | Found | Hit? | Price | QTY | Time Left | Title
        # Target = static "Silver" (no filename detection per scope correction)
        print("Target  | Found | Hit? | Price    | QTY | Time Left              | Title")
        print("-" * 100)
        
        for e in evaluated:
            listing = e.listing
            calc = e.silver_calc
            
            # Target column (first) - static value "Silver"
            target_str = "Silver "
            
            # Found column (second) - total listings in this file
            found_str = f"{file_count:5}"
            
            # Hit? column (third)
            hit_str = "HIT " if e.is_hit else "MISS"
            
            # Price column (fourth)
            total_price = getattr(listing, "total_price", None)
            price_str = f"${total_price:.2f}" if total_price is not None else "$--.--"
            
            # QTY column (fifth)
            qty = calc.get("quantity", 1)
            qty_str = f"{qty:3}"
            
            # Time Left column (sixth) - contract format
            # Access dict directly since listing is adapter
            listing_dict = listing._data if isinstance(listing, ListingAdapter) else {}
            time_str = format_time_left_contract(listing_dict)
            
            # Title column (seventh)
            title = getattr(listing, "title", None)
            title_str = (title[:50] if title else "NO TITLE")
            
            print(f"{target_str} | {found_str} | {hit_str} | {price_str:>8} | {qty_str} | {time_str:22} | {title_str}")
        
        print()


# =============================================================================
# Main Scan Logic
# =============================================================================

def run_once(cycle_num: int, seen_hits: Set[str]) -> Tuple[int, int]:
    """
    Single scan cycle.
    
    Returns: (hit_count, new_hit_count)
    """
    print_cycle_header(cycle_num)
    
    # 1. Discover HTML files
    html_files = discover_html_files()
    
    if not html_files:
        print("No HTML files found.")
        return 0, 0
    
    # 2. Parse listings (once per file) - returns list of dicts
    all_listings = []
    file_listing_map = {}  # Track which listings came from which file
    file_count_map = {}    # Track total count per file for "Found" column
    
    for filename, filepath in html_files:
        listings = parse_file(filename, filepath)
        
        if listings:
            all_listings.extend(listings)
            file_listing_map[filename] = listings
            file_count_map[filename] = len(listings)
            
            # Delete if configured
            if config.DELETE_PROCESSED_HTML:
                try:
                    os.remove(filepath)
                except Exception:
                    pass
    
    total_found = len(all_listings)
    
    # Track ineligible count for diagnostics (Sprint 06.1)
    if config.DEBUG_DIAGNOSTICS:
        import diagnostics
        # Reset state before this run
        classifier.reset_diagnostics_state()
        # Track total seen
        classifier._diagnostics["total_listings_seen"] = total_found
    
    # 3. Filter
    eligible = apply_filters(all_listings)
    eligible_count = len(eligible)
    
    # Track ineligible for diagnostics (Sprint 06.1)
    if config.DEBUG_DIAGNOSTICS:
        ineligible_count = total_found - eligible_count
        classifier._diagnostics["ineligible_count"] = ineligible_count
    
    # 4. EMA capture
    store = price_store.load_store()
    captured = capture_ema_updates(eligible, store)
    if captured > 0:
        price_store.save_store(store)
    
    # 5. Deduplicate (intra-run)
    unique = deduplicate_by_key(eligible)
    
    # 6. Convert dicts to ListingAdapter objects for classifier
    adapted = [ListingAdapter(lst) for lst in unique]
    
    # 7. Classify
    evaluated = classifier.classify_listings(adapted, diagnostics_enabled=config.DEBUG_DIAGNOSTICS)
    
    # Write diagnostics (Sprint 06.1)
    if config.DEBUG_DIAGNOSTICS:
        import diagnostics
        diag_data = classifier.get_diagnostics()
        diagnostics.write_diagnostics(diag_data)
    
    # 8. Select HITs
    hits = [e for e in evaluated if e.is_hit]
    hit_count = len(hits)
    
    # 9. Deduplicate new HITs (cross-run)
    new_hits = select_new_hits(hits, seen_hits)
    new_hit_count = len(new_hits)
    
    # Build file results for console output (using already parsed data)
    file_results = []
    for filename in file_listing_map:
        file_listings = file_listing_map[filename]
        # Match by comparing underlying dict data
        file_eval = []
        for e in evaluated:
            if isinstance(e.listing, ListingAdapter):
                if e.listing._data in file_listings:
                    file_eval.append(e)
        
        file_total_count = file_count_map[filename]
        if file_eval:
            file_results.append((filename, file_eval, file_total_count))
    
    # 10. Console output
    print_cycle_results(
        cycle_num=cycle_num,
        files_processed=len(html_files),
        total_found=total_found,
        eligible_count=eligible_count,
        hit_count=hit_count,
        new_hit_count=new_hit_count,
        file_results=file_results,
    )
    
    # 11. Email (if new HITs)
    if new_hit_count > 0:
        earliest_time = get_earliest_time_str(new_hits)
        subject = f"{earliest_time} Offline eBay Silver HITS ({new_hit_count} new)"
        body = build_email_body_simple(new_hits)
        
        success = send_email(subject, body)
        if success:
            print(f"EMAIL: sent ({new_hit_count} new) | Subject: {subject}")
        else:
            print(f"EMAIL: FAILED to send ({new_hit_count} new)")
    else:
        print("EMAIL: no new HITs, not sent")
    
    print()
    
    return hit_count, new_hit_count


# =============================================================================
# Main Loop
# =============================================================================

def main():
    """Main loop - continuous monitoring."""
    print("\n" + "=" * 70)
    print("EBAY OFFLINE SILVER MONITOR")
    print("=" * 70)
    print(f"Watching: {config.HTML_FOLDER_PATH}")
    print(f"Check interval: {config.DEFAULT_CHECK_INTERVAL_MIN} minutes")
    print("=" * 70)
    
    
    # Reset diagnostics on program start (Sprint 06.1)
    if config.DEBUG_DIAGNOSTICS:
        import diagnostics
        diagnostics.reset_diagnostics()
    seen_hits = load_seen_hits()
    cycle_num = 0
    
    while True:
        cycle_num += 1
        
        try:
            hit_count, new_hit_count = run_once(cycle_num, seen_hits)
            
            # Save seen hits after each cycle
            save_seen_hits(seen_hits)
            
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            save_seen_hits(seen_hits)
            break
        except Exception as e:
            print(f"\nERROR in cycle #{cycle_num}: {e}")
            import traceback
            traceback.print_exc()
        
        # Sleep
        sleep_sec = int(config.DEFAULT_CHECK_INTERVAL_MIN * 60)
        print(f"Waiting {sleep_sec} seconds...\n")
        time.sleep(sleep_sec)


if __name__ == "__main__":
    main()


#EndOfFile
