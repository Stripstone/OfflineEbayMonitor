# email_builder.py
"""
Offline eBay Silver Monitor — Email Builder (Sprint 07)

Sprint 07 scope:
- Production-ready email format per Contract v1.3.1 Section 2
- Complete melt entry format with all fields
- PROS entry format with placeholders
- Entry sorting (earliest first) and sequential numbering
- Link construction (eBay listing, eBay sales, CoinBook)

Contract: v1.3.1 Section 2 (Email UX Contract)
SRM: v1.4

#EndOfFile
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, List
from urllib.parse import quote_plus

import config


# =============================================================================
# Link Construction (Contract Section 4)
# =============================================================================

def construct_ebay_listing_url(item_id: str) -> str:
    """
    Construct eBay listing URL.
    
    Contract v1.3.1 Section 4:
    https://www.ebay.com/itm/<item_id>
    """
    if not item_id:
        return "[No item ID]"
    return f"https://www.ebay.com/itm/{item_id}"


def construct_ebay_sales_url(title: str) -> str:
    """
    Construct eBay sold listings search URL.
    
    Contract v1.3.1 Section 4:
    https://www.ebay.com/sch/i.html?_nkw=<series>+<year>+<mint>&LH_Sold=1&LH_Complete=1
    
    Best-effort extraction of series, year, mint from title.
    If extraction fails, use generic title search.
    """
    if not title:
        return "[No title]"
    
    # Extract series, year, mint (best effort)
    t = title.lower()
    
    # Series detection
    series = ""
    if "morgan" in t and "dollar" in t:
        series = "Morgan Dollar"
    elif "peace" in t and "dollar" in t:
        series = "Peace Dollar"
    elif "kennedy" in t:
        series = "Kennedy Half"
    elif "walking" in t and "liberty" in t:
        series = "Walking Liberty Half"
    elif "franklin" in t:
        series = "Franklin Half"
    elif "barber" in t:
        series = "Barber Half"
    elif "seated" in t:
        series = "Seated Liberty Half"
    
    # Year extraction (4-digit year 1794-2099)
    year = ""
    year_match = re.search(r'\b(1[7-9]\d{2}|20\d{2})\b', title)
    if year_match:
        year = year_match.group(1)
    
    # Mint extraction (after year if possible)
    mint = ""
    if year:
        # Look for mint mark after year
        mint_pattern = r'\b' + re.escape(year) + r'\s*([PDSOC]{1,2})\b'
        mint_match = re.search(mint_pattern, title, re.IGNORECASE)
        if mint_match:
            mint = mint_match.group(1).upper()
    
    # Build search query
    if series or year:
        parts = []
        if series:
            parts.append(series)
        if year:
            parts.append(year)
        if mint:
            parts.append(mint)
        search_query = quote_plus(" ".join(parts))
    else:
        # Fallback: use first 50 chars of title
        search_query = quote_plus(title[:50])
    
    return f"https://www.ebay.com/sch/i.html?_nkw={search_query}&LH_Sold=1&LH_Complete=1"


def construct_coinbook_url() -> str:
    """
    Construct CoinBook URL (placeholder for Sprint 07).
    
    Contract v1.3.1 Section 4:
    https://www.pcgs.com/coinfacts/<series-slug>
    
    Sprint 07: Return placeholder
    Sprint 08: Implement real series slug logic
    """
    return "[Placeholder - CoinBook]"


# =============================================================================
# Helper Functions
# =============================================================================

def extract_earliest_time(hits: List[Any]) -> str:
    """
    Extract earliest end time as h:mm AM/PM format.
    
    Contract v1.3.1 Section 2:
    Subject line format: [A1] = Earliest listing time (h:mm AM/PM format)
    
    Args:
        hits: List of Evaluated objects (already sorted by end_time_ts)
    
    Returns:
        Time string like "3:45 PM" or "--:--" if unavailable
    """
    if not hits:
        return "--:--"
    
    earliest = hits[0]
    
    # Try end_time_ts first (unix timestamp)
    end_ts = getattr(earliest.listing, "end_time_ts", None)
    if end_ts is not None:
        try:
            dt = datetime.fromtimestamp(float(end_ts))
            return dt.strftime("%I:%M %p").lstrip("0")
        except Exception:
            pass
    
    # Fallback: parse end_clock string "(Today 11:16 AM)" or similar
    end_clock = getattr(earliest.listing, "end_clock", None)
    if end_clock:
        # Extract time from formats like "(Today 11:16 AM)" or "(Tomorrow 3:45 PM)"
        import re
        match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', str(end_clock), re.IGNORECASE)
        if match:
            time_str = match.group(1).strip()
            # Strip leading zero from hour
            return re.sub(r'^0', '', time_str)
    
    return "--:--"


def cleanup_title(title: str) -> str:
    """
    Remove eBay parser artifacts from title.
    
    Strips: "Opens in a new window or tab"
    """
    if not title:
        return title
    
    # Strip common eBay artifacts
    artifacts = [
        "Opens in a new window or tab",
        "opens in a new window or tab",
    ]
    
    result = title
    for artifact in artifacts:
        result = result.replace(artifact, "")
    
    # Clean up extra whitespace
    result = " ".join(result.split())
    
    return result.strip()


def format_header_section() -> str:
    """
    Format email header section.
    
    Contract v1.3.1 Section 2:
    EBAY OFFLINE SILVER HITS
    ================================
    Spot: [A2] | Pawn: [A3]%
    Bid offset: [A4]
    Target margin: [A5-min]%—[A5-max]%
    Max time left: [A7] hours
    Total HITs: [A6]
    """
    lines = []
    
    # Title
    lines.append("EBAY OFFLINE SILVER HITS")
    lines.append("=" * 32)
    
    # Line 1: Spot | Pawn
    spot = config.SPOT_PRICE
    pawn_pct = config.PAWN_PAYOUT_PCT
    lines.append(f"Spot: ${spot:.2f} | Pawn: {pawn_pct:.0f}%")
    
    # Line 2: Bid offset
    bid_offset = getattr(config, "BID_OFFSET_USD", 0.0)
    lines.append(f"Bid offset: ${bid_offset:.2f}")
    
    # Line 3: Target margin (with em dash)
    min_margin = config.MIN_MARGIN_PCT
    max_margin = config.MAX_MARGIN_PCT
    lines.append(f"Target margin: {min_margin:.1f}%—{max_margin:.1f}%")
    
    # Line 4: Max time left
    max_time = config.MAX_TIME_HOURS or 0.0
    lines.append(f"Max time left: {max_time:.2f} hours")
    
    return "\n".join(lines)


def format_melt_entry(entry_num: int, evaluated: Any) -> str:
    """
    Format melt entry per Contract v1.3.1 Section 2.
    
    HTML format with clickable links.
    """
    listing = evaluated.listing
    calc = evaluated.silver_calc
    
    lines = []
    
    # Header: #N filename (Issue #1: use source_filename instead of item_id)
    filename = getattr(listing, "source_filename", None) or "unknown"
    lines.append(f"#{entry_num} {filename}")
    
    # Title (full, no truncation, cleaned)
    title = getattr(listing, "title", None) or "NO TITLE"
    title = cleanup_title(title)
    lines.append(f"Title: {title}")
    lines.append("")
    
    # Price section - Contract v1.3.2 order
    total_price = float(getattr(listing, "total_price", 0.0) or 0.0)
    shipping = float(getattr(listing, "ship_price", 0.0) or 0.0)
    item_price = max(0.0, total_price - shipping)
    
    profit = calc.get("profit", 0.0)
    margin_pct = calc.get("margin_pct", 0.0)
    
    rec_max_item = calc.get("rec_max_item", 0.0)
    rec_max_total = calc.get("rec_max_total", 0.0)
    profit_at_max = calc.get("profit_at_rec_max", 0.0)
    margin_at_max = calc.get("margin_at_rec_max", 0.0)
    
    lines.append(f"RecMaxBid: ${rec_max_item:.2f} (${rec_max_total:.2f} incl. ship) | ${profit_at_max:.2f} ({margin_at_max:.1f}% margin vs pawn)")
    lines.append(f"Current Profit (pawn): ${profit:.2f} ({margin_pct:.1f}% margin vs pawn)")
    lines.append(f"Current Total: ${total_price:.2f} (item ${item_price:.2f} + ship ${shipping:.2f})")
    lines.append("")
    
    # Silver content section
    qty = calc.get("quantity", 1)
    oz_per = calc.get("oz_per_coin", 0.0)
    total_oz = calc.get("total_oz", 0.0)
    lines.append(f"Qty: {qty} | oz/coin: {oz_per:.5f} | Total oz: {total_oz:.2f}")
    
    melt_value = calc.get("melt_value", 0.0)
    melt_payout = calc.get("melt_payout", 0.0)
    lines.append(f"Melt: ${melt_value:.2f} | Pawn payout: ${melt_payout:.2f}")
    
    # Time left
    time_left = getattr(listing, "time_left", None) or "--:--"
    end_clock = getattr(listing, "end_clock", None) or ""
    
    if time_left.endswith(" left"):
        time_left = time_left[:-5]
    
    if end_clock.startswith("(") and end_clock.endswith(")"):
        end_clock = end_clock[1:-1]
    
    if end_clock:
        lines.append(f"Time left: {time_left} ({end_clock})")
    else:
        lines.append(f"Time left: {time_left}")
    lines.append("")
    
    # Links (HTML format with descriptive text)
    item_id = getattr(listing, "item_id", None) or "unknown"
    ebay_listing_url = construct_ebay_listing_url(item_id)
    ebay_sales_url = construct_ebay_sales_url(title)
    
    links_html = f'Links: <a href="{ebay_listing_url}">Link to Listing</a> | <a href="{ebay_sales_url}">Link to Ebay Sales</a>'
    lines.append(links_html)
    lines.append("-" * 40)
    
    return "<br>".join(lines)


def format_pros_entry(entry_num: int, evaluated: Any) -> str:
    """
    Format PROS entry with placeholders per Contract v1.3.1 Section 2.
    
    HTML format with clickable links.
    Sprint 07: PROS fields show placeholders ("--" or "N/A")
    Sprint 08: Will populate real PROS data
    """
    listing = evaluated.listing
    calc = evaluated.silver_calc
    
    lines = []
    
    # Header: #N filename (Issue #1: use source_filename instead of item_id)
    filename = getattr(listing, "source_filename", None) or "unknown"
    lines.append(f"#{entry_num} {filename}")
    
    # Title (full, no truncation, cleaned)
    title = getattr(listing, "title", None) or "NO TITLE"
    title = cleanup_title(title)
    lines.append(f"Title: {title}")
    lines.append(f"&lt;&lt;&lt;&lt; Numismatic override: N/A &gt;&gt;&gt;&gt;")
    lines.append("")
    
    # PROS-specific fields (placeholders)
    lines.append(f"Est. dealer payout (@---%): -- (est. profit: --, ---% margin vs current)")
    lines.append(f"FMV floor (G—VG): -- | Source: Offline EMA --")
    
    # Price section - Contract v1.3.2 order
    total_price = float(getattr(listing, "total_price", 0.0) or 0.0)
    shipping = float(getattr(listing, "ship_price", 0.0) or 0.0)
    item_price = max(0.0, total_price - shipping)
    
    profit = calc.get("profit", 0.0)
    margin_pct = calc.get("margin_pct", 0.0)
    
    rec_max_total = calc.get("rec_max_total", 0.0)
    rec_max_item = calc.get("rec_max_item", 0.0)
    
    lines.append(f"RecMaxBid (item only): ${rec_max_item:.2f}")
    lines.append(f"RecMaxTotal (incl. ship): ${rec_max_total:.2f}")
    lines.append(f"Current Profit: ${profit:.2f} ({margin_pct:.1f}% margin)")
    lines.append(f"Current Total: ${total_price:.2f} (item ${item_price:.2f} + ship ${shipping:.2f})")
    lines.append("")
    
    # Silver content section (same as melt)
    qty = calc.get("quantity", 1)
    oz_per = calc.get("oz_per_coin", 0.0)
    total_oz = calc.get("total_oz", 0.0)
    lines.append(f"Qty: {qty} | oz/coin: {oz_per:.5f} | Total oz: {total_oz:.2f}")
    
    melt_value = calc.get("melt_value", 0.0)
    melt_payout = calc.get("melt_payout", 0.0)
    lines.append(f"Melt: ${melt_value:.2f} | Pawn payout: ${melt_payout:.2f}")
    
    # Time left (same as melt)
    time_left = getattr(listing, "time_left", None) or "--:--"
    end_clock = getattr(listing, "end_clock", None) or ""
    
    if time_left.endswith(" left"):
        time_left = time_left[:-5]
    
    if end_clock.startswith("(") and end_clock.endswith(")"):
        end_clock = end_clock[1:-1]
    
    if end_clock:
        lines.append(f"Time left: {time_left} ({end_clock})")
    else:
        lines.append(f"Time left: {time_left}")
    lines.append("")
    
    # Links (including CoinBook placeholder, HTML format)
    item_id = getattr(listing, "item_id", None) or "unknown"
    ebay_listing_url = construct_ebay_listing_url(item_id)
    ebay_sales_url = construct_ebay_sales_url(title)
    coinbook_placeholder = construct_coinbook_url()
    
    links_html = f'Links: <a href="{ebay_listing_url}">Link to Listing</a> | <a href="{ebay_sales_url}">Link to Ebay Sales</a> | {coinbook_placeholder}'
    lines.append(links_html)
    lines.append("-" * 40)
    
    return "<br>".join(lines)


# =============================================================================
# Main Email Building
# =============================================================================

def build_email_subject(hits: List[Any]) -> str:
    """
    Build email subject line.
    
    Contract v1.3.1 Section 2:
    [A1] Offline eBay Silver HITS ([A6] new)
    
    Args:
        hits: List of Evaluated objects (already sorted)
    
    Returns:
        Subject line string
    """
    earliest_time = extract_earliest_time(hits)
    hit_count = len(hits)
    
    return f"{earliest_time} Offline eBay Silver HITS ({hit_count} new)"


def build_email_body(hits: List[Any]) -> str:
    """
    Build complete email body per Contract v1.3.1 Section 2.
    
    HTML format with clickable links.
    
    Args:
        hits: List of Evaluated objects with is_hit=True
    
    Returns:
        Complete email body string (HTML)
    
    Contract: v1.3.1 Section 2 (Email UX Contract)
    """
    lines = []
    
    # HTML opening
    lines.append("<html><body>")
    lines.append("<pre style='font-family: monospace;'>")
    
    # Header section (includes title, divider, and Total HITs)
    lines.append(format_header_section())
    lines.append(f"Total HITs: {len(hits)}")
    
    lines.append("</pre>")

    # Divider after this block
    lines.append("-" * 40 + "<br>")
    
    # Sort entries by earliest end time
    sorted_hits = sorted(
        hits,
        key=lambda e: getattr(e.listing, "end_time_ts", None) or 10**18
    )
    
    # Entry blocks (numbered sequentially)
    for i, evaluated in enumerate(sorted_hits, 1):
        
        is_prospect = getattr(evaluated, "is_prospect", False)
        
        if is_prospect:
            lines.append(format_pros_entry(i, evaluated))
        else:
            lines.append(format_melt_entry(i, evaluated))
        
        lines.append("<br>")
    
    # Footer
    lines.append("<pre style='font-family: monospace;'>")
    lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("</pre>")
    
    # HTML closing
    lines.append("</body></html>")
    
    return "\n".join(lines)


#EndOfFile
