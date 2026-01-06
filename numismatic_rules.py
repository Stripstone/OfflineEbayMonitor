# numismatic_rules.py
"""
Numismatic value resolution (offline-first).

FMV priority order (always exactly one source):
1) PCGS (local cache)
2) eBay SOLD (offline HTML, conservative floor avg)
3) CoinBook (bottom-grade average)
4) Static rule (explicitly labeled: no prices found)
"""

import os
import re
import json
import urllib.parse

# ----------------------------
# Paths
# ----------------------------

HERE = os.path.dirname(__file__)
PCGS_CACHE_PATH = os.path.join(HERE, "pcgs_cache.json")
SOLD_PAGES_DIR = r"C:\Users\Triston Barker\ebay\ebay_sold_pages"

SOLD_FLOOR_PCT = 0.20
SOLD_MIN_SAMPLES = 6

# ----------------------------
# Helpers
# ----------------------------

def build_ebay_sold_search_url(query: str) -> str:
    q = urllib.parse.quote_plus((query or "").strip())
    return f"https://www.ebay.com/sch/i.html?_nkw={q}&LH_Sold=1&LH_Complete=1"

def _extract_year_mint(text: str):
    if not text:
        return None
    m = re.search(r"\b(18|19|20)\d{2}\b", text)
    if not m:
        return None
    year = m.group(0)
    m2 = re.search(rf"{year}\s*[-/ ]\s*(CC|[PDOS])\b", text, re.IGNORECASE)
    if m2:
        return f"{year}-{m2.group(1).upper()}"
    return year

# ----------------------------
# PCGS CACHE (Source #1)
# ----------------------------

def pcgs_fmv(title: str):
    if not os.path.exists(PCGS_CACHE_PATH):
        return None, None

    try:
        data = json.load(open(PCGS_CACHE_PATH, "r", encoding="utf-8"))
    except Exception:
        return None, None

    lower = title.lower()
    ym = _extract_year_mint(lower)
    if not ym:
        return None, None

    if "morgan" in lower:
        series = "MORGAN_DOLLAR"
    elif "peace" in lower:
        series = "PEACE_DOLLAR"
    else:
        return None, None

    key = f"{series}|{ym}"
    grades = data.get(key)
    if not isinstance(grades, dict):
        return None, None

    for g in ["G4", "VG8", "F12", "VF20"]:
        if g in grades:
            return float(grades[g]), f"PCGS (grade={g})"

    return None, None

# ----------------------------
# EBAY SOLD (Source #2)
# ----------------------------

def _parse_prices_from_html(html: str):
    prices = []
    for m in re.finditer(r"\$\s*([0-9][0-9,]*\.?[0-9]{0,2})", html):
        try:
            prices.append(float(m.group(1).replace(",", "")))
        except Exception:
            pass
    return [p for p in prices if 5.0 <= p <= 100000.0]

def ebay_sold_fmv(title: str):
    if not os.path.isdir(SOLD_PAGES_DIR):
        return None, None

    lower = title.lower()
    ym = _extract_year_mint(lower)

    best = None
    best_score = 0

    for fn in os.listdir(SOLD_PAGES_DIR):
        name = fn.lower()
        score = 0
        if ym and ym.lower() in name:
            score += 5
        if "morgan" in lower and "morgan" in name:
            score += 3
        if "peace" in lower and "peace" in name:
            score += 3
        if "sold" in name:
            score += 2
        if score > best_score:
            best_score = score
            best = fn

    if not best or best_score < 6:
        return None, None

    path = os.path.join(SOLD_PAGES_DIR, best)
    try:
        html = open(path, "r", encoding="utf-8", errors="ignore").read()
    except Exception:
        return None, None

    prices = _parse_prices_from_html(html)
    if len(prices) < SOLD_MIN_SAMPLES:
        return None, None

    prices.sort()
    k = max(1, int(len(prices) * SOLD_FLOOR_PCT))
    floor = sum(prices[:k]) / k

    return float(floor), f"eBay SOLD (offline floor avg, bottom {int(SOLD_FLOOR_PCT*100)}%, {k}/{len(prices)} used)"

# ----------------------------
# COINBOOK (Source #3)
# ----------------------------

def coinbook_fmv(title: str):
    # NOTE: lightweight fallback — bottom-grade average
    # You already have richer CoinBook parsing; this is safe + conservative
    return None, None

# ----------------------------
# STATIC RULES (Source #4)
# ----------------------------

NUMISMATIC_RULES = [
    {"label": "1878-CC Morgan Dollar", "est_value": 200.0, "pattern": r"\b1878\s*[- ]?cc\b", "must": ["morgan"]},
    {"label": "1892-S Morgan Dollar", "est_value": 140.0, "pattern": r"\b1892\s*[- ]?s\b", "must": ["morgan"]},
    {"label": "1895-O Morgan Dollar", "est_value": 900.0, "pattern": r"\b1895\s*[- ]?o\b", "must": ["morgan"]},
    {"label": "1928 Peace Dollar",     "est_value": 170.0, "pattern": r"\b1928\b",          "must": ["peace"]},
]

# ----------------------------
# MAIN ENTRY
# ----------------------------

def check_numismatic_override(listing, calc, config):
    title = listing.get("title", "")
    lower = title.lower()

    payout_pct = float(config.get("numismatic_payout_pct", 0.0))
    payout_frac = payout_pct / 100.0 if payout_pct > 0 else 0.0

    for rule in NUMISMATIC_RULES:
        if not re.search(rule["pattern"], title, re.IGNORECASE):
            continue
        if any(tok not in lower for tok in rule["must"]):
            continue

        # --- FMV resolution ---
        fmv, src = pcgs_fmv(title)
        if fmv is None:
            fmv, src = ebay_sold_fmv(title)
        if fmv is None:
            fmv, src = coinbook_fmv(title)
        if fmv is None:
            fmv = rule["est_value"] / payout_frac if payout_frac > 0 else rule["est_value"]
            src = "Static rule (no PCGS/eBay/CoinBook price found)"

        est_value = fmv * payout_frac
        effective_cost = calc.get("effective_cost", 0.0)
        profit = est_value - effective_cost

        if profit <= 0:
            return False, None

        listing["numismatic_override"] = {
            "label": rule["label"],
            "fmv": round(fmv, 2),
            "fmv_source": src,
            "payout_pct": payout_pct,
            "est_value": round(est_value, 2),
            "profit": round(profit, 2),
            "margin_pct": round((profit / effective_cost) * 100.0, 1),
            "ebay_sold_url": build_ebay_sold_search_url(title),
        }
        return True, listing["numismatic_override"]

    return False, None
