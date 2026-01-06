# email_format.py
"""EMAIL FORMAT (USER-FACING CONTRACT)

This module renders the *exact* plain-text email layout that has been locked
as a UX contract for this project.

Non-negotiables:
- Subject: "HH:MM AM/PM Offline eBay Silver HITS (N new)"
- Body:
    EBAY OFFLINE SILVER HITS
    ================================
    Spot / Pawn / Bid offset / Target margin / Max time left
    Total HITs: <HIT + PROS>
    ----------------------------------------
    #<n> [<source_file>]
    Title: ...
    (melt OR numismatic prospect block)
    Links: Ebay Listing - Online: <url> | Ebay Sold Page - Online: <url> [| CoinBook - Online: <url>]
    ----------------------------------------
    Generated at: YYYY-MM-DD HH:MM:SS

No debug lines, no extra fields.
"""

from __future__ import annotations

from datetime import datetime
import html as _html
from typing import Any, List, Optional
from urllib.parse import quote_plus


def _fmt_money(x: Any) -> str:
    try:
        return f"${float(x):.2f}"
    except Exception:
        return "$0.00"


def _fmt_pct(x: Any) -> str:
    try:
        return f"{float(x):.1f}%"
    except Exception:
        return "0.0%"


def _fmt_float(x: Any, decimals: int) -> str:
    try:
        return f"{float(x):.{decimals}f}"
    except Exception:
        return f"{0.0:.{decimals}f}"



def _get_current_total_prices(listing: Any, silver_calc: dict) -> tuple[float, float, float]:
    """Return (current_total, item_price, shipping) for a listing.

    This is the contract source of truth for 'Current Total:' and any
    profit-vs-current computations that appear elsewhere in the email.
    """
    item_price = getattr(listing, "item_price", None)
    shipping = getattr(listing, "shipping", None)
    total_price = getattr(listing, "total_price", None)

    try:
        total_price_f = float(total_price) if total_price is not None else None
    except Exception:
        total_price_f = None
    try:
        item_price_f = float(item_price) if item_price is not None else None
    except Exception:
        item_price_f = None
    try:
        shipping_f = float(shipping) if shipping is not None else None
    except Exception:
        shipping_f = None

    if total_price_f is None:
        total_price_f = (item_price_f or 0.0) + (shipping_f or 0.0)
    if item_price_f is None:
        item_price_f = max(0.0, total_price_f - (shipping_f or 0.0))
    if shipping_f is None:
        shipping_f = max(0.0, total_price_f - (item_price_f or 0.0))

    return float(total_price_f), float(item_price_f), float(shipping_f)

def _append_post_recmax_details(
    lines: List[str],
    *,
    listing: Any,
    silver_calc: dict,
    spot_price: float,
    pawn_payout_pct: float,
) -> None:
    """Append the locked per-entry details block.

    Placement contract:
    - BELOW "Recommended max bid (item only): ..."
    - ABOVE the Links line

    Layout contract:
        Current Total: $.. (item $.. + ship $..)
        Qty: N | oz/coin: 0.77344 | Total oz: 0.77
        Melt: $.. | Pawn payout: $..
        Time left: ...
    """
    item_price = getattr(listing, "item_price", None)
    shipping = getattr(listing, "shipping", None)
    total_price = getattr(listing, "total_price", None)
    qty = getattr(listing, "quantity", None)
    time_left = getattr(listing, "time_left", "") or ""

    # Prefer the already-calculated silver metrics when available.
    if not isinstance(silver_calc, dict):
        silver_calc = {}

    qty = silver_calc.get("quantity", qty)
    oz_per = silver_calc.get("oz_per_coin", getattr(listing, "oz_per_coin", None))
    total_oz = silver_calc.get("total_oz")
    melt_value = silver_calc.get("melt_value")
    melt_payout = silver_calc.get("melt_payout")

    # Defensive fallbacks
    try:
        qty_i = int(qty) if qty is not None else 1
        if qty_i < 1:
            qty_i = 1
    except Exception:
        qty_i = 1

    try:
        oz_per_f = float(oz_per) if oz_per is not None else 0.0
    except Exception:
        oz_per_f = 0.0

    if total_oz is None:
        total_oz = oz_per_f * qty_i

    if melt_value is None:
        try:
            melt_value = float(total_oz) * float(spot_price)
        except Exception:
            melt_value = 0.0

    if melt_payout is None:
        try:
            melt_payout = float(melt_value) * (float(pawn_payout_pct) / 100.0)
        except Exception:
            melt_payout = 0.0

    # Prices
    try:
        total_price_f = float(total_price) if total_price is not None else None
    except Exception:
        total_price_f = None
    try:
        item_price_f = float(item_price) if item_price is not None else None
    except Exception:
        item_price_f = None
    try:
        shipping_f = float(shipping) if shipping is not None else None
    except Exception:
        shipping_f = None

    # Ensure all three totals are present for the line
    if total_price_f is None:
        total_price_f = (item_price_f or 0.0) + (shipping_f or 0.0)
    if item_price_f is None:
        item_price_f = max(0.0, total_price_f - (shipping_f or 0.0))
    if shipping_f is None:
        shipping_f = max(0.0, total_price_f - (item_price_f or 0.0))

    lines.append(
        f"Current Total: {_fmt_money(total_price_f)} (item {_fmt_money(item_price_f)} + ship {_fmt_money(shipping_f)})"
    )
    lines.append(
        f"Qty: {qty_i} | oz/coin: {_fmt_float(oz_per_f, 5)} | Total oz: {_fmt_float(total_oz, 2)}"
    )
    lines.append(f"Melt: {_fmt_money(melt_value)} | Pawn payout: {_fmt_money(melt_payout)}")
    if time_left:
        lines.append(f"Time left: {time_left}")

def _sold_link_for(title: str) -> str:
    q = quote_plus((title or "").strip())
    return f"https://www.ebay.com/sch/i.html?_nkw={q}&LH_Sold=1&LH_Complete=1"


def build_email_subject(earliest_time_str: str, n_new: int, market_name: str = "Silver") -> str:
    return f"{earliest_time_str} Offline eBay {market_name} HITS ({n_new} new)"


def build_email_body(hits: List[Any], *, spot_price: Optional[float] = None) -> str:
    """Render the locked plain-text email body.

    `hits` should already be filtered to *email-worthy* entries (HITs + PROS).
    """
    import config  # local import; treated as a stable project module

    if spot_price is None:
        spot_price = float(getattr(config, "SPOT_PRICE", 0.0) or 0.0)

    pawn_pct = float(getattr(config, "PAWN_PAYOUT_PCT", 0.0) or 0.0)
    bid_offset = float(getattr(config, "BID_OFFSET", 0.0) or 0.0)
    min_margin = float(getattr(config, "MIN_MARGIN_PCT", 0.0) or 0.0)
    max_margin = float(getattr(config, "MAX_MARGIN_PCT", 0.0) or 0.0)
    max_time = getattr(config, "MAX_TIME_HOURS", None)
    max_time_str = "None" if max_time is None else f"{float(max_time):.2f} hours"

    lines: List[str] = []

    # Header block (exact structure)
    lines.append("EBAY OFFLINE SILVER HITS")
    lines.append("================================")
    lines.append(f"Spot: {_fmt_money(spot_price)} | Pawn: {pawn_pct:.1f}%")
    lines.append(f"Bid offset: {_fmt_money(bid_offset)}")
    lines.append(f"Target margin: {min_margin:.1f}%–{max_margin:.1f}%")
    lines.append(f"Max time left: {max_time_str}")
    lines.append(f"Total HITs: {len(hits)}")
    lines.append("----------------------------------------")

    for idx, e in enumerate(hits, start=1):
        lst = getattr(e, "listing", None)
        if lst is None:
            continue

        title = getattr(lst, "title", "") or ""
        source_file = getattr(lst, "source_file", "unknown") or "unknown"

        sc = getattr(e, "silver_calc", {})
        if not isinstance(sc, dict):
            sc = {}

        # Listing header
        lines.append(f"#{idx} [{source_file}]")
        lines.append(f"Title: {title}")

        is_prospect = bool(sc.get("is_prospect"))
        has_override = bool(sc.get("numismatic_override"))

        # --- Numismatic prospect block
        if is_prospect and has_override:
            override_label = str(sc.get("numismatic_override") or "")
            fmv_floor = sc.get("fmv_floor")
            fmv_source = str(sc.get("fmv_source") or "")
            payout_pct = float(getattr(config, "NUMISMATIC_PAYOUT_PCT", 0.0) or 0.0)
            dealer_value = sc.get("dealer_value")
            dealer_profit = sc.get("dealer_profit")
            dealer_margin = sc.get("dealer_margin_pct")

            dealer_rec_total = sc.get("dealer_rec_max_total")
            dealer_rec_item = sc.get("dealer_rec_max_item")
            dealer_profit_at_rec = sc.get("dealer_profit_at_rec_max")
            dealer_margin_at_rec = sc.get("dealer_margin_at_rec_max")

            lines.append(f"\n<<<<Numismatic override: {override_label}")

            current_total_f, _, _ = _get_current_total_prices(lst, sc)

            try:
                dealer_profit_vs_current = float(dealer_value) - float(current_total_f)
            except Exception:
                dealer_profit_vs_current = 0.0
            try:
                dealer_margin_vs_current_pct = (dealer_profit_vs_current / float(current_total_f)) * 100.0
            except Exception:
                dealer_margin_vs_current_pct = 0.0
                
            lines.append(
                f"Est. dealer payout (@{payout_pct:.1f}%): {_fmt_money(dealer_value)} "
                f"(est. profit: {_fmt_money(dealer_profit_vs_current)}, {_fmt_pct(dealer_margin_vs_current_pct)} margin vs curent)"
            )
            
            if fmv_floor is not None:
                lines.append(f"FMV floor (G–VG): {_fmt_money(fmv_floor)} | Source: {fmv_source}")

            
            # Current profit vs pawn payout (melt-based)
            profit = sc.get("profit")
            margin = sc.get("margin_pct")
            profit_at_rec = sc.get("profit_at_rec_max")
            margin_at_rec = sc.get("margin_at_rec_max")
            rec_total = sc.get("rec_max_total")
            rec_item = sc.get("rec_max_item")

            lines.append(
                f"\nCurrent Profit: {_fmt_money(profit)} ({_fmt_pct(margin)} margin)"
            )

            # Recommended max is ALWAYS melt/pawn-based (never FMV/dealer-based)
            lines.append(
                f"RecMaxTotal (incl. ship): {_fmt_money(rec_total)} |  {_fmt_money(profit_at_rec)} ({_fmt_pct(margin_at_rec)} margin vs pawn)"
            )
            lines.append(f"RecMaxBid (item only): {_fmt_money(rec_item)}")
            _append_post_recmax_details(
                lines,
                listing=lst,
                silver_calc=sc,
                spot_price=float(spot_price),
                pawn_payout_pct=float(pawn_pct),
            )
            
        # --- Melt HIT block
        else:
            profit = sc.get("profit")
            margin = sc.get("margin_pct")
            profit_at_rec = sc.get("profit_at_rec_max")
            margin_at_rec = sc.get("margin_at_rec_max")
            rec_total = sc.get("rec_max_total")
            rec_item = sc.get("rec_max_item")

            lines.append(f"Current Profit: {_fmt_money(profit)} ({_fmt_pct(margin)} margin)")
            lines.append(
                f"ProfitAtMax: {_fmt_money(profit_at_rec)} ({_fmt_pct(margin_at_rec)} margin)"
            )
            lines.append(f"RecMaxTotal (incl. ship): {_fmt_money(rec_total)}")
            lines.append(f"RecMaxBid (item only): {_fmt_money(rec_item)}")

            _append_post_recmax_details(
                lines,
                listing=lst,
                silver_calc=sc,
                spot_price=float(spot_price),
                pawn_payout_pct=float(pawn_pct),
            )

        # Links line (exact label + separator contract)
        listing_url = (
            getattr(lst, "url", None)
            or getattr(lst, "link", None)
            or ""
        )
        sold_url = _sold_link_for(title)
        coinbook_url = sc.get("coinbook_url") if (is_prospect and has_override) else None

        # We render links as HTML anchors at the end. Insert a sentinel here so
        # the plain-text layout remains stable while still getting clickable
        # shorthand labels.
        lines.append(f"__LINKS__{idx-1}")

        lines.append("----------------------------------------")

    lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # -----------------------------
    # HTML render (preserve layout + make links clickable)
    # -----------------------------
    # We render as HTML because the email transport layer sends HTML bodies.
    # Using <br> keeps the exact visual structure, while <a> provides the
    # user-required shorthand clickable links.

    final_lines: List[str] = []
    for raw_line in lines:
        if not raw_line.startswith("__LINKS__"):
            final_lines.append(_html.escape(raw_line))
            continue

        # Derive per-entry links from the indexed hit to avoid any drift.
        try:
            i = int(raw_line.replace("__LINKS__", "").strip())
            e = hits[i]
        except Exception:
            final_lines.append(_html.escape(raw_line))
            continue

        lst = getattr(e, "listing", None)
        sc = getattr(e, "silver_calc", {})
        if not isinstance(sc, dict):
            sc = {}

        title = getattr(lst, "title", "") or ""
        listing_url = (
            getattr(lst, "url", None)
            or getattr(lst, "link", None)
            or ""
        )
        sold_url = _sold_link_for(title)
        coinbook_url = sc.get("coinbook_url")

        parts: List[str] = ["Links:"]

        def a(label: str, href: str) -> str:
            if href:
                return f"<a href=\"{_html.escape(href, quote=True)}\">{_html.escape(label)}</a>"
            return _html.escape(label)

        parts.append(a("Link to Listing", listing_url))
        parts.append(a("Link to Ebay Sales", sold_url))
        if coinbook_url:
            parts.append(a("Link to CoinBook", str(coinbook_url)))

        final_lines.append(" ".join([parts[0], " | ".join(parts[1:])]))

    return (
        '<div style="font-family: monospace; white-space: pre-wrap;">'
        + "<br>".join(final_lines)
        + "</div>"
    )
