# parser_listings.py
"""
Sprint 05.1 — Schema Integration (Post-Pricing Listing Shape / Adapter)

Purpose:
- Extend Sprint 03 parser output with additive, post-pricing fields so
  prospect_score.score_prospect() can consume:
    - total_price
    - bids
- Preserve all prior keys and meanings.
- No UX, EMA, HIT/MISS/PROS, or scoring logic.

Boundaries (SRM / Contract):
- Parser owns raw extraction only.
- No business rules, no math beyond total_price = item_price + ship_price.
- No logging/printing unless explicitly invoked via helper.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup


# -------------------------
# Defaults (shape-only flags)
# -------------------------

DEFAULT_FILTER_TERMS: Tuple[str, ...] = (
    "copy",
    "replica",
    "reproduction",
    "plated",
    "clad",
    "silver plate",
    "silverplated",
    "not silver",
    "fake",
)

DEFAULT_NUMISMATIC_FLAG_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("has_pcgs", r"\bpcgs\b"),
    ("has_ngc", r"\bngc\b"),
    ("has_anacs", r"\banacs\b"),
    ("has_cac", r"\bcac\b"),
    ("has_slabbed", r"\bslab(?:bed)?\b"),
    ("has_proof", r"\bproof\b|\bpr\d{1,2}\b|\bpf\d{1,2}\b"),
    ("has_ms_grade", r"\bms\s?\d{1,2}\b|\bms\d{1,2}\b"),
    ("has_au_grade", r"\bau\s?\d{1,2}\b|\bau\d{1,2}\b"),
    ("has_unc_bu", r"\bunc\b|\buncirculated\b|\bbu\b|\bbrilliant uncirculated\b"),
    ("has_dm_pl", r"\bdmpl\b|\bpl\b|\bprooflike\b"),
    ("has_key_date", r"\bkey date\b|\bsemi[- ]key\b"),
)


# -------------------------
# Public API
# -------------------------

def parse_listings_from_html(
    html_text: str,
    *,
    filter_terms: Optional[Sequence[str]] = None,
    numismatic_flag_patterns: Optional[Sequence[Tuple[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Parse offline eBay search-result HTML into stable listing records.

    Base (Sprint 03):
      - title
      - qty
      - filter_flags
      - numismatic_flags
      - optional item_id, url

    Additive (Sprint 05.1):
      - item_price: float | None
      - ship_price: float | None
      - total_price: float | None
      - bids: int
      - time_left: str | None
      - end_clock: str | None
    """
    soup = BeautifulSoup(html_text, "html.parser")
    containers = _find_listing_containers(soup)
    out: List[Dict[str, Any]] = []

    ft = tuple(filter_terms) if filter_terms is not None else DEFAULT_FILTER_TERMS
    nfp = tuple(numismatic_flag_patterns) if numismatic_flag_patterns is not None else DEFAULT_NUMISMATIC_FLAG_PATTERNS

    for li in containers:
        title = _extract_title(li) or ""
        qty = _infer_qty_from_title(title)

        filter_flags = _make_term_flags(title, ft)
        numismatic_flags = _make_regex_flags(title, nfp)

        item_id, url = _extract_item_id_and_url(li)

        item_price = _extract_item_price(li)
        ship_price = _extract_shipping_price(li)
        total_price = None
        if item_price is not None and ship_price is not None:
            total_price = item_price + ship_price

        bids = _extract_bid_count(li)
        time_left, end_clock = _extract_time_left_and_end(li)

        rec: Dict[str, Any] = {
            "title": title,
            "qty": qty,
            "filter_flags": filter_flags,
            "numismatic_flags": numismatic_flags,
            "item_price": item_price,
            "ship_price": ship_price,
            "total_price": total_price,
            "bids": bids,
            "time_left": time_left,
            "end_clock": end_clock,
        }

        if item_id:
            rec["item_id"] = item_id
        if url:
            rec["url"] = url

        out.append(rec)

    return out


# -------------------------
# Container discovery
# -------------------------

def _find_listing_containers(soup: BeautifulSoup) -> List[Any]:
    lis = soup.find_all("li")
    containers: List[Any] = []
    for li in lis:
        classes = li.get("class") or []
        if not classes:
            continue
        if any("s-card" in c for c in classes):
            containers.append(li)
            continue
        if "s-item" in classes:
            containers.append(li)
            continue
    return containers


# -------------------------
# Title extraction
# -------------------------

def _extract_title(container: Any) -> str:
    node = container.select_one(".s-card__title")
    if node is not None:
        return _normalize_title_text(node.get_text(" ", strip=True))

    node = container.select_one("h3.s-item__title")
    if node is not None:
        return _normalize_title_text(node.get_text(" ", strip=True))

    node = container.select_one('[class*="__title"]')
    if node is not None:
        return _normalize_title_text(node.get_text(" ", strip=True))

    return ""


def _normalize_title_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# -------------------------
# Identity-only extraction
# -------------------------

_ITM_ID_RE = re.compile(r"/itm/(\d{6,})")

def _extract_item_id_and_url(container: Any) -> Tuple[Optional[str], Optional[str]]:
    a = container.select_one("a.s-card__link[href]") or container.select_one("a[href*='/itm/']")
    if a is None:
        return None, None
    href = (a.get("href") or "").strip()
    if not href:
        return None, None
    m = _ITM_ID_RE.search(href)
    if not m:
        return None, href
    return m.group(1), href


# -------------------------
# Pricing extraction (raw)
# -------------------------

_PRICE_RE = re.compile(r"\$([\d,]+(?:\.\d{2})?)")

def _extract_item_price(container: Any) -> Optional[float]:
    node = container.select_one(".s-card__price")
    if node is None:
        return None
    txt = node.get_text(" ", strip=True)
    m = _PRICE_RE.search(txt)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _extract_shipping_price(container: Any) -> Optional[float]:
    texts = container.select("span.su-styled-text")
    for n in texts:
        t = n.get_text(" ", strip=True).lower()
        if "free" in t and ("delivery" in t or "shipping" in t):
            return 0.0
        if "delivery" in t or "shipping" in t:
            m = _PRICE_RE.search(t)
            if not m:
                return None
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                return None
    return None


# -------------------------
# Bids / time-left extraction
# -------------------------

_BIDS_RE = re.compile(r"(\d+)\s+bids?", re.IGNORECASE)

def _extract_bid_count(container: Any) -> int:
    texts = container.find_all(text=True)
    for t in texts:
        m = _BIDS_RE.search(t)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return 0


def _extract_time_left_and_end(container: Any) -> Tuple[Optional[str], Optional[str]]:
    tl = None
    ec = None

    node = container.select_one(".s-card__time-left")
    if node is not None:
        tl = node.get_text(" ", strip=True)

    node = container.select_one(".s-card__time-end")
    if node is not None:
        ec = node.get_text(" ", strip=True)

    if tl is None:
        node = container.select_one("span.s-item__time-left")
        if node is not None:
            tl = node.get_text(" ", strip=True)

    return tl, ec


# -------------------------
# Quantity inference
# -------------------------

_QTY_RULES: Tuple[Tuple[str, re.Pattern], ...] = (
    ("lot_of", re.compile(r"\blot\s+(?:of\s+)?(\d{1,3})\b", re.IGNORECASE)),
    ("qty", re.compile(r"\bqty\b[\s:]*?(\d{1,3})\b|\bquantity\b[\s:]*?(\d{1,3})\b", re.IGNORECASE)),
    ("x_form", re.compile(r"\b(?:x(\d{1,3})|(\d{1,3})x)\b", re.IGNORECASE)),
    ("count_words", re.compile(r"\b(\d{1,3})\s*(?:pc|pcs|pieces|coins|coin)\b", re.IGNORECASE)),
)

def _infer_qty_from_title(title: str) -> int:
    if not title:
        return 1
    for _, rx in _QTY_RULES:
        m = rx.search(title)
        if not m:
            continue
        val = next((g for g in m.groups() if g is not None), None)
        if val is None:
            continue
        try:
            n = int(val)
        except ValueError:
            continue
        if 1 <= n <= 199:
            return n
    return 1


# -------------------------
# Flags (shape-only)
# -------------------------

def _make_term_flags(title: str, terms: Sequence[str]) -> Dict[str, bool]:
    lower = title.lower() if title else ""
    flags: Dict[str, bool] = {}
    for term in terms:
        key = _term_to_flag_key(term)
        flags[key] = term.lower() in lower
    return flags


def _term_to_flag_key(term: str) -> str:
    k = term.lower().strip()
    k = re.sub(r"\s+", "_", k)
    k = re.sub(r"[^a-z0-9_]+", "", k)
    return f"has_{k}" if not k.startswith("has_") else k


def _make_regex_flags(title: str, patterns: Sequence[Tuple[str, str]]) -> Dict[str, bool]:
    lower = title.lower() if title else ""
    out: Dict[str, bool] = {}
    for key, pat in patterns:
        out[key] = re.search(pat, lower, flags=re.IGNORECASE) is not None
    return out


# -------------------------
# Field presence report (explicit helper)
# -------------------------

def report_field_presence(html_texts: Sequence[str]) -> Dict[str, int]:
    counts = {
        "item_price": 0,
        "ship_price": 0,
        "total_price": 0,
        "bids": 0,
        "time_left": 0,
        "end_clock": 0,
        "item_id": 0,
    }
    for html in html_texts:
        for rec in parse_listings_from_html(html):
            for k in counts:
                if k in rec and rec[k] is not None:
                    counts[k] += 1
    return counts


#EndOfFile


# -------------------------
# Coin metadata extraction (Sprint 05.6)
# -------------------------

_COIN_SERIES_PATTERNS = (
    ("Morgan Dollar", re.compile(r"\bmorgan\b.*\bdollar\b", re.IGNORECASE)),
    ("Peace Dollar", re.compile(r"\bpeace\b.*\bdollar\b", re.IGNORECASE)),
    ("Kennedy Half", re.compile(r"\bkennedy\b.*(?:half|50)", re.IGNORECASE)),
    ("Walking Liberty Half", re.compile(r"\bwalking\s+liberty\b.*(?:half|50)", re.IGNORECASE)),
    ("Franklin Half", re.compile(r"\bfranklin\b.*(?:half|50)", re.IGNORECASE)),
    ("Barber Half", re.compile(r"\bbarber\b.*(?:half|50)", re.IGNORECASE)),
    ("Seated Liberty Half", re.compile(r"\bseated\b.*(?:half|50)", re.IGNORECASE)),
)

_YEAR_PATTERN = re.compile(r"\b(1[7-9]\d{2}|20\d{2})\b")
_MINT_PATTERN = re.compile(r"\b([PDSOC]{1,2})\b")


def extract_coin_metadata(title: str) -> dict:
    """
    Extract normalized coin metadata from title.
    
    Returns:
        {
            "series": str,  # e.g., "Morgan Dollar"
            "year": str,    # e.g., "1881"
            "mint": str     # e.g., "CC" or ""
        }
    
    Sprint 05.6: Key normalization for price_store
    Contract: v1.3.1 Clarification Issue #5
    """
    metadata = {
        "series": "",
        "year": "",
        "mint": ""
    }
    
    if not title:
        return metadata
    
    # Extract series
    for series_name, pattern in _COIN_SERIES_PATTERNS:
        if pattern.search(title):
            metadata["series"] = series_name
            break
    
    # Extract year
    year_match = _YEAR_PATTERN.search(title)
    if year_match:
        metadata["year"] = year_match.group(1)
    
    # Extract mint mark (after year if possible)
    if metadata["year"]:
        # Search after year position
        year_pos = title.find(metadata["year"])
        after_year = title[year_pos + 4:] if year_pos != -1 else title
        mint_match = _MINT_PATTERN.search(after_year)
        if mint_match:
            metadata["mint"] = mint_match.group(1).upper()
    else:
        # Search entire title
        mint_match = _MINT_PATTERN.search(title)
        if mint_match:
            metadata["mint"] = mint_match.group(1).upper()
    
    return metadata


#EndOfFile
