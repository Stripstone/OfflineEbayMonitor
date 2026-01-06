# Sprint_05.5_Plan.md

**Goal:** Create working runtime foundation that integrates Sprints 02-05 outputs into end-to-end monitor

**Contract Version:** v1.2 (authoritative)

**Master Sprint Plan Reference:** Foundation sprint (bridges Phase 2 → Sprint 06)

---

## Context

**Situation:**
- Sprints 02-05 delivered isolated modules (parser, EMA, email, prospect scoring)
- Missing: Runtime orchestrator that wires modules together
- Need: Working monitor before Sprint 06 classification enhancements

**This sprint creates the runtime foundation.**

---

## In Scope

- Main runtime orchestrator (`silver_monitor.py`)
- Melt calculation engine (`silver_math.py`)
- Basic HIT/MISS classification (`classifier.py`)
- Configuration (`config.py`)
- Integration with all existing modules
- End-to-end working monitor (parse → classify → email)

## Out of Scope (Deferred to Sprint 06.x)

- ❌ Diagnostic output (Sprint 06.1)
- ❌ Filter word gates (Sprint 06.2)
- ❌ PROS classification (Sprint 06.3)
- ❌ Prospect scoring integration in classifier (Sprint 06.3)

---

## Files to CREATE

### **`silver_monitor.py`** — Runtime Orchestrator

**Responsibility:**
- Main loop and scan cycle control
- HTML file discovery and loading
- Parser orchestration
- EMA capture coordination
- Deduplication (intra-run and cross-run)
- Email sending coordination
- Console output coordination

**Must NOT:**
- Perform melt calculations (delegated to `silver_math.py`)
- Make HIT/MISS decisions (delegated to `classifier.py`)
- Parse HTML (delegated to `parser_listings.py`)
- Format email content (delegated to `email_builder.py`)

**Required Structure:**

```python
def main():
    """Main loop - continuous monitoring"""
    while True:
        result = run_once()
        # Print results
        # Send email if new HITs
        # Sleep
        
def run_once():
    """Single scan cycle"""
    # 1. Discover HTML files
    # 2. Parse listings
    # 3. Filter (qty, blacklist, time window)
    # 4. EMA capture (price_store.py)
    # 5. Deduplicate
    # 6. Classify (classifier.py)
    # 7. Select HITs
    # 8. Deduplicate new HITs
    # 9. Return results
```

**Integration Points:**
- `parser_listings.py` → `parse_listings_from_html(html_text, max_time_hours, default_min_qty, keyword_blacklist)`
- `silver_math.py` → `calc_silver(listing)` (called by classifier)
- `classifier.py` → `classify_listings(listings)`
- `price_store.py` → `load_store()`, `save_store()`, `capture_updates()`
- `email_builder.py` → `build_email_subject()`, `build_email_body()`
- `prospect_score.py` → NOT used yet (Sprint 06.3)

**Console Output (per Contract v1.2 Section 1):**
- Banner on start
- Timestamped cycle status
- Counts: Found / Eligible / HITs
- Hit!/Miss table (call existing table formatter if it exists, or implement basic version)
- Email status
- Sleep indicator

**Email Output (per Contract v1.2 Section 2):**
- Send only if new HITs exist
- Subject: `<earliest_time> Offline eBay Silver HITS (<N> new)`
- Body: formatted via `email_builder.py`

---

### **`silver_math.py`** — Melt Calculation Engine

**Responsibility:**
- Silver content calculation (qty × oz_per_coin)
- Melt value calculation (total_oz × spot_price)
- Pawn payout calculation (melt_value × pawn_pct)
- Profit and margin calculation (cost-basis, per Contract v1.2 Section 3)
- Recommended max price calculation (for target margin)
- Quantity extraction from title
- Coin type detection from title (Dollar vs Half Dollar)

**Must NOT:**
- Make HIT/MISS decisions
- Access EMA values
- Apply filters or gates

**Required Interface:**

```python
def calc_silver(listing) -> dict:
    """
    Calculate melt metrics for a listing.
    
    Args:
        listing: Parsed listing object with:
            - title: str
            - total_price: float (item_price + shipping)
            - shipping: float
    
    Returns:
        dict with keys:
            - quantity: int
            - oz_per_coin: float
            - total_oz: float
            - melt_value: float
            - melt_payout: float (melt × pawn_pct)
            - profit: float (payout - total_price)
            - margin_pct: float (cost-basis: profit/cost × 100)
            - rec_max_total: float (max total price for target margin)
            - rec_max_item: float (max item price, excluding shipping)
            - profit_at_rec_max: float
            - margin_at_rec_max: float
    """
    pass

def extract_quantity_from_title(title: str) -> int:
    """Extract quantity from title, default to 1 if unclear"""
    pass

def detect_oz_per_coin_from_title(title: str) -> float:
    """
    Detect silver content per coin from title.
    
    Returns:
        - 0.77344 for dollars (Morgan, Peace, Seated Dollar)
        - 0.36169 for half dollars (Kennedy, Franklin, Walking Liberty, Barber Half, Seated Half)
        - Default: 0.36169 (conservative)
    """
    pass
```

**Coin Detection Logic:**
- Look for "half" keywords → 0.36169 oz
- Look for "dollar" or specific series (Morgan, Peace) → 0.77344 oz
- Default to half dollar if ambiguous (conservative)

**Math Formulas (per Contract v1.2 Section 3):**
- `total_oz = qty × oz_per_coin`
- `melt_value = total_oz × spot_price`
- `pawn_payout = melt_value × (pawn_pct / 100)`
- `profit = pawn_payout - total_price`
- `margin_pct = (profit / total_price) × 100` (cost-basis)
- `rec_max_total = pawn_payout / (1 + min_margin_pct/100)`
- `rec_max_item = rec_max_total - shipping`

**Dependencies:**
- `config.SPOT_PRICE` — current silver spot price
- `config.PAWN_PAYOUT_PCT` — pawn payout percentage
- `config.MIN_MARGIN_PCT` — target margin for rec_max calculation

---

### **`classifier.py`** — Basic HIT/MISS Classification

**Responsibility (Sprint 05.5 ONLY):**
- Accept list of parsed listings
- For each listing, determine HIT or MISS based on melt economics
- Return list of `Evaluated` objects

**Must NOT (Sprint 05.5):**
- Apply filter words (Sprint 06.2)
- Apply PROS logic (Sprint 06.3)
- Track diagnostics (Sprint 06.1)
- Integrate prospect scoring (Sprint 06.3)

**Required Interface:**

```python
from dataclasses import dataclass
from typing import List, Any

@dataclass
class Evaluated:
    listing: Any
    silver_calc: dict  # from silver_math.calc_silver()
    is_hit: bool
    is_prospect: bool = False  # Always False in Sprint 05.5

def classify_listings(listings: List[Any]) -> List[Evaluated]:
    """
    Classify listings as HIT or MISS based on melt economics.
    
    Args:
        listings: Parsed listing objects
    
    Returns:
        List of Evaluated objects, sorted by end_time_ts (earliest first)
    """
    pass
```

**Implementation Logic:**

```python
def classify_listings(listings):
    evaluated = []
    
    for listing in listings:
        # Get melt calculations
        silver_calc = silver_math.calc_silver(listing)
        
        # Classify: HIT if total_price <= rec_max_total
        rec_max = silver_calc.get("rec_max_total")
        is_hit = (rec_max is not None and listing.total_price <= rec_max)
        
        # Create Evaluated object
        evaluated.append(Evaluated(
            listing=listing,
            silver_calc=silver_calc,
            is_hit=is_hit,
            is_prospect=False  # Sprint 06.3
        ))
    
    # Sort by earliest ending time
    evaluated.sort(key=lambda e: e.listing.end_time_ts)
    
    return evaluated
```

**Note:** This is basic melt-only classification. Sprint 06.1+ will enhance this module.

---

### **`config.py`** — Configuration

**Responsibility:**
- All user-configurable thresholds and settings
- Hard constants (file paths, credentials per Contract v1.2 Section 6)
- Feature flags

**Must NOT:**
- Contain logic (pure configuration only)
- Be modified during runtime (read-only)

**Required Values:**

```python
# =============================================================================
# FILE SYSTEM
# =============================================================================
HTML_FOLDER_PATH = r"C:\Users\Triston Barker\Desktop\EbayMiner\ebay_pages"
PRICE_STORE_PATH = "price_store.json"
SEEN_HITS_PATH = "seen_hits.json"

# =============================================================================
# CORE MARKET CONFIG
# =============================================================================
SPOT_PRICE = 31.50  # USD per oz (manually updated)
PAWN_PAYOUT_PCT = 80.0  # Pawn shop payout % of melt value
MIN_MARGIN_PCT = 15.0  # Minimum margin threshold for HIT
MAX_MARGIN_PCT = 60.0  # Maximum expected margin

# =============================================================================
# TIME & QUANTITY FILTERS
# =============================================================================
MAX_TIME_HOURS = 24.0  # Only consider listings ending within X hours (None = no limit)
DEFAULT_MIN_QUANTITY = None  # Minimum quantity (None = no filter)

# =============================================================================
# BLACKLIST
# =============================================================================
DEFAULT_BLACKLIST = []  # Global keyword blacklist

# =============================================================================
# FILE SELECTION
# =============================================================================
SILVER_FILENAME_KEYWORDS = [
    "morgan", "peace", "barber", "seated", "franklin", "kennedy", "walking", "silver"
]

DELETE_PROCESSED_HTML = True  # Delete HTML files after processing

# =============================================================================
# MONITOR LOOP TIMING
# =============================================================================
DEFAULT_CHECK_INTERVAL_MIN = 2.0  # Minutes between scan cycles
SLEEP_JITTER_SEC = 5.0  # Random jitter to avoid patterns

# =============================================================================
# EMAIL SETTINGS
# =============================================================================
EMAIL_ENABLED = True

FROM_EMAIL = "alerts@sandboxdb0bf36453ab448baf9ac17275a43135.mailgun.org"
TO_EMAILS = ["johnny.monitor@gmx.com"]

MAILGUN_SMTP_SERVER = "smtp.mailgun.org"
MAILGUN_SMTP_PORT = 587
MAILGUN_SMTP_LOGIN = "johnnymonitor.mailgun.org@sandboxdb0bf36453ab448baf9ac17275a43135.mailgun.org"
MAILGUN_SMTP_PASSWORD = "99Pushups%"

# =============================================================================
# EMA (PRICE CAPTURE) SETTINGS
# =============================================================================
PRICE_CAPTURE_ONLY_IF_BIDS = True  # Only capture prices with bids > 0
PRICE_CAPTURE_BUMP_PCT = 8.0  # Bump % for late auction simulation
EMA_ALPHA = 0.40  # EMA smoothing factor
PRICE_CAPTURE_MAX_MINUTES = 30  # Only capture if ending within X minutes

# =============================================================================
# NUMISMATIC SETTINGS (Sprint 05 output, not used yet in classifier)
# =============================================================================
NUMISMATIC_PAYOUT_PCT = 60.0  # Dealer payout % of FMV (Sprint 06.3)
```

---

## Files to INTEGRATE (Existing from Artifacts-02-03)

### **`parser_listings.py`**
- **From:** Sprint 03
- **Function:** `parse_ebay_search_html(filename, html)` → List[Listing]
- **Usage:** Called by `silver_monitor.py` to parse HTML files
- **Do NOT modify**

### **`price_store.py`**
- **From:** Sprint 04
- **Functions:**
  - `load_store()` → dict
  - `save_store(store)` → None
  - `capture_updates(store, updates)` → None
  - `get_ema_value_and_observers(key)` → (float, int) or (None, None)
- **Usage:** Called by `silver_monitor.py` for EMA capture
- **Do NOT modify**

### **`email_builder.py`**
- **From:** Sprint 02
- **Functions:**
  - `build_email_subject(earliest_time_str, n_new, market_name)` → str
  - `build_email_body(hits)` → str (HTML)
- **Usage:** Called by `silver_monitor.py` to format emails
- **Do NOT modify**

### **`prospect_score.py`**
- **From:** Sprint 05
- **Function:** `score_prospect(listing, fmv_floor, dealer_value)` → ProspectScore
- **Usage:** NOT used in Sprint 05.5 (deferred to Sprint 06.3)
- **Do NOT modify**

---

## Files NOT in Scope

**These may exist in a_materials but are NOT needed for Sprint 05.5:**
- `numismatic_rules.py` — coin detection (Sprint 06.3 integration)
- `console_tables.py` — table formatter (implement basic version in silver_monitor.py or defer)
- `emailer.py` — SMTP sending (implement inline or use existing if available)
- `state_store.py` — seen HITs tracking (implement inline or use existing if available)
- `html_loader.py` — HTML file loading (implement inline or use existing if available)

**Implementation note:** If these utility modules exist in a_materials and comply with Contract v1.2, Build Studio may use them. Otherwise, implement necessary functions inline in `silver_monitor.py`.

---

## Acceptance Criteria

### ✅ **Functional Requirements:**

1. **Monitor runs end-to-end:**
   - Discovers HTML files in configured folder
   - Parses listings successfully
   - Calculates melt values correctly
   - Classifies HITs based on margin threshold
   - Sends email when new HITs found
   - Prints console output per Contract v1.2 Section 1

2. **Melt calculation correct:**
   - Detects coin type (dollar vs half dollar)
   - Extracts quantity from title
   - Calculates melt value using spot price
   - Calculates pawn payout using pawn %
   - Calculates margin (cost-basis formula)
   - Returns recommended max prices

3. **Classification correct:**
   - HIT when `total_price <= rec_max_total`
   - MISS otherwise
   - Sorted by earliest ending time
   - Returns `Evaluated` objects with `silver_calc` dict

4. **Integration correct:**
   - Calls `parser_listings.parse_ebay_search_html()` successfully
   - Calls `price_store` functions for EMA capture
   - Calls `email_builder` functions for email formatting
   - All modules wire together without errors

5. **Console output per contract:**
   - Cycle counts displayed
   - Hit!/Miss indication clear
   - Email status shown
   - Sleep time visible

6. **Email output per contract:**
   - Subject format correct: `<time> Offline eBay Silver HITS (<N> new)`
   - Only sent when new HITs exist
   - Body formatted via `email_builder.py`

### ✅ **Code Quality:**

7. **No scope creep:**
   - No diagnostic output (Sprint 06.1)
   - No filter words (Sprint 06.2)
   - No PROS classification (Sprint 06.3)
   - No prospect scoring integration (Sprint 06.3)

8. **Clean module boundaries:**
   - `silver_monitor.py` orchestrates only
   - `silver_math.py` calculates only
   - `classifier.py` classifies only
   - `config.py` configures only

9. **Contract compliance:**
   - Math formulas per Contract v1.2 Section 3
   - Console UX per Contract v1.2 Section 1
   - Email UX per Contract v1.2 Section 2
   - EMA capture per Contract v1.2 Section 7

### ✅ **Testing Readiness:**

10. **User can verify:**
    - Monitor starts without errors
    - Parses HTML files successfully
    - Classifies listings as HIT/MISS
    - Sends email with HITs
    - Console output is clear
    - Can run continuously without crashing

---

## Implementation Notes

### **Listing Object Structure**

Based on `parser_listings.py` output, listings should have:
```python
listing.title: str
listing.item_price: float
listing.shipping: float
listing.total_price: float  # item_price + shipping
listing.bids: int
listing.time_left: str
listing.end_time_ts: float  # Unix timestamp
listing.url: str
listing.item_id: str (optional)
```

### **Deduplication Strategy**

**Intra-run deduplication:**
- Same item appearing multiple times in one HTML file
- Dedupe by item_id (preferred) or URL or title
- Do BEFORE classification

**Cross-run deduplication:**
- Track seen HITs across scan cycles
- Use item_id or URL as key
- Store in `seen_hits.json` or similar
- Only email NEW HITs

### **EMA Capture Integration**

**EMA capture happens BEFORE classification:**
1. Parse listings
2. Filter (qty, blacklist, time window)
3. **EMA capture** (price_store.py)
4. Deduplicate
5. Classify
6. Email

**EMA eligibility (per Contract v1.2 Section 7):**
- `qty == 1`
- `bids >= 1`
- NOT lot/roll/set/face value
- NOT album/folder/book/"NO COINS"
- NOT accessory (money clip, keychain, pendant, jewelry, cutout)
- NOT damaged (holed, hole, pierced, drilled)

**Implementation:** `silver_monitor.py` applies these filters before calling `price_store.capture_updates()`

### **Console Table Output**

**Minimum viable console output:**
```
[2025-01-01 10:30:45] Relevant cycles: 1/1 | Files: 2 | Listings: 15 | HITs: 3 | New: 2

=== morgan_dollars.html ===
HIT  | $42.50 | 1 | 2h15m (Today 12:45 PM) | 1921 Morgan Dollar AU
MISS | $65.00 | 1 | 3h20m (Today 1:50 PM) | 1885 Morgan Dollar VF
HIT  | $38.00 | 1 | 45m (Today 11:15 AM) | 1921-D Morgan Dollar

EMAIL: sent (2 new) | Subject: 11:15 AM Offline eBay Silver HITS (2 new)

Sleep: 125s
```

**If existing table formatter available, use it. Otherwise, implement basic version.**

---

## Contract Compliance Checklist

Per Contract_Packet_v1.2:

- ✅ **Section 1 (Console UX):** Cycle output, counts, table, email status, sleep indicator
- ✅ **Section 2 (Email UX):** Subject format, send only on new HITs, body via email_builder
- ✅ **Section 3 (Math Contract):** Cost-basis margins, melt formulas, rounding rules
- ✅ **Section 6 (Constants):** HTML_FOLDER_PATH, email credentials unchanged
- ✅ **Section 7 (EMA):** Write-time capture only, eligibility gates enforced

---

## Handoff to Build Studio

**Required materials:**
1. This Sprint Plan (Sprint_05.5_Plan.md)
2. Contract_Packet_v1.2.md
3. System_Responsibility_Map_v1.3.md (updated, see next artifact)
4. Existing modules from Artifacts-02-03:
   - `parser_listings.py`
   - `price_store.py`
   - `email_builder.py`
   - `prospect_score.py`

**Build Studio will produce:**
- `silver_monitor.py` (new file, complete)
- `silver_math.py` (new file, complete)
- `classifier.py` (new file, complete)
- `config.py` (new file, complete)

**Total output: 4 new files that integrate with 4 existing modules**

---

**End of Sprint_05.5_Plan.md**