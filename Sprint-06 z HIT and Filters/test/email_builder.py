# email_builder.py
"""
Offline eBay Silver Monitor — Email Builder (Sprint 02 skeleton)

Sprint 02 scope:
- Render a Contract_Packet_v1.0 compliant *email UX skeleton* with placeholders only.
- No dependency on parsing, classification, EMA, or price_store.
- Whitespace-preserving, monospaced intent; no raw URLs rendered.

This module is intentionally standalone and safe to import anywhere.

#EndOfFile
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple


# --------------------------
# UX Constants (email product)
# --------------------------

_EMAIL_TITLE = "EBAY OFFLINE SILVER HITS"
_SEPARATOR = "============================================================"
_DIVIDER = "------------------------------------------------------------"


@dataclass(frozen=True)
class EmailSkeletonConfig:
    """
    Placeholders-only config.

    Notes:
    - All fields may be left as None; placeholders will be used.
    - This is intentionally NOT tied to the runtime config.py object.
    """
    spot_usd_per_oz: Optional[float] = None
    pawn_payout_pct: Optional[float] = None
    bid_offset_usd: Optional[float] = None
    target_margin_min_pct: Optional[float] = None
    target_margin_max_pct: Optional[float] = None
    max_time_left_hours: Optional[float] = None


def _fmt_currency_or_placeholder(value: Optional[float]) -> str:
    if value is None:
        return "$XX.XX"
    return f"${value:.2f}"


def _fmt_pct_or_placeholder(value: Optional[float]) -> str:
    if value is None:
        return "--.-%"
    return f"{value:.1f}%"


def _fmt_hours_or_placeholder(value: Optional[float]) -> str:
    if value is None:
        return "--.-- hours"
    return f"{value:.2f} hours"


def build_email_subject(earliest_time: Optional[str], new_count: int) -> str:
    """
    Contract subject (exact pattern):
      <earliest_time> Offline eBay Silver HITS (<N> new)

    Skeleton behavior:
    - earliest_time may be None => uses '--:--'
    - new_count may be 0
    """
    et = earliest_time if earliest_time else "--:--"
    return f"{et} Offline eBay Silver HITS ({int(new_count)} new)"


def build_email_body_skeleton(
    config: Optional[EmailSkeletonConfig] = None,
    *,
    total_hits: int = 0,
    placeholder_entries: int = 1,
    generated_at: Optional[datetime] = None,
) -> str:
    """
    Contract body structure (fixed order):
      1) Header title
      2) Separator line
      3) Summary block:
         - Spot | Pawn
         - Bid offset
         - Target margin
         - Max time left
      4) Blank line
      5) Total HITs: <N>
      6) Divider
      7) One or more placeholder entry blocks
      8) Final divider
      9) Generated at: YYYY-MM-DD HH:MM:SS

    Placeholders only:
      Currency: $XX.XX
      Percent: --.-%
      Counts/time: --
      No raw URLs rendered.
    """
    cfg = config or EmailSkeletonConfig()
    now = generated_at or datetime.now()

    spot_str = _fmt_currency_or_placeholder(cfg.spot_usd_per_oz)
    pawn_str = _fmt_pct_or_placeholder(cfg.pawn_payout_pct)
    bid_offset_str = _fmt_currency_or_placeholder(cfg.bid_offset_usd)
    tmin_str = _fmt_pct_or_placeholder(cfg.target_margin_min_pct)
    tmax_str = _fmt_pct_or_placeholder(cfg.target_margin_max_pct)
    max_time_str = _fmt_hours_or_placeholder(cfg.max_time_left_hours)

    lines: list[str] = []
    lines.append(_EMAIL_TITLE)
    lines.append(_SEPARATOR)

    # Summary block (labels are contract-anchored)
    lines.append(f"Spot | Pawn: {spot_str} | {pawn_str}")
    lines.append(f"Bid offset: {bid_offset_str}")
    lines.append(f"Target margin: {tmin_str}–{tmax_str}")
    lines.append(f"Max time left: {max_time_str}")

    # Blank line (whitespace significant)
    lines.append("")

    lines.append(f"Total HITs: {int(total_hits)}")
    lines.append(_DIVIDER)

    # Entry blocks — placeholders only.
    # We keep the entry layout close to the contract expectations, but without any live data.
    n_entries = max(0, int(placeholder_entries))
    if n_entries == 0:
        # Still render structure; no entries.
        pass
    else:
        for i in range(1, n_entries + 1):
            # Melt-style placeholder (no explicit HIT header)
            lines.append(f"#{i} [placeholder_{i}.html]")
            lines.append("Title: <PLACEHOLDER TITLE>")

            lines.append("")
            lines.append("Current Profit (pawn): $XX.XX (--.-% margin vs pawn)")
            lines.append("ProfitAtMaxBid (pawn): $XX.XX (--.-% margin vs pawn)")
            lines.append("RecMaxBid: $XX.XX ($XX.XX total incl. ship)")
            lines.append("Current Total: $XX.XX")

            lines.append("")
            lines.append("Qty: -- | oz/coin: 0.00000 | Total oz: --.--")
            lines.append("Melt | Pawn payout: $XX.XX | $XX.XX")
            lines.append("Time left: --h--m (Today --:-- --)")

            lines.append("")
            lines.append("Links:")
            lines.append("  Link to Listing: <shorthand-link>")
            lines.append("  Link to Ebay Sales: <shorthand-link>")

            lines.append(_DIVIDER)

    # Final divider (contract requires a divider before footer)
    lines.append(_DIVIDER)
    lines.append(f"Generated at: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


def build_email_skeleton(
    *,
    earliest_time: Optional[str] = None,
    total_hits: int = 0,
    placeholder_entries: int = 1,
    config: Optional[EmailSkeletonConfig] = None,
    generated_at: Optional[datetime] = None,
) -> Tuple[str, str]:
    """
    Convenience wrapper to produce (subject, body) for Sprint 02 tests.
    """
    subject = build_email_subject(earliest_time=earliest_time, new_count=total_hits)
    body = build_email_body_skeleton(
        config=config,
        total_hits=total_hits,
        placeholder_entries=placeholder_entries,
        generated_at=generated_at,
    )
    return subject, body


#EndOfFile
