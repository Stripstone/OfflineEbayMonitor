# numismatic_rules.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple
import re

# -----------------------------
# Public model
# -----------------------------

@dataclass(frozen=True)
class NumismaticOverride:
    coin_type: str
    year: int
    mint: str
    display_name: str


# -----------------------------
# Helpers
# -----------------------------

_YEAR_RE = re.compile(r"\b(17\d{2}|18\d{2}|19\d{2}|20\d{2})\b")
# Common mint markers in titles: "1906 d", "1884-cc", "1892 S", "1908 - O"
_MINT_RE = re.compile(r"(?i)(?:^|[\s\-])\s*(cc|[dso])\b")

# coin type keyword patterns -> canonical coin_type used by the project
_COIN_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\bmorgan\b"), "Morgan Dollar"),
    (re.compile(r"(?i)\bpeace\b"), "Peace Dollar"),
    (re.compile(r"(?i)\bbarber\b.*\bhalf\b|\bbarber\s*half\b"), "Barber Half"),
    (re.compile(r"(?i)\bseated\b.*\bliberty\b.*\bhalf\b"), "Seated Liberty Half"),
    (re.compile(r"(?i)\bseated\b.*\bliberty\b.*\bdollar\b"), "Seated Liberty Dollar"),
    (re.compile(r"(?i)\bwalking\b.*\bliberty\b.*\bhalf\b|\bwalker\b.*\bhalf\b"), "Walking Liberty Half"),
]

# Some listings omit mint; treat as Philadelphia ("P") for key stability.
_DEFAULT_MINT = "P"


def _norm_mint(m: str) -> str:
    m = (m or "").strip().upper()
    if not m:
        return _DEFAULT_MINT
    # Normalize common variants
    if m in {"PHILADELPHIA"}:
        return "P"
    if m in {"O", "D", "S", "P", "CC"}:
        return m
    # If someone passes "C C" or weird spacing
    m = m.replace(" ", "")
    if m in {"CC"}:
        return "CC"
    return m


# -----------------------------
# Public API
# -----------------------------

def detect_coin_identity(title: str) -> Optional[Tuple[str, int, str]]:
    """Best-effort identity from a listing title. Never raises."""
    try:
        t = (title or "").strip()
        if not t:
            return None

        coin_type: Optional[str] = None
        for pat, ctype in _COIN_PATTERNS:
            if pat.search(t):
                coin_type = ctype
                break
        if not coin_type:
            return None

        ym = _YEAR_RE.search(t)
        if not ym:
            return None
        year = int(ym.group(1))

        mm = _MINT_RE.search(t)
        mint = _norm_mint(mm.group(1) if mm else _DEFAULT_MINT)

        # Reject modern/non-classic matches and common non-numismatic cues.
        tl = t.lower()
        if 'proof' in tl or 'replica' in tl or 'copy' in tl:
            return None
        # Date-range validation to keep numismatic logic 'classic types only'.
        if coin_type == 'Morgan Dollar' and not (1878 <= year <= 1921):
            return None
        if coin_type == 'Peace Dollar' and not (1921 <= year <= 1935):
            return None
        if coin_type == 'Barber Half' and not (1892 <= year <= 1915):
            return None
        if coin_type == 'Seated Liberty Half' and not (1839 <= year <= 1891):
            return None
        if coin_type == 'Seated Liberty Dollar' and not (1840 <= year <= 1873):
            return None
        if coin_type == 'Walking Liberty Half' and not (1916 <= year <= 1947):
            return None

        return coin_type, year, mint
    except Exception:
        return None


def make_benchmark_key(coin_type: str, year: int, mint: str) -> str:
    """Canonical key format used across defaults + EMA store."""
    try:
        return f"{str(coin_type)}|{int(year)}|{_norm_mint(str(mint))}"
    except Exception:
        # Absolute fallback: keep it non-throwing
        return f"{coin_type}|{year}|{mint}"


def check_numismatic_override(*args: Any, **kwargs: Any) -> Optional[NumismaticOverride]:
    """
    Backward-compatible override detector.

    Supported call patterns:
      - check_numismatic_override(title: str)
      - check_numismatic_override(listing) where listing has .title
      - check_numismatic_override(listing, silver_calc) (ignored second arg)

    Returns:
      NumismaticOverride or None
    """
    title = None
    try:
        if args:
            a0 = args[0]
            if isinstance(a0, str):
                title = a0
            elif hasattr(a0, "title"):
                title = getattr(a0, "title", None)
        if title is None:
            title = kwargs.get("title")
        ident = detect_coin_identity(title or "")
        if not ident:
            return None
        coin_type, year, mint = ident
        display = f"{coin_type} {year}-{mint}"
        return NumismaticOverride(coin_type=coin_type, year=year, mint=mint, display_name=display)
    except Exception:
        return None
