# ebay_item_parser.py
"""EBAY ITEM PARSER (offline saved listing page HTML)

Purpose:
- Parse an offline-saved *individual item* page when available.
- This improves link confidence and can provide fields not present in search cards.

Non-goals:
- No live scraping
- No sold-page crawling

Output:
- Partial dict suitable to merge onto a Listing (caller decides merge rules)
"""


from __future__ import annotations

import re
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup

from utils import parse_money, normalize_whitespace


def _extract_itm_id_from_any_url(url: str) -> Optional[str]:
    if not url:
        return None
    m = re.search(r"/itm/(\d+)", url)
    return m.group(1) if m else None


def parse_ebay_item_html(filename_label: str, html_text: str) -> Dict[str, Any]:
    if not html_text:
        return {}

    soup = BeautifulSoup(html_text, "html.parser")

    # Canonical URL / item id
    canonical = soup.select_one("link[rel='canonical']")
    canonical_url = canonical.get("href", "").strip() if canonical else ""
    item_id = _extract_itm_id_from_any_url(canonical_url)

    # Title
    title = ""
    title_el = soup.select_one("h1#itemTitle, h1.x-item-title__mainTitle, h1[data-testid='x-item-title__mainTitle']")
    if title_el:
        title = normalize_whitespace(title_el.get_text(" ", strip=True))
        title = title.replace("Details about", "").strip()

    # Price (best-effort)
    price = None
    price_el = soup.select_one("[data-testid='x-price-primary'] span, .x-price-primary span, #prcIsum, #mm-saleDscPrc")
    if price_el:
        price = parse_money(price_el.get_text(" ", strip=True))

    # Shipping (best-effort)
    shipping = None
    ship_el = soup.select_one("[data-testid='shippingSummary'] , [data-testid='x-shippingSummary'] , #fshippingCost")
    if ship_el:
        tx = ship_el.get_text(" ", strip=True).lower()
        if "free" in tx:
            shipping = 0.0
        else:
            shipping = parse_money(tx)

    # Bids (auction)
    bids = None
    bid_el = soup.select_one("[data-testid='bidCount'] , [data-testid='bid-count'] , span#qty-test")
    if bid_el:
        m = re.search(r"(\d+)", bid_el.get_text(" ", strip=True))
        if m:
            try:
                bids = int(m.group(1))
            except Exception:
                bids = None

    # Time-left/end-time (best-effort)
    time_left = ""
    tl_el = soup.select_one("[data-testid='ux-timer__text'] , span#vi-cdown_timeLeft")
    if tl_el:
        time_left = normalize_whitespace(tl_el.get_text(" ", strip=True))

    out: Dict[str, Any] = {}
    if title:
        out["title"] = title
    if canonical_url:
        out["link"] = canonical_url
    if item_id:
        out["item_id"] = item_id
    if price is not None:
        out["item_price"] = float(price)
    if shipping is not None:
        out["shipping"] = float(shipping)
    if (price is not None) and (shipping is not None):
        out["total_price"] = float(price) + float(shipping)
    if bids is not None:
        out["bids"] = int(bids)
    if time_left:
        out["time_left"] = time_left

    return out
