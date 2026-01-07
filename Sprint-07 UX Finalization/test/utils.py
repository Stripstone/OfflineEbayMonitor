# utils.py
import re
import time
from datetime import datetime, timedelta
from typing import Optional

_MONEY_RE = re.compile(r"\$([\d,]+(?:\.\d+)?)")
_TIME_RE = re.compile(r"(\d+)\s*([dhm])", re.IGNORECASE)

def now_ts() -> int:
    return int(time.time())

def parse_money(text: str) -> Optional[float]:
    if not text:
        return None
    m = _MONEY_RE.search(text)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))

def normalize_whitespace(s: str) -> str:
    return " ".join((s or "").split())

def parse_time_left_to_minutes(time_left: str) -> Optional[int]:
    if not time_left:
        return None
    total = 0
    for n, unit in _TIME_RE.findall(time_left.lower()):
        n = int(n)
        if unit == "d":
            total += n * 1440
        elif unit == "h":
            total += n * 60
        elif unit == "m":
            total += n
    return total if total > 0 else None

def parse_end_datetime(time_left: str) -> Optional[datetime]:
    if not time_left:
        return None

    m = re.search(r"\((Today|Tomorrow)\s+(\d{1,2}:\d{2}\s*[AP]M)\)", time_left, re.I)
    if m:
        day_word, time_part = m.groups()
        base = datetime.now().date()
        if day_word.lower() == "tomorrow":
            base += timedelta(days=1)
        try:
            t = datetime.strptime(time_part, "%I:%M %p").time()
            return datetime.combine(base, t)
        except ValueError:
            return None

    m = re.search(r"\(([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s*[AP]M)\)", time_left)
    if m:
        for fmt in ("%b %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p"):
            try:
                return datetime.strptime(m.group(1), fmt)
            except ValueError:
                pass

    return None
