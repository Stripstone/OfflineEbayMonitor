# parser_listings.py
"""
Sprint 03 — Parser + Classification Shape (No Math)

Purpose:
- Deterministic extraction of:
  - title (modern + legacy)
  - qty (deterministic precedence)
  - filter_flags (descriptive only)
  - numismatic_flags (descriptive only)
- Optional identity-only fields when trivially available:
  - item_id (from /itm/<id>)
  - url (canonical listing URL)

Hard boundaries (SRM / Sprint 03):
- No imports from math/email/mailer/EMA/scoring modules
- No HIT/MISS/PROS gates
- No payout/melt/dealer math
- No UX string formatting

#EndOfFile
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

# Numismatic/high-grade signals (descriptive only this sprint)
# Keep names stable and explicit.
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

    Returns list of dicts with at least:
      - title: str
      - qty: int (>=1)
      - filter_flags: {str: bool}
      - numismatic_flags: {str: bool}

    Optional, identity-only:
      - item_id: str
      - url: str
    """
    soup = BeautifulSoup(html_text, "html.parser")

    containers = _find_listing_containers(soup)
    out: List[Dict[str, Any]] = []

    ft = tuple(filter_terms) if filter_terms is not None else DEFAULT_FILTER_TERMS
    nfp = tuple(numismatic_flag_patterns) if numismatic_flag_patterns is not None else DEFAULT_NUMISMATIC_FLAG_PATTERNS

    for li in containers:
        title = _extract_title(li)
        # Ensure stable types even if title extraction fails
        if not title:
            title = ""

        qty = _infer_qty_from_title(title)

        filter_flags = _make_term_flags(title, ft)
        numismatic_flags = _make_regex_flags(title, nfp)

        item_id, url = _extract_item_id_and_url(li)

        rec: Dict[str, Any] = {
            "title": title,
            "qty": qty,
            "filter_flags": filter_flags,
            "numismatic_flags": numismatic_flags,
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
    """
    Supports:
      - modern: <li class="s-card ...">
      - legacy: <li class="s-item">
    """
    lis = soup.find_all("li")
    containers: List[Any] = []
    for li in lis:
        classes = li.get("class") or []
        if not classes:
            continue

        # modern: any li containing class token that includes 's-card'
        if any("s-card" in c for c in classes):
            containers.append(li)
            continue

        # legacy: exact token 's-item'
        if "s-item" in classes:
            containers.append(li)
            continue

    return containers


# -------------------------
# Title extraction
# -------------------------

def _extract_title(container: Any) -> str:
    """
    Modern:
      .s-card__title (often div[role=heading] ... > span)
    Legacy:
      h3.s-item__title
    """
    # modern first
    node = container.select_one(".s-card__title")
    if node is not None:
        txt = node.get_text(" ", strip=True)
        return _normalize_title_text(txt)

    # legacy fallback
    node = container.select_one("h3.s-item__title")
    if node is not None:
        txt = node.get_text(" ", strip=True)
        return _normalize_title_text(txt)

    # conservative fallback: any element with class ending in __title
    node = container.select_one('[class*="__title"]')
    if node is not None:
        txt = node.get_text(" ", strip=True)
        return _normalize_title_text(txt)

    return ""


def _normalize_title_text(s: str) -> str:
    # collapse whitespace deterministically, do not rewrite meaning
    s2 = re.sub(r"\s+", " ", s).strip()
    return s2


# -------------------------
# Identity-only extraction (optional)
# -------------------------

_ITM_ID_RE = re.compile(r"/itm/(\d{6,})")

def _extract_item_id_and_url(container: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Looks for canonical listing link:
      <a class="s-card__link" href="https://www.ebay.com/itm/<ITEM_ID>">
    Returns (item_id, url) when available.
    """
    a = container.select_one("a.s-card__link[href]") or container.select_one("a[href*='/itm/']")
    if a is None:
        return None, None

    href = (a.get("href") or "").strip()
    if not href:
        return None, None

    m = _ITM_ID_RE.search(href)
    if not m:
        return None, href  # still identity-ish, but no parsed id
    return m.group(1), href


# -------------------------
# Quantity inference (deterministic precedence)
# -------------------------

_QTY_RULES: Tuple[Tuple[str, re.Pattern], ...] = (
    # 1) "lot of 3", "lot 3"
    ("lot_of", re.compile(r"\blot\s+(?:of\s+)?(\d{1,3})\b", re.IGNORECASE)),
    # 2) "qty 3", "quantity 3"
    ("qty", re.compile(r"\bqty\b[\s:]*?(\d{1,3})\b|\bquantity\b[\s:]*?(\d{1,3})\b", re.IGNORECASE)),
    # 3) "x3", "3x" (avoid matching things like 'x100' unlikely but capped)
    ("x_form", re.compile(r"\b(?:x(\d{1,3})|(\d{1,3})x)\b", re.IGNORECASE)),
    # 4) "3 pcs", "3 pieces", "3 coins"
    ("count_words", re.compile(r"\b(\d{1,3})\s*(?:pc|pcs|pieces|coins|coin)\b", re.IGNORECASE)),
)

def _infer_qty_from_title(title: str) -> int:
    """
    Deterministic qty rules only.
    Precedence is fixed by _QTY_RULES order.

    Defaults to qty=1 if no signal exists.

    Guardrails:
    - Only accept 1..199 to avoid years/IDs dominating.
    """
    if not title:
        return 1

    t = title.strip()
    for _, rx in _QTY_RULES:
        m = rx.search(t)
        if not m:
            continue

        # some patterns have two groups; choose first non-None
        val = None
        for g in m.groups():
            if g is not None:
                val = g
                break

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
    """
    Simple substring flags, stable keys derived from terms.
    """
    lower = title.lower() if title else ""
    flags: Dict[str, bool] = {}
    for term in terms:
        key = _term_to_flag_key(term)
        flags[key] = term.lower() in lower
    return flags


def _term_to_flag_key(term: str) -> str:
    # stable, filename-safe-ish key
    k = term.lower().strip()
    k = re.sub(r"\s+", "_", k)
    k = re.sub(r"[^a-z0-9_]+", "", k)
    return f"has_{k}" if not k.startswith("has_") else k


def _make_regex_flags(title: str, patterns: Sequence[Tuple[str, str]]) -> Dict[str, bool]:
    """
    Regex-based flags with explicit, stable keys.
    """
    lower = title.lower() if title else ""
    out: Dict[str, bool] = {}
    for key, pat in patterns:
        out[key] = re.search(pat, lower, flags=re.IGNORECASE) is not None
    return out


#EndOfFile
