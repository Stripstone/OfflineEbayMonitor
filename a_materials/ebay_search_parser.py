# ebay_search_parser.py
"""EBAY SEARCH PARSER (offline saved HTML)

Input:
- One offline-saved eBay search results HTML page (string)

Output:
- A list of Listing objects (model_types.Listing) with normalized fields:
  title, link, item_price, shipping, total_price, bids, time_left, item_id

Additional fields (set via setattr for compatibility):
  end_time_ts (epoch seconds, float)
  end_time_str (human readable like "Today 02:48 PM" when present)

Key blueprint alignment:
- Canonical link selection priority:
    1) a[href*='/itm/']
    2) a.s-item__link
    3) a.s-card__link
    4) first anchor tag
- Item identity ladder:
    1) /itm/<itemid> extracted from canonical URL
    2) data-listing-id attribute (and known variants)
    3) data-itemid attribute
    4) data-view digits-only (fallback)
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup

from model_types import Listing
from utils import parse_money, normalize_whitespace


_INVALID_ITM_IDS = {"123456", "000000", "0000000000", "000000000000"}

_CONTAINER_SELECTORS = [
    "li.s-card",
    "li.s-item",
    "ul.srp-results.srp-list > li",
    "div.s-card",
    "div.s-item",
    "[data-view]",
]

_PRICE_SELECTORS = [
    ".s-item__price",
    ".s-card__price",
    "[data-testid='item-price']",
    "[data-testid='x-price-primary']",
    "[data-testid='x-price-approx']",
    ".x-price-primary",
    ".s-item__detail--primary .s-item__price",
]

_SHIP_SELECTORS = [
    ".s-item__shipping",
    ".s-card__shipping",
    "[data-testid='shipping-price']",
    ".s-item__logisticsCost",
]

_TIMELEFT_SELECTORS = [
    ".s-item__time-left",
    ".s-card__time-left",
    ".s-item__dynamic .LIGHT_HIGHLIGHT",
    "[data-testid='time-left']",
]

_TIMEEND_SELECTORS = [
    ".s-card__time-end",
    ".s-item__time-end",
]

_BIDCOUNT_SELECTORS = [
    ".s-item__bidCount",
    ".s-item__bids",
    "[data-testid='bidCount']",
    "[data-testid='bid-count']",
]


def _select_result_nodes(soup: BeautifulSoup):
    for sel in _CONTAINER_SELECTORS:
        nodes = soup.select(sel)
        if nodes:
            return nodes
    return []


def _clean_title(text: str) -> str:
    t = normalize_whitespace(text or "")
    for phrase in (
        "Opens in a new window or tab",
        "Opens in a new window or tab.",
        "New Listing",
        "Sponsored",
    ):
        t = t.replace(phrase, "")
    return normalize_whitespace(t)


def _normalize_link(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://www.ebay.com" + href
    return href


def _pick_canonical_link(node) -> str:
    a = node.select_one("a[href*='/itm/']")
    if a and a.has_attr("href"):
        return _normalize_link(a["href"])

    a = node.select_one("a.s-item__link")
    if a and a.has_attr("href"):
        return _normalize_link(a["href"])

    a = node.select_one("a.s-card__link")
    if a and a.has_attr("href"):
        return _normalize_link(a["href"])

    a = node.select_one("a[href]")
    if a and a.has_attr("href"):
        return _normalize_link(a["href"])

    return ""


def _extract_item_id_from_link(link: str) -> Optional[str]:
    if not link:
        return None
    m = re.search(r"/itm/(\d+)", link)
    if not m:
        return None
    item_id = m.group(1)
    if item_id in _INVALID_ITM_IDS:
        return None
    return item_id


def _extract_attr_first(node, names: Tuple[str, ...]) -> Optional[str]:
    for n in names:
        if node.has_attr(n):
            v = str(node.get(n) or "").strip()
            if v:
                return v
    return None


def _extract_item_identity(node, canonical_link: str) -> Optional[str]:
    itm = _extract_item_id_from_link(canonical_link)
    if itm:
        return itm

    v = _extract_attr_first(node, ("data-listing-id", "data-listingid", "data-listingId", "data-listingID"))
    if v:
        digits = re.sub(r"\D+", "", v)
        return digits or v

    v = _extract_attr_first(node, ("data-itemid", "data-itemId", "data-itemID"))
    if v:
        digits = re.sub(r"\D+", "", v)
        return digits or v

    v = _extract_attr_first(node, ("data-view",))
    if v:
        digits = re.sub(r"\D+", "", v)
        return digits or None

    return None


def _extract_price(node) -> Optional[float]:
    for sel in _PRICE_SELECTORS:
        el = node.select_one(sel)
        if el:
            val = parse_money(el.get_text(" ", strip=True))
            if val is not None:
                return float(val)

    full = node.get_text(" ", strip=True) or ""
    candidates = re.findall(r"\$[\d,]+(?:\.\d+)?", full)
    for c in candidates:
        v = parse_money(c)
        if v is None:
            continue
        if 0.01 <= v <= 500000:
            return float(v)
    return None


def _extract_shipping(node) -> float:
    for sel in _SHIP_SELECTORS:
        el = node.select_one(sel)
        if el:
            tx = (el.get_text(" ", strip=True) or "").lower()
            if "free" in tx:
                return 0.0
            v = parse_money(tx)
            if v is not None:
                return float(v)

    full = (node.get_text(" ", strip=True) or "").lower()

    # Common eBay SRP patterns include:
    #   "+$4.95 shipping" / "+$4.95 delivery"
    #   "Free shipping" / "Free delivery"
    if "free shipping" in full or "free delivery" in full:
        return 0.0

    # Prefer explicit +$X.XX (shipping/delivery) patterns.
    m = re.search(r"\+\s*\$([\d,]+(?:\.\d+)?)\s*(?:shipping|delivery)", full, re.I)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except Exception:
            return 0.0

    # Older/alternate pattern: "shipping $X.XX" or "delivery $X.XX"
    m = re.search(r"(?:shipping|delivery)\W*\$([\d,]+(?:\.\d+)?)", full, re.I)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except Exception:
            return 0.0

    # Last resort: first money token found anywhere in the text, but only if
    # it appears in the vicinity of shipping/delivery language.
    if "shipping" in full or "delivery" in full:
        v = parse_money(full)
        if v is not None:
            return float(v)

    return 0.0


def _extract_time_left_and_end(node) -> tuple[str, str]:
    """
    Returns (time_left_text, time_end_text).
    time_left_text example: "26m left"
    time_end_text example: "(Today 03:36 PM)" or "Today 03:36 PM"
    """
    tl = ""
    for sel in _TIMELEFT_SELECTORS:
        el = node.select_one(sel)
        if el:
            tl = el.get_text(" ", strip=True)
            break

    te = ""
    for sel in _TIMEEND_SELECTORS:
        el = node.select_one(sel)
        if el:
            te = el.get_text(" ", strip=True)
            break

    tl = normalize_whitespace(tl)
    te = normalize_whitespace(te)
    return tl, te


def _parse_time_left_seconds(tl_text: str) -> Optional[int]:
    """
    Parse formats like:
      "26m left"
      "3h 15m left"
      "1d 2h left"
    Returns seconds or None.
    """
    if not tl_text:
        return None

    txt = tl_text.lower()
    # ensure we only parse the part before "left"
    txt = txt.split("left", 1)[0].strip()

    # find number+unit tokens
    tokens = re.findall(r"(\d+)\s*([dhm])", txt)
    if not tokens:
        return None

    days = hours = minutes = 0
    for num_s, unit in tokens:
        try:
            num = int(num_s)
        except Exception:
            continue
        if unit == "d":
            days += num
        elif unit == "h":
            hours += num
        elif unit == "m":
            minutes += num

    return days * 86400 + hours * 3600 + minutes * 60


def _extract_bids(node) -> int:
    for sel in _BIDCOUNT_SELECTORS:
        el = node.select_one(sel)
        if el:
            tx = el.get_text(" ", strip=True) or ""
            m = re.search(r"(\d+)", tx)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    return 0

    full = node.get_text(" ", strip=True) or ""
    m = re.search(r"\b(\d+)\s+bids?\b", full, re.I)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return 0
    return 0


def parse_ebay_search_html(filename_label: str, html_text: str) -> List[Listing]:
    if not html_text:
        return []

    soup = BeautifulSoup(html_text, "html.parser")
    nodes = _select_result_nodes(soup)
    if not nodes:
        return []

    out: List[Listing] = []

    now_ts = time.time()

    for node in nodes:
        try:
            title_el = node.select_one(
                ".s-item__title, .s-card__title, .s-item__info .s-item__title, [data-testid='item-title']"
            )
            title = _clean_title(title_el.get_text(" ", strip=True) if title_el else "")
            if not title:
                continue
            if title.lower() in {"shop on ebay", "sponsored"}:
                continue

            item_price = _extract_price(node)
            if item_price is None:
                continue

            shipping = _extract_shipping(node)
            total = float(item_price) + float(shipping)

            link = _pick_canonical_link(node)
            item_id = _extract_item_identity(node, link)

            tl_raw, te_raw = _extract_time_left_and_end(node)

            # Unified display string (existing behavior)
            if tl_raw and te_raw:
                time_left = normalize_whitespace(f"{tl_raw} {te_raw}")
            else:
                time_left = tl_raw or ""

            bids = _extract_bids(node)

            lst = Listing(
                title=title,
                link=link,
                item_price=float(item_price),
                shipping=float(shipping),
                total_price=float(total),
                bids=int(bids),
                time_left=time_left,
                item_id=item_id,
            )

            # --- NEW: end time fields for filtering/sorting
            seconds_left = _parse_time_left_seconds(tl_raw)
            if seconds_left is not None:
                setattr(lst, "end_time_ts", float(now_ts + seconds_left))

            # prefer storing a clean end time label if present
            if te_raw:
                # strip parentheses if present
                te_clean = te_raw.strip()
                if te_clean.startswith("(") and te_clean.endswith(")"):
                    te_clean = te_clean[1:-1].strip()
                setattr(lst, "end_time_str", te_clean)

            out.append(lst)

        except Exception:
            continue

    return out
