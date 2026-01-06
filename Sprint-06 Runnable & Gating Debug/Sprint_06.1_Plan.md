# Sprint_06.1_Plan.md

**Goal:** Validate core melt economics produce visible HITs with diagnostic observability

**Contract Version:** v1.2 (authoritative)

**Master Sprint Plan Reference:** Phase 2, Sprint 06.1 — Melt HIT/MISS Only

---

## In Scope

- QTY-aware melt calculation (via `silver_math.calc_silver()`)
- Pawn payout calculation (already in `silver_math`)
- Melt HIT gate: `(pawn_profit / current_total) >= target_min_margin`
- MISS classification when HIT gate fails
- Diagnostic output (JSON + summary text) when `DEBUG_DIAGNOSTICS == True`
- Integration with existing `silver_monitor.py` orchestration

## Out of Scope (Deferred to Later Sprints)

- ❌ Filter words / blocked terms (Sprint 06.2)
- ❌ PROS classification (Sprint 06.3)
- ❌ Numismatic override logic (Sprint 06.3)
- ❌ Prospect scoring (Sprint 06.3)
- ❌ EMA capture logic (already implemented in `silver_monitor.py`, unchanged)
- ❌ UX changes (console/email format locked per Contract v1.2)

---

## Files to CREATE

### **`classifier.py`** — Melt HIT/MISS classification engine

**Responsibility:**
- Accept list of parsed listings
- For each listing, determine HIT or MISS based on melt economics only
- Return list of `Evaluated` objects (compatible with existing email/console formatters)
- Accumulate diagnostic data (if `config.DEBUG_DIAGNOSTICS == True`)

**Required Interface:**

```python
from dataclasses import dataclass
from typing import List, Any, Optional

@dataclass
class Evaluated:
    listing: Any
    silver_calc: dict  # melt calculation results from silver_math
    is_hit: bool
    is_prospect: bool = False  # Always False in Sprint 06.1

def classify_listings(
    listings: List[Any],
    diagnostics_enabled: bool = False
) -> List[Evaluated]:
    """
    Classify listings as HIT or MISS based on melt economics.
    
    Args:
        listings: Parsed listing objects (from existing parser)
        diagnostics_enabled: If True, accumulate diagnostic data
    
    Returns:
        List of Evaluated objects, sorted by end_time_ts (earliest first)
    """
    pass
```

**Implementation Requirements:**

1. **For each listing:**
   - Call `silver_math.calc_silver(listing)` to get melt metrics
   - Extract from `calc_silver()` result:
     - `pawn_profit` (melt_payout - total_price)
     - `rec_max_total` (recommended max total price for target margin)
   - Classify:
     - **HIT** if `listing.total_price <= rec_max_total`
     - **MISS** otherwise
   - Create `Evaluated` object with:
     - `listing` (original listing object)
     - `silver_calc` (dict from `calc_silver()`)
     - `is_hit` (True/False)
     - `is_prospect` (always False in 06.1)

2. **Sort output:**
   - By `listing.end_time_ts` (earliest → latest)

3. **Diagnostics (if enabled):**
   - Track counts:
     - `total_listings_seen`
     - `eligible_count` (listings that could be evaluated)
     - `hit_count`
     - `miss_count`
     - `ineligible_count` (listings missing required fields)
   - Track rejection reasons with sample titles (max 3 per reason):
     - `missing_price`
     - `missing_time`
     - `insufficient_margin`
   - Store diagnostic data in module-level state for retrieval

**Dependencies:**
- `silver_math.calc_silver()` — existing melt calculation
- `config.MIN_MARGIN_PCT` — HIT threshold
- `dataclasses` (standard library)

---

### **`diagnostics.py`** — Diagnostic output handler

**Responsibility:**
- Write diagnostic data to disk (JSON + human-readable summary)
- Reset diagnostic files on program start
- Accumulate data across scan cycles within one run
- Never output to console or email

**Required Interface:**

```python
def reset_diagnostics() -> None:
    """
    Called once at program start.
    Ensures ./diagnostics/ directory exists.
    Overwrites (resets) run_diagnostics.json and run_diagnostics_summary.txt.
    """
    pass

def write_diagnostics(data: dict) -> None:
    """
    Write diagnostic data to disk.
    
    Args:
        data: Dictionary containing:
            - total_listings_seen: int
            - eligible_count: int
            - hit_count: int
            - miss_count: int
            - ineligible_count: int
            - rejection_buckets: dict[str, int]  # reason -> count
            - samples_by_reason: dict[str, list[dict]]  # reason -> [{"title": str, "reason_detail": str}]
    
    Writes:
        - ./diagnostics/run_diagnostics.json (full data, machine-readable)
        - ./diagnostics/run_diagnostics_summary.txt (human-readable summary)
    """
    pass
```

**Output Format (JSON):**

```json
{
  "timestamp": "2025-01-01 10:30:45",
  "total_listings_seen": 42,
  "eligible_count": 38,
  "hit_count": 5,
  "miss_count": 33,
  "ineligible_count": 4,
  "rejection_buckets": {
    "insufficient_margin": 28,
    "missing_price": 3,
    "missing_time": 1
  },
  "samples_by_reason": {
    "insufficient_margin": [
      {"title": "1964 Kennedy Half Dollar", "reason_detail": "Margin 8.2% < 15.0% threshold"},
      {"title": "Walking Liberty Half", "reason_detail": "Margin 12.1% < 15.0% threshold"},
      {"title": "Franklin Half 1962", "reason_detail": "Margin 10.5% < 15.0% threshold"}
    ]
  }
}
```

**Output Format (Summary Text):**

```
=== DIAGNOSTICS SUMMARY ===
Run: 2025-01-01 10:30:45

Total Listings Seen: 42
  Eligible: 38
  Ineligible: 4

Classification Results:
  HIT: 5
  MISS: 33

Top Rejection Reasons:
  1. insufficient_margin: 28
  2. missing_price: 3
  3. missing_time: 1

Sample Titles (insufficient_margin):
  - "1964 Kennedy Half Dollar" (Margin 8.2% < 15.0% threshold)
  - "Walking Liberty Half" (Margin 12.1% < 15.0% threshold)
  - "Franklin Half 1962" (Margin 10.5% < 15.0% threshold)

===========================
```

**File Locations:**
- `./diagnostics/run_diagnostics.json`
- `./diagnostics/run_diagnostics_summary.txt`

**Behavior:**
- Create `./diagnostics/` directory if not exists
- Overwrite files on each write (not append)
- Never print to console
- Never send via email

---

## Files to MODIFY

### **`silver_monitor.py`**

**Changes Required:**

1. **Import changes:**
   ```python
   # OLD (remove):
   from hit_engine import evaluate_listings, select_hits
   
   # NEW (add):
   from classifier import classify_listings
   from diagnostics import reset_diagnostics, write_diagnostics
   ```

2. **Add diagnostic reset at program start:**
   ```python
   def main():
       print("\n============================================================")
       print("  EBAY OFFLINE SILVER MONITOR")
       print("============================================================\n")
       
       # NEW: Reset diagnostics on program start
       if config.DEBUG_DIAGNOSTICS:
           reset_diagnostics()
       
       min_qty = config.DEFAULT_MIN_QUANTITY
       # ... rest of main() unchanged
   ```

3. **Replace evaluation call in `run_once()`:**
   ```python
   # OLD (remove):
   evaluated = evaluate_listings(
       filtered,
       max_time_hours=config.MAX_TIME_HOURS,
   )
   hits = select_hits(evaluated)
   
   # NEW (replace with):
   evaluated = classify_listings(
       filtered,
       diagnostics_enabled=config.DEBUG_DIAGNOSTICS
   )
   
   # Select HITs (Sprint 06.1: only is_hit=True, no PROS yet)
   hits = [e for e in evaluated if e.is_hit]
   ```

4. **Add diagnostic output after classification:**
   ```python
   # NEW: Write diagnostics if enabled
   if config.DEBUG_DIAGNOSTICS:
       # Collect diagnostic data from classifier
       # (classifier.py will expose a get_diagnostics() function)
       from classifier import get_diagnostics
       diag_data = get_diagnostics()
       write_diagnostics(diag_data)
   ```

**Everything else in `silver_monitor.py` remains unchanged:**
- HTML loading
- Parsing
- EMA capture
- Deduplication
- Email sending
- Console output

---

### **`config.py`**

**Add (if missing):**

```python
# Diagnostics (Sprint 06)
DEBUG_DIAGNOSTICS = True  # Set to False to disable diagnostic output
```

**Verify exists (required for classifier):**

```python
MIN_MARGIN_PCT = 15.0  # Melt HIT threshold (cost-basis margin)
SPOT_PRICE_SILVER = 31.50  # Current silver spot price (USD/oz)
PAWN_PAYOUT_PCT = 80.0  # Pawn shop payout percentage of melt value
```

---

## Files to READ (Reference Only — Do NOT Modify)

### **`silver_math.py`**
- Contains `calc_silver(listing)` function
- Returns dict with melt calculations:
  - `quantity`, `oz_per_coin`, `total_oz`, `melt_value`, `melt_payout`
  - `profit`, `margin_pct`, `rec_max_total`, `rec_max_item`
- **Use as-is, do not modify**

### **`hit_engine.py`**
- Current implementation (to be replaced)
- Reference for structure and `Evaluated` dataclass
- **Do not modify, mark as deprecated**

### **`numismatic_rules.py`**
- Contains coin detection logic (`detect_coin_identity()`)
- **Not used in Sprint 06.1** (deferred to 06.3)
- **Do not modify**

### **Parser modules** (existing)
- Extract: title, price, shipping, bids, time_left, end_time_ts, etc.
- **Do not modify**

---

## Files to DEPRECATE (Mark, Do Not Delete)

### **`hit_engine.py`**
- Add comment at top of file:
  ```python
  # DEPRECATED: Replaced by classifier.py in Sprint 06.1
  # Kept for reference only. Do not import in active code.
  ```
- **Do not delete file** (may be useful for reference in later sprints)

---

## Acceptance Criteria

### ✅ **Functional Requirements:**

1. **Melt HIT classification works:**
   - Listings with `margin_pct >= MIN_MARGIN_PCT` classified as HIT
   - Listings below threshold classified as MISS
   - Email shows melt HITs only (no PROS in 06.1)

2. **Diagnostics output correct:**
   - When `DEBUG_DIAGNOSTICS = True`:
     - `./diagnostics/run_diagnostics.json` created with correct counts
     - `./diagnostics/run_diagnostics_summary.txt` created with human-readable summary
     - Files reset on program start, updated after each scan cycle
   - When `DEBUG_DIAGNOSTICS = False`:
     - No diagnostic files created
     - No performance impact

3. **Integration with existing code:**
   - `silver_monitor.py` calls `classifier.classify_listings()` successfully
   - Console table rendering works (uses `Evaluated` objects)
   - Email formatting works (uses `Evaluated` objects)
   - No changes to console or email UX

4. **Silver math integration:**
   - `classifier.py` calls `silver_math.calc_silver()` correctly
   - Melt calculations match Contract v1.2 formulas
   - Rounding per contract (currency: 2 decimals, percent: 1 decimal)

### ✅ **Code Quality:**

5. **No scope creep:**
   - No filter word logic
   - No PROS classification
   - No numismatic override logic
   - No EMA modifications

6. **Clean deprecation:**
   - `hit_engine.py` marked deprecated but not deleted
   - No imports of `hit_engine` in active code

7. **Diagnostic discipline:**
   - Diagnostics never output to console
   - Diagnostics never sent via email
   - Diagnostics written to disk only

### ✅ **Testing Readiness:**

8. **User can verify:**
   - Email arrives with melt HITs
   - Console shows Hit!/Miss correctly
   - Diagnostic files exist and show accurate counts
   - Rejection reasons make sense

---

## Implementation Notes

### **Coin Type Detection (Sprint 06.1 Scope):**

For melt calculation, `silver_math.calc_silver()` needs to know coin type (Dollar vs Half Dollar) to determine silver content:
- Dollar: 0.77344 oz
- Half Dollar: 0.36169 oz

**Implementation approach:**
- Parse title for "dollar" vs "half" keywords
- Simple regex: `r"\bhalf\b"` → Half Dollar, else Dollar
- If ambiguous, default to Half Dollar (conservative)

**This is minimal coin detection for melt only. Full numismatic detection (year/mint) deferred to Sprint 06.3.**

### **Diagnostic State Management:**

`classifier.py` should maintain module-level state for diagnostics:

```python
# Module-level diagnostic state
_diagnostics = {
    "total_listings_seen": 0,
    "eligible_count": 0,
    "hit_count": 0,
    "miss_count": 0,
    "ineligible_count": 0,
    "rejection_buckets": {},
    "samples_by_reason": {}
}

def get_diagnostics() -> dict:
    """Return current diagnostic data and reset for next cycle."""
    global _diagnostics
    data = _diagnostics.copy()
    _diagnostics = {
        "total_listings_seen": 0,
        "eligible_count": 0,
        "hit_count": 0,
        "miss_count": 0,
        "ineligible_count": 0,
        "rejection_buckets": {},
        "samples_by_reason": {}
    }
    return data
```

---

## Contract Compliance Checklist

Per Contract_Packet_v1.2:

- ✅ Math Contract Section 3: Melt HIT uses cost-basis margin formula
- ✅ Diagnostic Addendum Section 8: Diagnostics are non-user-facing, disk-only
- ✅ No UX changes (console/email format unchanged)
- ✅ PROS must never override Melt HIT (N/A in 06.1, no PROS yet)
- ✅ EMA capture unchanged (handled in `silver_monitor.py`)

---

## Handoff to Build Studio

**Required materials:**
1. This Sprint Plan
2. Contract_Packet_v1.2.md
3. System_Responsibility_Map (updated, see next artifact)
4. Source files:
   - `silver_monitor.py` (current version)
   - `silver_math.py` (reference)
   - `config.py` (to be modified)
   - `hit_engine.py` (reference for `Evaluated` structure)

**Build Studio will produce:**
- `classifier.py` (new file, complete)
- `diagnostics.py` (new file, complete)
- `silver_monitor.py` (modified, full file with changes)
- `config.py` (modified, full file with `DEBUG_DIAGNOSTICS` added if missing)

---

**End of Sprint_06.1_Plan.md**