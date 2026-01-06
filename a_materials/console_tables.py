# console_tables.py
"""
CONSOLE TABLE RENDERING (USER-FACING UX)

Requirements:
- Show only listings within max time window (filtering happens upstream)
- Table is readability-first, fixed columns, separated by ' | '
- Fixed columns sized to fit a typical default Windows console window (~120 chars)
- No wrapping past Title (truncate)
- No business logic beyond safe formatting/normalization
"""

from __future__ import annotations

from typing import Iterable, Any


def _truncate(text: str, width: int) -> str:
    s = "" if text is None else str(text)
    return s if len(s) <= width else s[: max(0, width - 3)] + "..."


def _fmt_row(values, widths):
    out = []
    for v, w in zip(values, widths):
        out.append(_truncate(v, w).ljust(w))
    return " | ".join(out)


def _as_calc_dict(silver_calc: Any) -> dict:
    """
    Normalizes silver_calc to a dict so user-facing code never crashes.
    Accepts:
      - dict
      - list of dict (takes first dict)
      - anything else -> {}
    """
    if isinstance(silver_calc, dict):
        return silver_calc
    if isinstance(silver_calc, list):
        for item in silver_calc:
            if isinstance(item, dict):
                return item
        return {}
    return {}


def _is_hit(e: Any) -> bool:
    """
    Supports both:
      - e.is_hit
      - e.silver_hit / e.numis_hit
    """
    if hasattr(e, "is_hit"):
        return bool(getattr(e, "is_hit"))
    silver_hit = bool(getattr(e, "silver_hit", False))
    numis_hit = bool(getattr(e, "numis_hit", False))
    return silver_hit or numis_hit


def _is_prospect(e: Any) -> bool:
    """Best-effort detection of a numismatic prospect (PROS).

    We keep this purely user-facing and tolerant of interface drift:
    - Prefer e.is_prospect if present
    - Else fall back to e.silver_calc['is_prospect']
    """
    if hasattr(e, "is_prospect"):
        return bool(getattr(e, "is_prospect"))
    sc = _as_calc_dict(getattr(e, "silver_calc", None))
    return bool(sc.get("is_prospect"))


def print_hit_miss_table(evaluated: Iterable[Any]) -> None:
    """
    evaluated: iterable of evaluated entries
    Expected minimum fields:
      e.listing.total_price
      e.listing.quantity
      e.listing.time_left
      e.listing.title
      e.silver_calc (dict OR list[dict])
      e.is_hit OR (e.silver_hit/e.numis_hit)
    """

    rows = []

    for e in evaluated:
        lst = getattr(e, "listing", None)
        if lst is None:
            continue

        sc = _as_calc_dict(getattr(e, "silver_calc", None))

        if _is_hit(e):
            hit_label = "HIT! --"
        elif _is_prospect(e):
            hit_label = "PROS --"
        else:
            hit_label = "Miss"

        # For PROS (numismatic prospects), display dealer-based economics
        if hit_label == "PROS":
            found = f"{float(sc.get('dealer_margin_pct', 0.0)):.1f}%"
            profit = f"${float(sc.get('dealer_profit', 0.0)):.2f}"
            recmax = f"${float(sc.get('dealer_rec_max_total', 0.0)):.2f}"
        else:
            found = f"{float(sc.get('margin_pct', 0.0)):.1f}%"
            profit = f"${float(sc.get('profit', 0.0)):.2f}"
            recmax = f"${float(sc.get('rec_max_total', 0.0)):.2f}"

        total = f"${float(getattr(lst, 'total_price', 0.0)):.2f}"
        qty = str(sc.get("quantity", getattr(lst, "quantity", 1) or 1))
        tleft = getattr(lst, "time_left", "") or ""
        title = getattr(lst, "title", "") or ""

        # Column order per request:
        # Title | HIT!/Miss | Found | Profit | RecMax | Total | Qty | Time Left
        rows.append([title, hit_label, found, profit, recmax, total, qty, tleft])

    if not rows:
        print("HIT!/Miss\n(none)\n")
        return

    headers = [
        "Title",
        "HIT!/Miss",
        "Found",
        "Profit",
        "RecMax",
        "Total",
        "Qty",
        "Time Left",
    ]

    # Target ~120 chars total, including separators (" | " = 3 chars each)
    widths = [27, 9, 7, 9, 10, 8, 3, 25]

    print("\nHIT!/Miss")
    print(_fmt_row(headers, widths))
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))

    for r in rows:
        print(_fmt_row(r, widths))

    print()
