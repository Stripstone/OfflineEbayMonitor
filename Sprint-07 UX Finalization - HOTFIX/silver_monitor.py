# silver_monitor.py
"""
SILVER MONITOR â€” Runtime Orchestrator

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
    """Parse single HTML file and return listing dicts with source filename."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        
        # Use parser_listings directly (returns list of dicts)
        listings = parser_listings.parse_listings_from_html(html)
        
        # Attach source filename to each listing (Issue #1 fix)
        for listing in listings:
            listing["source_filename"] = filename
        
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
    Sprint 07 fix: Parse time_left string for time filter
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
        
        # Time window filter (parse time_left string)
        if config.MAX_TIME_HOURS is not None:
            time_left = listing.get("time_left")
            if time_left:
                import utils
                minutes = utils.parse_time_left_to_minutes(time_left)
                if minutes is not None:
                    hours_left = minutes / 60.0
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
    OBSOLETE (Sprint 07): Replaced by email_builder.build_email_body()
    
    This function is no longer used. Email formatting moved to email_builder.py
    per Contract v1.3.1 Section 2.
    
    Kept for reference only.
    """
    raise NotImplementedError("Use email_builder.build_email_body() instead")


def get_earliest_time_str(hits: List[classifier.Evaluated]) -> str:
    """
    OBSOLETE (Sprint 07): Replaced by email_builder.extract_earliest_time()
    
    This function is no longer used. Email subject line construction
    moved to email_builder.py per Contract v1.3.1 Section 2.
    
    Kept for reference only.
    """
    raise NotImplementedError("Use email_builder.build_email_subject() instead")


def send_email(subject: str, body: str) -> bool:
    """Send email via SMTP."""
    if not config.EMAIL_ENABLED:
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = config.FROM_EMAIL
        msg["To"] = ", ".join(config.TO_EMAILS)
        msg["Subject"] = subject
        
        msg.attach(MIMEText(body, "html"))
        
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
    
    # Initialize diagnostics
    if config.DEBUG_DIAGNOSTICS:
        import diagnostics
        classifier.reset_diagnostics_state()
    
    # 2. Process each file individually (parse -> filter -> classify -> print)
    all_evaluated = []
    all_eligible_listings = []
    total_found = 0
    eligible_count = 0
    
    for filename, filepath in html_files:
        # Parse
        listings = parse_file(filename, filepath)
        if not listings:
            continue
        
        file_found = len(listings)
        total_found += file_found
        
        # Filter
        filtered = apply_filters(listings)
        eligible_count += len(filtered)
        all_eligible_listings.extend(filtered)
        
        # Convert to objects and classify
        adapted = [ListingAdapter(lst) for lst in filtered]
        evaluated = classifier.classify_listings(adapted, diagnostics_enabled=config.DEBUG_DIAGNOSTICS)
        
        # Print this file's results immediately
        if evaluated:
            print(f"=== {filename} ({file_found} found) ===")
            print("Target  | Found | Hit? | Price    | QTY | Time Left              | Title")
            print("-" * 100)
            
            for e in evaluated:
                listing = e.listing
                calc = e.silver_calc
                
                target_str = "Silver "
                found_str = f"{file_found:5}"
                hit_str = "HIT " if e.is_hit else "MISS"
                
                total_price = getattr(listing, "total_price", None)
                price_str = f"${total_price:.2f}" if total_price is not None else "$--.--"
                
                qty = calc.get("quantity", 1)
                qty_str = f"{qty:3}"
                
                listing_dict = listing._data if isinstance(listing, ListingAdapter) else {}
                time_str = format_time_left_contract(listing_dict)
                
                title = getattr(listing, "title", None)
                title_str = (title[:50] if title else "NO TITLE")
                
                print(f"{target_str} | {found_str} | {hit_str} | {price_str:>8} | {qty_str} | {time_str:22} | {title_str}")
            
            print()
        
        all_evaluated.extend(evaluated)
    
    # Track diagnostics totals
    if config.DEBUG_DIAGNOSTICS:
        classifier._diagnostics["total_listings_seen"] = total_found
        ineligible_count = total_found - eligible_count
        classifier._diagnostics["ineligible_count"] = ineligible_count
    
    # EMA capture
    store = price_store.load_store()
    captured = capture_ema_updates(all_eligible_listings, store)
    if captured > 0:
        price_store.save_store(store)
    
    # 3. Deduplicate and count HITs
    hits = [e for e in all_evaluated if e.is_hit]
    hit_count = len(hits)
    
    # Deduplicate new HITs (cross-run)
    new_hits = select_new_hits(hits, seen_hits)
    new_hit_count = len(new_hits)
    
    # 4. Print summary
    print(f"Found: {total_found} | Eligible: {eligible_count} | HITs: {hit_count} | New: {new_hit_count}")
    print()
    
    # 5. Diagnostics
    if config.DEBUG_DIAGNOSTICS:
        import diagnostics
        diag_data = classifier.get_diagnostics()
        diagnostics.write_diagnostics(diag_data)
    
    # 6. Email (if new HITs)
    if new_hit_count > 0:
        import email_builder
        subject = email_builder.build_email_subject(new_hits)
        body = email_builder.build_email_body(new_hits)
        
        success = send_email(subject, body)
        if success:
            print(f"EMAIL: sent ({new_hit_count} new) | Subject: {subject}")
        else:
            print(f"EMAIL: FAILED to send ({new_hit_count} new)")
    else:
        print("EMAIL: no new HITs, not sent")
    
    print()
    
    # 7. Delete processed files (after all output complete)
    if config.DELETE_PROCESSED_HTML:
        for filename, filepath in html_files:
            try:
                os.remove(filepath)
            except Exception:
                pass
    
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
