"""
EBAY BIDDING — MINIMAL GUIDE
----------------------------
Enter your FULL max bid once at 6–10 seconds left.
Your proxy max protects you: eBay only raises your bid 
enough to beat others by the minimum increment.

Max bid: 39.00 at a $33 listing
Ebay puts you at 34.12
Opponents bid $40 you lose (correct)
Opponents bid $35 you win (near 35.43) the minimal required increment
Any more than one max bid is essentially reactionary bidding

Why this matters:
- The UI disables itself in the last seconds.
- Manual bidding invites emotional overbidding.
- Using your full max earlier gives finer increments
  and much better control.

Summary: Set true max → enter once → don’t react.
"""

import os
import re
import html as html_lib
from bs4 import BeautifulSoup  # may be used by core_monitor parsers
from datetime import datetime, timedelta

from core_monitor import (
    run_monitor,
    parse_time_left_to_minutes_for_sort,
    parse_end_datetime_from_time_left,
    parse_ebay_search_html,
)
from mail_config import MAILGUN_CONFIG


# ==========================
# CONFIG SECTION
# ==========================

# Folder where your HTML-only saved eBay pages live
FOLDER_PATH = r"C:\Users\Triston Barker\Desktop\EbayMiner\ebay_pages"  # <-- CHANGE THIS to your folder

# Silver / deal config (defaults; can be adjusted here)
SPOT_PRICE = 59          # $ per oz (update as needed)
PAWN_PAYOUT_PCT = 84.0      # e.g. 90% of melt
MIN_MARGIN = 15.0           # minimum % margin to count as HIT (melt-based)
MAX_MARGIN = 60.0           # maximum % margin to count as HIT (melt-based)
MAX_TIME_HOURS = 0.5        # only consider items ending in <= this many hours; set None to disable
BID_OFFSET = 0              # extra dollars you expect to bid above current total (item+shipping)

# ==========================
# NUMISMATIC OVERRIDE RULES
# ==========================
# These rules ONLY ever *add* HITs — melt logic / core_monitor remain untouched.
# Each rule describes a coin whose *numismatic* value is high enough that
# a dealer would pay at least est_value (cash) for a single G–VG coin.
#
# Flow:
#   1) We still compute melt/pawn profit as usual.
#   2) Separately, we try to match the listing title against NUMISMATIC_RULES.
#   3) If a match is found and (est_value - price) gives a strong profit
#      that meets MIN_MARGIN, we "override" purely on numismatic value.
#   4) In that case, the listing becomes a HIT even if melt margin is bad.
#
# These are intentionally conservative "dealer-buy floors", not retail prices.

NUMISMATIC_RULES = [
    # ============================================================
    #                  MORGAN DOLLARS — ULTRA / STRONG KEYS
    # (All values are conservative G–VG dealer buy estimates)
    # ============================================================

    # ---------- Ultra keys ----------
    {
        "label": "1893-S Morgan Dollar (Key Date)",
        "est_value": 1800.0,
        "pattern": re.compile(r"\b1893\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1889-CC Morgan Dollar",
        "est_value": 900.0,
        "pattern": re.compile(r"\b1889\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },

    # We keep 1895-O / 1895-S as strong keys; 1895-P proof-only is not targeted
    {
        "label": "1895-O Morgan Dollar",
        "est_value": 900.0,
        "pattern": re.compile(r"\b1895\s*[-/ ]?o\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1895-S Morgan Dollar",
        "est_value": 900.0,
        "pattern": re.compile(r"\b1895\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },

    # ---------- Strong CC keys (early & late) ----------
    {
        "label": "1878-CC Morgan Dollar",
        "est_value": 200.0,
        "pattern": re.compile(r"\b1878\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1879-CC Morgan Dollar",
        "est_value": 200.0,
        "pattern": re.compile(r"\b1879\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1880-CC Morgan Dollar",
        "est_value": 200.0,
        "pattern": re.compile(r"\b1880\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1881-CC Morgan Dollar",
        "est_value": 200.0,
        "pattern": re.compile(r"\b1881\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1882-CC Morgan Dollar",
        "est_value": 150.0,
        "pattern": re.compile(r"\b1882\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1883-CC Morgan Dollar",
        "est_value": 150.0,
        "pattern": re.compile(r"\b1883\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1884-CC Morgan Dollar",
        "est_value": 150.0,
        "pattern": re.compile(r"\b1884\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1885-CC Morgan Dollar",
        "est_value": 200.0,
        "pattern": re.compile(r"\b1885\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },

    # ---------- Other strong key dates ----------
    {
        "label": "1892-S Morgan Dollar",
        "est_value": 140.0,
        "pattern": re.compile(r"\b1892\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    # 1893-O ~120–180, conservative floor
    {
        "label": "1893-O Morgan Dollar",
        "est_value": 120.0,
        "pattern": re.compile(r"\b1893\s*[-/ ]?o\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    # 1894 (P) ~100–130
    {
        "label": "1894 Morgan Dollar",
        "est_value": 100.0,
        "pattern": re.compile(r"\b1894\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    # 1896-O / 1896-S ~100–150
    {
        "label": "1896-O Morgan Dollar",
        "est_value": 100.0,
        "pattern": re.compile(r"\b1896\s*[-/ ]?o\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1896-S Morgan Dollar",
        "est_value": 100.0,
        "pattern": re.compile(r"\b1896\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    # 1901-S ~300–450
    {
        "label": "1901-S Morgan Dollar",
        "est_value": 300.0,
        "pattern": re.compile(r"\b1901\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    # 1903-O / 1903-S ~180+ dealer buy
    {
        "label": "1903-O Morgan Dollar",
        "est_value": 180.0,
        "pattern": re.compile(r"\b1903\s*[-/ ]?o\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    {
        "label": "1903-S Morgan Dollar",
        "est_value": 180.0,
        "pattern": re.compile(r"\b1903\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },
    # 1904-S ~150–200
    {
        "label": "1904-S Morgan Dollar",
        "est_value": 150.0,
        "pattern": re.compile(r"\b1904\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["morgan"],
        "max_qty": 1,
    },

    # ---------- Fallback generic CC rule for other CC Morgans (1890-CC, 1891-CC, 1892-CC, etc.) ----------
    {
        "label": "Carson City Morgan Dollar",
        "est_value": 150.0,
        "pattern": re.compile(
            r"\b18[7-9]\d\s*[-/ ]?cc\b|\bcc\b\s*18[7-9]\d\b|\bcarson\s+city\b",
            re.IGNORECASE,
        ),
        "must_contain": ["morgan"],
        "max_qty": 3,
    },

    # ============================================================
    #                         PEACE DOLLARS
    # ============================================================

    {
        "label": "1921 Peace Dollar (High Relief)",
        "est_value": 100.0,
        "pattern": re.compile(r"\b1921\b", re.IGNORECASE),
        "must_contain": ["peace"],
        "max_qty": 2,
    },
    {
        "label": "1928 Peace Dollar (Key Date)",
        "est_value": 170.0,
        "pattern": re.compile(r"\b1928\b", re.IGNORECASE),
        "must_contain": ["peace"],
        "max_qty": 2,
    },

    # ============================================================
    #                   WALKING LIBERTY HALF DOLLARS
    # ============================================================

    # 1916-S (~80–100)
    {
        "label": "1916-S Walking Liberty Half",
        "est_value": 80.0,
        "pattern": re.compile(r"\b1916\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["walking", "half"],
        "max_qty": 2,
    },
    {
        "label": "1916-S Walker Half",
        "est_value": 80.0,
        "pattern": re.compile(r"\b1916\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["walker", "half"],
        "max_qty": 2,
    },

    # 1917-S (we can't distinguish obverse/reverse by title, but both are strong enough)
    {
        "label": "1917-S Walking Liberty Half",
        "est_value": 90.0,
        "pattern": re.compile(r"\b1917\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["walking", "half"],
        "max_qty": 2,
    },

    # 1921, 1921-D, 1921-S — all very strong in G–VG
    {
        "label": "1921 Walking Liberty Half",
        "est_value": 200.0,
        "pattern": re.compile(r"\b1921(?![0-9])", re.IGNORECASE),
        "must_contain": ["walking", "half"],
        "max_qty": 2,
    },
    {
        "label": "1921-D Walking Liberty Half",
        "est_value": 220.0,
        "pattern": re.compile(r"\b1921\s*[-/ ]?d\b", re.IGNORECASE),
        "must_contain": ["walking", "half"],
        "max_qty": 2,
    },
    {
        "label": "1921-S Walking Liberty Half",
        "est_value": 200.0,
        "pattern": re.compile(r"\b1921\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["walking", "half"],
        "max_qty": 2,
    },

    # 1938-D (~90–130)
    {
        "label": "1938-D Walking Liberty Half",
        "est_value": 90.0,
        "pattern": re.compile(r"\b1938\s*[-/ ]?d\b", re.IGNORECASE),
        "must_contain": ["walking", "half"],
        "max_qty": 2,
    },

    # ============================================================
    #                       BARBER HALF DOLLARS
    # ============================================================

    # Specific early key dates in G–VG
    {
        "label": "1892-O Barber Half",
        "est_value": 90.0,
        "pattern": re.compile(r"\b1892\s*[-/ ]?o\b", re.IGNORECASE),
        "must_contain": ["barber", "half"],
        "max_qty": 1,
    },
    {
        "label": "1892-O Micro O Barber Half",
        "est_value": 150.0,
        "pattern": re.compile(r"\b1892\s*[-/ ]?o\b", re.IGNORECASE),
        "must_contain": ["barber", "half", "micro"],
        "max_qty": 1,
    },
    {
        "label": "1892-S Barber Half",
        "est_value": 90.0,
        "pattern": re.compile(r"\b1892\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["barber", "half"],
        "max_qty": 1,
    },
    {
        "label": "1893 Barber Half",
        "est_value": 90.0,
        "pattern": re.compile(r"\b1893\b", re.IGNORECASE),
        "must_contain": ["barber", "half"],
        "max_qty": 1,
    },
    {
        "label": "1896-O Barber Half",
        "est_value": 120.0,
        "pattern": re.compile(r"\b1896\s*[-/ ]?o\b", re.IGNORECASE),
        "must_contain": ["barber", "half"],
        "max_qty": 1,
    },
    {
        "label": "1896-S Barber Half",
        "est_value": 100.0,
        "pattern": re.compile(r"\b1896\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["barber", "half"],
        "max_qty": 1,
    },
    {
        "label": "1897-O Barber Half",
        "est_value": 100.0,
        "pattern": re.compile(r"\b1897\s*[-/ ]?o\b", re.IGNORECASE),
        "must_contain": ["barber", "half"],
        "max_qty": 1,
    },
    {
        "label": "1897-S Barber Half",
        "est_value": 90.0,
        "pattern": re.compile(r"\b1897\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["barber", "half"],
        "max_qty": 1,
    },

    # Generic high-grade Barber halves (VF+ common dates that still hit $80+)
    {
        "label": "High-grade Barber Half Dollar",
        "est_value": 90.0,
        "pattern": re.compile(
            r"\b(vf|xf|ef|au|unc|uncirculated|bu|choice|gem|ms\d{2})\b",
            re.IGNORECASE,
        ),
        "must_contain": ["barber", "half"],
        "max_qty": 3,
    },

    # ============================================================
    #                  LIBERTY SEATED HALF DOLLARS
    # ============================================================

    # Ultra key — 1878-S (tiny population, five-figure coin)
    {
        "label": "1878-S Liberty Seated Half",
        "est_value": 15000.0,
        "pattern": re.compile(r"\b1878\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["seated", "half"],
        "max_qty": 1,
    },
    # Strong key — 1878-CC
    {
        "label": "1878-CC Liberty Seated Half",
        "est_value": 1400.0,
        "pattern": re.compile(r"\b1878\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["seated", "half"],
        "max_qty": 1,
    },
    # 1870-CC
    {
        "label": "1870-CC Liberty Seated Half",
        "est_value": 800.0,
        "pattern": re.compile(r"\b1870\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["seated", "half"],
        "max_qty": 1,
    },
    # 1874-CC
    {
        "label": "1874-CC Liberty Seated Half",
        "est_value": 800.0,
        "pattern": re.compile(r"\b1874\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["seated", "half"],
        "max_qty": 1,
    },
    # 1873-CC No Arrows
    {
        "label": "1873-CC No Arrows Liberty Seated Half",
        "est_value": 2000.0,
        "pattern": re.compile(r"\b1873\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["seated", "half", "no arrows"],
        "max_qty": 1,
    },
    # 1853-O No Arrows
    {
        "label": "1853-O No Arrows Liberty Seated Half",
        "est_value": 50000.0,
        "pattern": re.compile(r"\b1853\s*[-/ ]?o\b", re.IGNORECASE),
        "must_contain": ["seated", "half", "no arrows"],
        "max_qty": 1,
    },

    # ============================================================
    #                  LIBERTY SEATED DOLLARS (NEW)
    # ============================================================
    # These are full silver dollars (0.77344 oz), a separate series
    # from the halves. All values are conservative G–VG dealer floors.

    # Ultra-rare / six-figure
    {
        "label": "1870-S Liberty Seated Dollar",
        "est_value": 150000.0,
        "pattern": re.compile(r"\b1870\s*[-/ ]?s\b", re.IGNORECASE),
        "must_contain": ["seated", "dollar"],
        "max_qty": 1,
    },
    {
        "label": "1851 Original Liberty Seated Dollar",
        "est_value": 50000.0,
        "pattern": re.compile(r"\b1851\b", re.IGNORECASE),
        "must_contain": ["seated", "dollar", "original"],
        "max_qty": 1,
    },
    {
        "label": "1852 Original Liberty Seated Dollar",
        "est_value": 50000.0,
        "pattern": re.compile(r"\b1852\b", re.IGNORECASE),
        "must_contain": ["seated", "dollar", "original"],
        "max_qty": 1,
    },

    # Major keys ($1k+ dealer buy)
    {
        "label": "1872-CC Liberty Seated Dollar",
        "est_value": 1700.0,
        "pattern": re.compile(r"\b1872\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["seated", "dollar"],
        "max_qty": 1,
    },
    {
        "label": "1873-CC Liberty Seated Dollar",
        "est_value": 2500.0,
        "pattern": re.compile(r"\b1873\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["seated", "dollar"],
        "max_qty": 1,
    },
    {
        "label": "1858 Liberty Seated Dollar",
        "est_value": 800.0,
        "pattern": re.compile(r"\b1858\b", re.IGNORECASE),
        "must_contain": ["seated", "dollar"],
        "max_qty": 1,
    },

    # Strong keys ($300+ dealer buy)
    {
        "label": "1870-CC Liberty Seated Dollar",
        "est_value": 300.0,
        "pattern": re.compile(r"\b1870\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["seated", "dollar"],
        "max_qty": 1,
    },
    {
        "label": "1871-CC Liberty Seated Dollar",
        "est_value": 300.0,
        "pattern": re.compile(r"\b1871\s*[-/ ]?cc\b", re.IGNORECASE),
        "must_contain": ["seated", "dollar"],
        "max_qty": 1,
    },
]


def extract_display_time_for_subject(time_left):
    """Extract the clock portion from '(Today 05:40 PM)' if present."""
    if not time_left:
        return None
    m = re.search(r"\(.*?(\d{1,2}:\d{2}\s*[AP]M).*\)", time_left)
    if m:
        return m.group(1)
    return None


# ==========================
# ANALYZER CLASS
# ==========================

class EbayOfflineAnalyzer:
    def __init__(self):
        pass

    # ---------- Quantity Extraction ----------
    def extract_quantity(self, title):
        if not title:
            return 1
        t = title.lower()
        patterns = [
            r"\blot\s+of\s+(\d{1,3})(?!\.)\b",
            r"\broll\s+of\s+(\d{1,3})(?!\.)\b",
            r"\b(\d{1,3})(?!\.)\s+coins?\b",
            r"\b(\d{1,3})(?!\.)\s+pieces?\b",
            r"\((\d{1,3})(?!\.)\)",
            r"\b(\d{1,3})(?!\.)\s*[xX]\b",
            r"\b[xX]\s*(\d{1,3})(?!\.)\b",
            r"^\s*(\d{1,3})(?!\.)\b",
            r"\bqty[:\s]*(\d{1,3})(?!\.)\b",
            r"\b(\d{1,3})(?!\.)\s*pcs\b",
        ]
        for pat in patterns:
            m = re.search(pat, t)
            if m:
                qty = int(m.group(1))
                if 1 < qty <= 600:
                    return qty
        return 1

    # ---------- Time-left parsing ----------
    print("parse_time_left_to_minutes loaded")

    def parse_time_left_to_minutes(self, time_left_str):
        """Parse an eBay 'time left' string into total minutes."""
        if not time_left_str:
            return None

        s = time_left_str.lower()
        matches = re.findall(r"(\d+)\s*([dhm])", s)
        if not matches:
            return None

        total_minutes = 0
        for num_str, unit in matches:
            n = int(num_str)
            if unit == "d":
                total_minutes += n * 24 * 60
            elif unit == "h":
                total_minutes += n * 60
            elif unit == "m":
                total_minutes += n
        return total_minutes

    # ---------- Coin Type Detection ----------
    def detect_oz_per_coin(self, file_path, html_text):
        """
        Roughly detect the silver weight per coin for this file's listings.
        This is used for melt/pawn math ONLY; numismatic overrides ignore it.
        """
        fname = os.path.basename(file_path).lower()
        text = (html_text or "").lower()
        HALF = 0.36169
        FULL_DOLLAR = 0.77344
        EAGLE = 0.99

        def contains(word):
            return word in fname or word in text

        # First, explicitly recognize "half dollar" so we don't
        # accidentally treat Seated/LIBERTY DOLLAR pages as halves.
        half_tokens = ["half dollar", "half-dollar", "half_dollar", " 50c", " 50 c"]
        if any(contains(w) for w in half_tokens):
            return HALF

        # Silver dollars (Morgan, Peace, Seated Dollar, etc.)
        # If "dollar" appears WITHOUT "half", treat as full dollar.
        if "dollar" in fname or "dollar" in text:
            # Already ruled out "half dollar" above.
            return FULL_DOLLAR

        # Common half-dollar families (if the denomination isn't explicit)
        if any(
            contains(w)
            for w in [
                "barber",
                "franklin",
                "kennedy",
                "jfk",
                "walking",
                "walker",
                "columbian",
                "seated",  # typically half dollars if "dollar" isn't present
            ]
        ):
            return HALF

        # Silver eagles (~1 oz)
        if contains("silver eagle") or contains("american eagle"):
            return EAGLE

        # Fallback: assume half dollar weight
        return HALF

    # ---------- HTML Parsing ----------
    def parse_file(self, path):
        listings = parse_ebay_search_html(path)
        if not listings:
            return None, []

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                html_text = f.read()
        except Exception as e:
            print(f"Could not read file {path}: {e}")
            return None, []

        oz_per_coin = self.detect_oz_per_coin(path, html_text)
        for listing in listings:
            listing["quantity"] = self.extract_quantity(listing["title"])

        return oz_per_coin, listings

    # ---------- Profit Calculation ----------
    def calculate_silver_profit(self, listing, oz_per_coin, spot_price, pawn_payout_pct, bid_offset=0.0):
        """
        Base melt/pawn calculation. This is the "normal" silver logic:
        how much profit (and % margin) do we get if we cash out at a
        pawn/dealer that pays pawn_payout_pct of melt?
        """
        qty = listing.get("quantity", 1)
        total_oz = qty * oz_per_coin
        melt_value = total_oz * spot_price
        pawn_payout = melt_value * (pawn_payout_pct / 100.0)
        effective_cost = listing["price"] + bid_offset
        profit = pawn_payout - effective_cost
        margin_pct = (profit / effective_cost) * 100 if effective_cost > 0 else 0.0

        return {
            "quantity": qty,
            "total_oz": total_oz,
            "melt_value": melt_value,
            "pawn_payout": pawn_payout,
            "profit": profit,
            "margin_pct": margin_pct,
            "effective_cost": effective_cost,
        }

    # ---------- Numismatic Override Helpers ----------
    def estimate_numismatic_value(self, listing):
        """
        Try to match the listing title/quantity against NUMISMATIC_RULES.

        If a rule matches:
          - We assume the coin is at least est_value to a dealer
            in G–VG, *ignoring* melt.
          - We return {label, est_value} for downstream logic.

        If nothing matches, return None and the listing is treated
        purely as a melt-play.
        """
        title = (listing.get("title") or "").lower()
        qty = listing.get("quantity", 1)

        for rule in NUMISMATIC_RULES:
            max_qty = rule.get("max_qty")
            if max_qty is not None and qty > max_qty:
                continue

            must = rule.get("must_contain") or []
            # All tokens in must_contain must appear in the title
            if any(token.lower() not in title for token in must):
                continue

            if rule["pattern"].search(title):
                return {
                    "label": rule["label"],
                    "est_value": float(rule["est_value"]),
                }

        return None

    def is_numismatic_candidate_sane(self, listing, rule_info, calc):
        """
        Basic sanity filter so we don't treat obvious fakes / fantasies
        as huge HITs just because the date+mint matches a key.

        Examples rejected:
          - "Brand New 1870-CC Seated" from China at $25
          - Titles containing 'copy', 'replica', 'souvenir', etc.
          - Ultra-expensive dates (est_value >= $1000) that are
            raw, ungraded, and priced under ~15% of their floor.
        """
        title = (listing.get("title") or "").lower()
        est_value = float(rule_info.get("est_value", 0.0))
        effective_cost = float(calc.get("effective_cost", 0.0))

        # 1) Hard reject obvious reproductions
        bad_tokens = ["copy", "replica", "reproduction", "facsimile", "souvenir", "fantasy"]
        if any(tok in title for tok in bad_tokens):
            return False

        # 2) "Brand New" + 1800s date is extremely suspicious
        if "brand new" in title and re.search(r"\b18\d{2}\b", title):
            return False

        # 3) Extra guard for very high-end material (Seated keys, 1893-S, etc.)
        # If it's supposedly worth $1000+ but:
        #   - not slabbed/certified
        #   - AND the asking price is < 15% of that value,
        # then it's almost certainly counterfeit / fantasy and we ignore it.
        if est_value >= 1000.0:
            graders = ["pcgs", "ngc", "anacs", "icg", "graded", "certified"]
            has_grader = any(g in title for g in graders)

            if not has_grader:
                if effective_cost < est_value * 0.15:
                    return False

        return True

    def check_numismatic_override(self, listing, calc, config):
        """
        Decide if a listing should be promoted to a HIT via *numismatic* value.

        Important:
          - This NEVER removes an existing HIT.
          - It only ADDS HITs that would have been misses on melt alone.
          - We compare our conservative est_value (dealer cash) against
            the effective_cost to see if there's a strong margin.
        """
        info = self.estimate_numismatic_value(listing)
        if not info:
            return False, None

        est_value = info["est_value"]
        effective_cost = calc["effective_cost"]

        if effective_cost <= 0:
            return False, None

        # sanity check to avoid obvious fakes / fantasies
        if not self.is_numismatic_candidate_sane(listing, info, calc):
            return False, None

        profit = est_value - effective_cost
        if profit <= 0:
            # No point overriding if you're already upside down vs dealer cash
            return False, None

        margin_pct = (profit / effective_cost) * 100.0

        # Numismatic overrides do NOT require a minimum margin.
        # Any positive profit vs dealer est_value is enough.
        # (Sanity checks above already protect against fakes & fantasy listings.)

        info.update(
            {
                "profit": profit,
                "margin_pct": margin_pct,
            }
        )
        # Attach to listing so print/email layers can identify that
        # this coin is a HIT because of numismatic value, not melt.
        listing["numismatic_override"] = info
        return True, info

    # ---------- High-level File Analysis ----------
    def analyze_file(self, path, config):
        oz_per_coin, listings = self.parse_file(path)
        if oz_per_coin is None or not listings:
            return oz_per_coin, [], []

        # Apply filters
        listings = self.filter_by_quantity(listings, config.get("min_quantity"))
        listings = self.filter_by_blacklist(listings, config.get("blacklist"))
        listings = self.filter_by_time_left(listings, config.get("max_time_hours"))

        filename_label = os.path.basename(path)

        hits = []
        for listing in listings:
            calc = self.calculate_silver_profit(
                listing,
                oz_per_coin,
                config["spot_price"],
                config["pawn_payout_pct"],
                config.get("bid_offset", 0.0),
            )
            # cache calc for display
            listing["_silver_calc"] = calc

            # Normal melt-based HIT
            silver_hit = (
                config["min_margin"] <= calc["margin_pct"] <= config["max_margin"]
            )

            # Numismatic override HIT (using est dealer value instead of melt)
            numis_hit, _ = self.check_numismatic_override(listing, calc, config)

            if silver_hit or numis_hit:
                hits.append((os.path.basename(path), listing, calc, oz_per_coin))

        # Print per-file table (old behavior), but now aware of overrides.
        # NOTE: the on-screen table shows melt margin in the "Found" column;
        # if a coin is only a HIT because of numismatic_override, it will
        # still show "HIT!" even with a negative melt margin.
        self.print_silver_table(filename_label, listings, oz_per_coin, config)

        return oz_per_coin, listings, hits

    # ---------- Filters & math ----------
    def filter_by_quantity(self, listings, min_quantity):
        if not min_quantity:
            return listings

        filtered = []
        for listing in listings:
            qty = self.extract_quantity(listing["title"])
            if qty >= min_quantity:
                listing["quantity"] = qty
                filtered.append(listing)
        return filtered

    def filter_by_blacklist(self, listings, blacklist):
        if not blacklist:
            return listings
        bl = [w.lower() for w in blacklist]
        filtered = []
        for listing in listings:
            tl = listing["title"].lower()
            if not any(word in tl for word in bl):
                filtered.append(listing)
        return filtered

    def filter_by_time_left(self, listings, max_hours):
        if not max_hours:
            return listings
        max_minutes = max_hours * 60.0
        filtered = []
        for listing in listings:
            tl = listing.get("time_left")
            if not tl:
                continue
            mins = self.parse_time_left_to_minutes(tl)
            if mins is None:
                continue
            if mins <= max_minutes:
                filtered.append(listing)
        return filtered

    # ---------- Display ----------
    def print_silver_table(self, filename_label, listings, oz_per_coin, config):
        """
        Console table output.

        Note:
          - 'Found' always reflects MELT margin only.
          - 'Hit?' will be 'HIT!' if either:
             * melt margin is in [MIN, MAX], OR
             * numismatic_override is attached to the listing.
          - That means you can visually spot numismatic-only HITs as
            cases where Found is negative but Hit? == 'HIT!'.
        """
        if not listings:
            print(f"  [{filename_label}] No listings to display after filters.\n")
            return

        print(f"\n=== {filename_label} ===")
        target_str = f"{config['min_margin']:.0f}-{config['max_margin']:.0f}%"
        header = (
            f"{'Target':<9} | {'Found':<7} | {'Hit?':<8} | "
            f"{'Price':<10} | {'QTY':<5} | {'Time Left':<30} | Title"
        )
        print("  " + header)
        print("  " + "-" * len(header))

        for listing in listings:
            calc = listing.get("_silver_calc") or self.calculate_silver_profit(
                listing,
                oz_per_coin,
                config["spot_price"],
                config["pawn_payout_pct"],
                config.get("bid_offset", 0.0),
            )

            found_str = f"{calc['margin_pct']:.1f}%"

            silver_hit = (
                config["min_margin"] <= calc["margin_pct"] <= config["max_margin"]
            )
            numis_hit = bool(listing.get("numismatic_override"))

            hit_label = "HIT!" if (silver_hit or numis_hit) else "Miss"

            total_price = listing["price"]
            price_str = f"${total_price:.2f}"
            qty = calc["quantity"]
            time_left = listing.get("time_left") or "-"
            title = listing["title"]
            title_disp = title if len(title) <= 45 else title[:45] + "…"

            row = (
                f"{target_str:<9} | {found_str:<7} | {hit_label:<8} | "
                f"{price_str:<10} | {qty:<5} | {time_left:<30} | {title_disp}"
            )
            print("  " + row)

        print("  " + "-" * len(header) + "\n")


# ==========================
# EMAIL BODY BUILDER
# ==========================

def build_consolidated_hits_body(hits, config):
    """
    Build a consolidated HTML email body listing all HITs across files,
    using the newer, richer layout (current profit + profit at recommended max,
    recommended max bids, etc.).

    Important:
      - Melt math (pawn payout, recommended max) is *always* based on silver
        content.
      - When a numismatic_override is present, we ALSO show a separate block
        explaining the estimated dealer value and margin vs that value.
      - This makes it obvious when you're chasing a coin for its KEY DATE
        rather than its bullion content.
    """
    if not hits:
        # Keep it simple if no hits
        return "<html><body><pre>No HITs found.</pre></body></html>"

    # Sort hits by absolute end time if possible, otherwise by minutes-left
    def sort_key(entry):
        filename_label, listing, calc, oz_per_coin = entry
        tl = listing.get("time_left")

        # Prefer the explicit end time in parentheses (Today 08:35 PM, etc.)
        dt = parse_end_datetime_from_time_left(tl)
        if dt is not None:
            return dt

        # Fallback: approximate using "Xh Ym" relative minutes
        mins = parse_time_left_to_minutes_for_sort(tl)
        return datetime.now() + timedelta(minutes=mins)

    hits_sorted = sorted(hits, key=sort_key)

    lines = []
    lines.append("<html><body><div style='font-family: monospace; white-space: pre;'>")

    # Header block
    lines.append("EBAY OFFLINE SILVER HITS")
    lines.append("================================")
    lines.append(
        f"Spot: ${config['spot_price']:.2f} | Pawn: {config['pawn_payout_pct']:.1f}%"
    )
    lines.append(f"Bid offset: ${config.get('bid_offset', 0.0):.2f}")
    lines.append(
        f"Target margin: {config['min_margin']:.1f}%–{config['max_margin']:.1f}%"
    )
    if config.get("max_time_hours") is not None:
        lines.append(f"Max time left: {config['max_time_hours']:.2f} hours")
    lines.append("")
    lines.append(f"Total HITs: {len(hits_sorted)}")
    lines.append("----------------------------------------")
    lines.append("")

    # For recommended max bid math (melt-based)
    min_margin_pct = float(config.get("min_margin", 0.0))
    m = max(0.0, min_margin_pct / 100.0)

    # Render each hit using the gold-standard style
    for idx, (filename_label, listing, calc, oz_per_coin) in enumerate(hits_sorted, start=1):
        safe_fname = html_lib.escape(filename_label)
        safe_title = html_lib.escape(listing["title"])

        item_price = listing.get("item_price", listing["price"])
        shipping = listing.get("shipping", 0.0)
        price_total = listing["price"]
        time_left = listing.get("time_left") or "N/A"
        pawn_payout = calc["pawn_payout"]

        # Recommended max total for desired margin (still melt-based)
        if m > 0:
            rec_max_total = pawn_payout / (1.0 + m)
        else:
            rec_max_total = pawn_payout
        rec_max_total = round(rec_max_total, 2)
        rec_max_item = max(0.0, rec_max_total - shipping)

        profit_current = calc["profit"]
        margin_current = calc["margin_pct"]
        profit_at_max = pawn_payout - rec_max_total
        margin_at_max = (profit_at_max / rec_max_total) * 100 if rec_max_total > 0 else 0.0

        lines.append(f"#{idx} [{safe_fname}]")

        # --- Numismatic override display (if applicable) ---
        numis = listing.get("numismatic_override")
        if numis:
            # This block explains *why* the coin is a HIT independent of melt:
            # we believe a dealer will pay at least est_value in G–VG, and
            # your buy price leaves a strong profit vs that floor.
            safe_label = html_lib.escape(numis.get("label", "Numismatic override"))
            lines.append(f"Numismatic override: {safe_label}")
            lines.append(
                f"Est. dealer value: ${numis['est_value']:.2f} "
                f"(est. profit: ${numis['profit']:.2f}, "
                f"{numis['margin_pct']:.1f}% margin vs dealer)"
            )
            lines.append(
                "Note: Numismatic values ignore melt and use conservative "
                "G–VG dealer cash estimates."
            )

        lines.append(
            f"Current Profit: ${profit_current:.2f} ({margin_current:.1f}% margin)"
        )
        lines.append(
            f"Profit at Recommended Max: ${profit_at_max:.2f} ({margin_at_max:.1f}% margin)"
        )
        lines.append(
            f"Recommended max total (incl. ship): ${rec_max_total:.2f}"
        )
        lines.append(
            f"Recommended max bid (item only):   ${rec_max_item:.2f}"
        )

        # Add earliest-ending clock to the Title line
        clock = extract_display_time_for_subject(listing.get("time_left") or "")
        clock_str = f" ({clock})" if clock else ""
        lines.append(f"Title: {safe_title}{clock_str}")
        lines.append(
            f"Current Total: ${price_total:.2f} (item ${item_price:.2f} + ship ${shipping:.2f})"
        )
        lines.append(
            f"Qty: {calc['quantity']} | oz/coin: {oz_per_coin:.5f} | Total oz: {calc['total_oz']:.2f}"
        )
        lines.append(
            f"Melt: ${calc['melt_value']:.2f} | Pawn: ${pawn_payout:.2f}"
        )
        lines.append(f"Time left: {time_left}")
        link = listing.get("link")
        if link:
            if not link.startswith("http"):
                link = "https://www.ebay.com" + link
            safe_link = html_lib.escape(link, quote=True)
            lines.append(f"Link: <a href=\"{safe_link}\">Link to Listing</a>")
        lines.append("----------------------------------------")

    lines.append(
        f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    lines.append("</div></body></html>")

    return "\n".join(lines)


# ==========================
# USER FILTER PROMPTS
# ==========================

def prompt_filters_from_user():
    """
    Ask user for min quantity and blacklist terms.
    Returns:
      (min_quantity, blacklist_list)
    """
    print("\nFILTER CONFIG (press Enter to accept defaults)")

    # Min quantity
    min_qty = None
    min_qty_str = input("Minimum quantity of coins per listing (blank = no minimum): ").strip()
    if min_qty_str:
        try:
            min_qty = int(min_qty_str)
        except ValueError:
            print("  Invalid number, ignoring and using no minimum.")
            min_qty = None

    # Blacklist
    blacklist = []
    print("\nEnter blacklist keywords one at a time (e.g. 'proof', 'commemorative').")
    print("Press Enter on a blank line when you're done:")
    while True:
        term = input("> ").strip()
        if not term:
            break
        blacklist.append(term)

    return min_qty, blacklist


def prompt_loop_interval():
    """
    Ask user for loop interval in minutes.
    """
    default_interval = 1.1
    s = input(f"\nCheck interval in minutes (default {default_interval}): ").strip()
    if not s:
        return default_interval
    try:
        val = float(s)
        if val <= 0:
            raise ValueError()
        return val
    except ValueError:
        print("  Invalid interval, using default.")
        return default_interval


# ==========================
# ENTRYPOINT
# ==========================

def silver_filename_filter(filename: str) -> bool:
    """Detect if a file is for the silver monitor."""
    name = filename.lower()
    keywords = [
        "silver",
        "morgan",
        "walker",
        "franklin",
        "kennedy",
        "jfk",
        "half_dollar",
        "half-dollar",
        "seated",       # catches Seated Liberty Dollar / Half pages
    ]
    return any(k in name for k in keywords)


def main():
    # Base config from constants
    config = {
        "market_name": "Silver",
        "spot_price": SPOT_PRICE,
        "pawn_payout_pct": PAWN_PAYOUT_PCT,
        "min_margin": MIN_MARGIN,
        "max_margin": MAX_MARGIN,
        "max_time_hours": MAX_TIME_HOURS,
        "min_quantity": None,
        "blacklist": [],
        "bid_offset": BID_OFFSET,
    }

    # Prompt user for filters
    min_qty, blacklist = prompt_filters_from_user()
    config["min_quantity"] = min_qty
    config["blacklist"] = blacklist

    # Prompt for loop interval
    check_interval_min = prompt_loop_interval()

    analyzer = EbayOfflineAnalyzer()

    run_monitor(
        folder_path=FOLDER_PATH,
        analyzer=analyzer,
        config=config,
        build_email_body=build_consolidated_hits_body,
        mailgun_config=MAILGUN_CONFIG,
        check_interval_min=check_interval_min,
        filename_filter=silver_filename_filter,
    )


if __name__ == "__main__":
    main()
