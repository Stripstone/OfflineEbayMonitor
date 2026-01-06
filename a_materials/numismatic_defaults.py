# numismatic_defaults.py
"""NUMISMATIC DEFAULTS — static conservative floor values (offline)

Why this exists:
- The system must be able to run even when EMA price_store has no data yet.
- This module provides a *minimal* static fallback (FMV floor) for specific
  coin identities when you want numismatic detection to trigger immediately.

Blueprint alignment:
- These are *floors* (G–VG range) intended for dealer-buy estimates.
- If a coin is not listed here, return None so numismatic override does not trigger.

How to extend:
- Add entries to STATIC_FLOORS keyed by:
    (coin_type, year, mint, grade)
  where grade is usually "G" for now.

coin_type must match numismatic_rules.detect_coin_identity():
- "Morgan Dollar"
- "Peace Dollar"
- "Barber Half"
- "Seated Liberty Half"
- "Seated Liberty Dollar"
"""


from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class StaticFloor:
    coin_type: str
    year: str
    mint: str
    grade: str
    floor: float


# -------------------------------------------------------------------
# STATIC FLOORS (G–VG) — EDIT HERE
# -------------------------------------------------------------------
# Leave empty to disable static overrides entirely.
# Add only values you are confident a local dealer would treat as a floor.
#
# Example:
# ("Morgan Dollar", "1883", "O", "G"): 63.00
# -------------------------------------------------------------------
STATIC_FLOORS: Dict[Tuple[str, str, str, str], float] = {
    # Add your known floors here.
        # -------------------------
    # MORGAN SILVER DOLLARS
    # -------------------------
    ("Morgan Dollar", "1878", "CC", "G"): None,
    ("Morgan Dollar", "1881", "CC", "G"): 443.00,
    ("Morgan Dollar", "1885", "CC", "G"): None,
    ("Morgan Dollar", "1889", "CC", "G"): None,
    ("Morgan Dollar", "1892", "CC", "G"): None,
    ("Morgan Dollar", "1892", "S",  "G"): None,
    ("Morgan Dollar", "1893", "CC", "G"): None,
    ("Morgan Dollar", "1893", "S",  "G"): None,  # KING
    ("Morgan Dollar", "1895", "P",  "G"): None,  # proof-only
    ("Morgan Dollar", "1901", "P",  "G"): None,
    ("Morgan Dollar", "1903", "O",  "G"): None,

    # -------------------------
    # PEACE SILVER DOLLARS
    # -------------------------
    ("Peace Dollar", "1921", "P", "G"): None,  # high relief
    ("Peace Dollar", "1927", "S", "G"): None,
    ("Peace Dollar", "1928", "P", "G"): None,  # primary key
    ("Peace Dollar", "1928", "S", "G"): None,
    ("Peace Dollar", "1934", "S", "G"): None,
    ("Peace Dollar", "1935", "S", "G"): None,

    # -------------------------
    # SEATED LIBERTY HALF DOLLARS
    # -------------------------
    ("Seated Liberty Half", "1878", "S", "G"): None,
    ("Seated Liberty Half", "1885", "P", "G"): None,
    ("Seated Liberty Half", "1886", "P", "G"): None,
    ("Seated Liberty Half", "1887", "P", "G"): None,
    ("Seated Liberty Half", "1888", "P", "G"): None,

    # -------------------------
    # BARBER HALF DOLLARS
    # -------------------------
    ("Barber Half", "1892", "O", "G"): None,
    ("Barber Half", "1893", "S", "G"): None,
    ("Barber Half", "1896", "O", "G"): None,
    ("Barber Half", "1897", "O", "G"): None,
    ("Barber Half", "1914", "P", "G"): None,
    ("Barber Half", "1915", "P", "G"): None,

    # -------------------------
    # WALKING LIBERTY HALF DOLLARS
    # -------------------------
    ("Walking Liberty Half", "1916", "S", "G"): None,
    ("Walking Liberty Half", "1919", "D", "G"): None,
    ("Walking Liberty Half", "1919", "S", "G"): None,
    ("Walking Liberty Half", "1921", "P", "G"): None,
    ("Walking Liberty Half", "1921", "D", "G"): None,
    ("Walking Liberty Half", "1921", "S", "G"): None,
    ("Walking Liberty Half", "1938", "D", "G"): None,
    ("Walking Liberty Half", "1939", "S", "G"): None,
}


def get_static_floor(coin_type: str, year: str, mint: str, grade: str = "G") -> Optional[StaticFloor]:
    key = (str(coin_type), str(year), str(mint), str(grade))
    v = STATIC_FLOORS.get(key)
    if v is None:
        return None
    try:
        return StaticFloor(coin_type=coin_type, year=year, mint=mint, grade=grade, floor=float(v))
    except Exception:
        return None


# Backwards-compat alias (older modules imported STATIC_DEFAULTS)
STATIC_NUMISMATIC_DEFAULTS = STATIC_FLOORS
