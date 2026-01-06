# SYSTEM RESPONSIBILITY MAP v1.5
**Updated:** December 31, 2025  
**Previous Version:** v1.4 (deprecated — had incorrect function signatures from Sprints 02-03 modules)

---

## Changes from v1.4

**Critical Corrections (verified against actual source code):**

1. **parser_listings.py** — Corrected function signature and return type
   - Function name: `parse_listings_from_html()` ✓ (v1.4 was correct)
   - Parameters: **CHANGED** — only accepts `html_text` and optional keyword args
   - Returns: `List[Dict[str, Any]]` ✓ (v1.4 was correct)
   - **Key change:** Does NOT accept `max_time_hours`, `default_min_qty`, `keyword_blacklist` as originally documented

2. **price_store.py** — Corrected all function names
   - `load_price_store()` → `load_store()` ✓
   - `save_price_store(data)` → `save_store(data)` ✓
   - `capture_ema_from_listings()` → `update_price()` ✓
   - **All function names in v1.4 were incorrect**

3. **email_builder.py** — Corrected function signatures
   - Only provides skeleton/placeholder functions
   - Does NOT provide production email building for HITs
   - Sprint 05.5 must implement inline email building

4. **Added actual dict structure** from parser with all fields documented

---

## File Inventory

### Core Monitor (Sprint 05.5)

#### `silver_monitor.py`
- **Owner:** Sprint 05.5
- **Purpose:** Main orchestrator — file discovery, loop control, output
- **Stability:** Evolving (Sprint 06+ adds diagnostics)
- **Dependencies:**
  - `parser_listings` (parse HTML)
  - `price_store` (EMA capture)
  - `silver_math` (calculations)
  - `classifier` (HIT/MISS)
  - `email_builder` (skeleton only — must implement production email inline)
  - `config` (all settings)
- **Key Responsibilities:**
  - Discover HTML files in watch folder
  - Parse each file via `parser_listings.parse_listings_from_html()`
  - Apply filters (time/qty/blacklist) — **MUST IMPLEMENT INLINE** (parser doesn't filter)
  - Convert dicts → objects via ListingAdapter
  - Classify listings via `classifier.classify_listings()`
  - Deduplicate HITs (cross-run)
  - Print console output
  - Send email alerts (implement inline)
  - Capture EMA data via `price_store.update_price()`
- **Integration Points:**
  - Calls `parser_listings.parse_listings_from_html(html_text)` → `List[Dict]`
  - Calls `classifier.classify_listings(obj_listings)` → `List[Evaluated]`
  - Calls `price_store.load_store()` → `dict`
  - Calls `price_store.update_price(store, key, total_price, bid_count, qty=, title=)` → `bool`
  - Calls `price_store.save_store(store)`
  - **Must implement email body building inline** (email_builder.py only has skeleton)

---

#### `classifier.py`
- **Owner:** Sprint 05.5
- **Purpose:** HIT/MISS classification based on melt economics
- **Stability:** Stable for melt logic, extends in Sprint 06.3 (PROS)
- **Dependencies:**
  - `silver_math` (calculation functions)
- **Key Responsibilities:**
  - Accept list of listing objects
  - Call `silver_math.calc_silver()` for each listing
  - Determine HIT if `total_price <= rec_max_total`
  - Return `List[Evaluated]` with classification results
  - Sort by earliest ending time
- **Data Structures:**
  - Input: `List[Any]` (objects with attributes: `total_price`, `qty`, `oz`, etc.)
  - Output: `List[Evaluated]` where `Evaluated` has fields:
    - `listing` (original object)
    - `silver_calc` (dict from silver_math)
    - `is_hit` (bool)
    - `is_prospect` (bool — always False in Sprint 05.5)
- **Integration Points:**
  - Receives objects from `silver_monitor` (via ListingAdapter)
  - Calls `silver_math.calc_silver(listing)` → `dict`
  - Returns `Evaluated` objects to `silver_monitor`

---

#### `silver_math.py`
- **Owner:** Sprint 05.5
- **Purpose:** Silver economics calculations (melt value, margins, rec max)
- **Stability:** Stable (Contract Section 3 formulas)
- **Dependencies:** None (pure math)
- **Key Responsibilities:**
  - Calculate melt value: `oz * spot_price`
  - Calculate pawn exit: `melt_value * pawn_payout_pct / 100`
  - Calculate rec_max: `(pawn_exit / (1 + min_margin_pct / 100)) * qty`
  - Calculate margin: `((pawn_exit - total_price) / total_price) * 100` if price given
  - Extract silver content (oz) from listing via `get_silver_oz()`
- **Function Contracts:**
  - `calc_silver(listing) -> dict` with keys: `melt_value`, `pawn_exit`, `rec_max_unit`, `rec_max_total`, `margin_pct`, `oz`
  - `get_silver_oz(listing) -> float` — extracts oz from `listing.silver_oz` or `listing.oz`
- **Integration Points:**
  - Called by `classifier.py` for each listing

---

#### `config.py`
- **Owner:** Sprint 05.5
- **Purpose:** Single source of truth for all configuration
- **Stability:** Stable (values updated, structure unchanged)
- **Dependencies:** None
- **Key Constants:**
  - `HTML_FOLDER_PATH` — Where to watch for files
  - `SPOT_PRICE` — Current silver spot (manual update)
  - `PAWN_PAYOUT_PCT` — Pawn exit percentage
  - `MIN_MARGIN_PCT`, `MAX_MARGIN_PCT` — Margin gates
  - `PRICE_STORE_PATH` — Path to price_store.json
  - `EMA_ALPHA` — EMA smoothing factor
  - `PRICE_CAPTURE_BUMP_PCT` — Bump percentage for EMA capture
  - SMTP settings
- **Integration Points:**
  - Imported by all modules needing config values

---

### Parser & Data (Sprints 02-03 — Stable)

#### `parser_listings.py`
- **Owner:** Sprint 03 (extended in Sprint 05.1)
- **Purpose:** Parse eBay search result HTML into structured data
- **Stability:** Stable (do not modify without PM approval)
- **Dependencies:** `beautifulsoup4`
- **Key Function:**
  ```python
  def parse_listings_from_html(
      html_text: str,
      *,
      filter_terms: Optional[Sequence[str]] = None,
      numismatic_flag_patterns: Optional[Sequence[Tuple[str, str]]] = None
  ) -> List[Dict[str, Any]]
  ```
- **Returns:** List of dicts with keys:
  - `title` (str)
  - `qty` (int) — inferred from title
  - `filter_flags` (dict) — boolean flags for filter terms
  - `numismatic_flags` (dict) — boolean flags for numismatic patterns
  - `item_price` (float | None)
  - `ship_price` (float | None)
  - `total_price` (float | None) — item_price + ship_price
  - `bids` (int) — bid count, defaults to 0
  - `time_left` (str | None)
  - `end_clock` (str | None)
  - `item_id` (str) — optional
  - `url` (str) — optional
  
- **Filter Behavior:**
  - Parser does NOT apply time/qty/blacklist filtering
  - Parser only sets flags in `filter_flags` dict
  - **Caller (silver_monitor.py) must filter based on flags**
  
- **Integration Points:**
  - Called by `silver_monitor.py`: `parse_listings_from_html(html_text)`
  - Returns dicts (NOT objects)

---

#### `price_store.py`
- **Owner:** Sprint 02/04
- **Purpose:** Offline EMA price database (benchmark storage)
- **Stability:** Stable (do not modify without PM approval)
- **Dependencies:** `json`, `config`, `utils`
- **Key Functions:**
  ```python
  def load_store(path: Optional[str] = None) -> Store
  # Returns dict (Store type alias for Dict[str, list])
  
  def save_store(store: Store, path: Optional[str] = None) -> None
  # Saves store to JSON file
  
  def update_price(
      store: Store,
      key: str,
      total_price: float,
      bid_count: int,
      *,
      qty: Optional[int] = None,
      title: Optional[str] = None
  ) -> bool
  # Updates EMA for key (with eligibility enforcement)
  # Returns True if update applied, False if ineligible
  
  def get_ema_value(key: str, store: Store | None = None) -> Optional[float]
  # Returns EMA value for key
  
  def get_ema_value_and_observers(
      key: str, 
      store: Store | None = None
  ) -> Tuple[Optional[float], Optional[int]]
  # Returns (ema_value, observers_total) for key
  ```

- **Schema:** Store is `Dict[str, list]` where list = `[ema_price, samples, last_total_price, last_updated_ts, observers_total]`

- **EMA Eligibility (enforced in update_price):**
  - `qty == 1`
  - `bids >= 1`
  - NOT lot/roll/set/face value
  - NOT album/folder/book/"NO COINS"
  - NOT accessory (money clip, keychain, pendant, jewelry, cutout)
  - NOT damaged (holed, hole, pierced, drilled)

- **Integration Points:**
  - Called by `silver_monitor.py`:
    - `load_store()` at start of run
    - `update_price(store, key, total_price, bid_count, qty=qty, title=title)` for each eligible listing
    - `save_store(store)` after updates

---

### Email (Sprint 02 — Stable)

#### `email_builder.py`
- **Owner:** Sprint 02
- **Purpose:** Email skeleton/placeholder functions ONLY
- **Stability:** Stable (do not modify without PM approval)
- **Dependencies:** None
- **Key Functions:**
  ```python
  def build_email_subject(earliest_time: Optional[str], new_count: int) -> str
  # Returns subject line: "<earliest_time> Offline eBay Silver HITS (<N> new)"
  
  def build_email_body_skeleton(
      config: Optional[EmailSkeletonConfig] = None,
      *,
      total_hits: int = 0,
      placeholder_entries: int = 1,
      generated_at: Optional[datetime] = None
  ) -> str
  # Returns placeholder email body (NOT production-ready)
  ```

- **CRITICAL NOTE:**
  - **email_builder.py provides SKELETON ONLY** (placeholders like $XX.XX)
  - **Does NOT provide production email building for actual HITs**
  - **silver_monitor.py MUST implement email body building inline**
  - Can use `build_email_subject()` for subject line format

- **Integration Points:**
  - `silver_monitor.py` may call `build_email_subject()` for subject format
  - `silver_monitor.py` MUST implement own email body building (skeleton not suitable for production)

---

### Utilities (Sprint 01 — Stable)

#### `utils.py`
- **Owner:** Sprint 01
- **Purpose:** Helper functions (time parsing, file I/O, etc.)
- **Stability:** Stable
- **Dependencies:** None
- **Key Functions:**
  - `now_ts()` → Unix timestamp (int)
  - Time parsing helpers
  - File read/write helpers
- **Integration Points:**
  - Imported by multiple modules as needed

---

## Architecture — Component Flow

```
[HTML Files] 
    ↓
silver_monitor.py
    ↓ (reads files)
    ↓
parser_listings.parse_listings_from_html(html_text)
    ↓ (returns List[Dict] with all fields)
    ↓
silver_monitor.py (filters inline based on dict fields)
    ↓ (applies time/qty/blacklist filters)
    ↓
ListingAdapter (silver_monitor.py)
    ↓ (converts Dict → Object)
    ↓
classifier.classify_listings(obj_listings)
    ├─→ silver_math.calc_silver(listing) → dict
    └─→ Returns List[Evaluated]
        ↓
silver_monitor.py
    ├─→ Dedupe HITs
    ├─→ Console output (inline)
    ├─→ Build email body (inline, NOT email_builder)
    ├─→ Send email via SMTP (inline)
    └─→ price_store.update_price() for each eligible listing
        └─→ price_store.save_store(store)
```

---

## Integration Contracts

### parser_listings → silver_monitor

**Function:** `parse_listings_from_html(html_text, *, filter_terms=None, numismatic_flag_patterns=None)`  
**Returns:** `List[Dict[str, Any]]`  

**Dict Keys (all present, some may be None):**
- `title` (str)
- `qty` (int) — defaults to 1 if not in title
- `filter_flags` (dict) — e.g., `{"has_copy": False, "has_replica": False, ...}`
- `numismatic_flags` (dict) — e.g., `{"has_pcgs": True, "has_ngc": False, ...}`
- `item_price` (float | None)
- `ship_price` (float | None)
- `total_price` (float | None)
- `bids` (int) — defaults to 0
- `time_left` (str | None)
- `end_clock` (str | None)
- `item_id` (str) — optional, may not be in dict
- `url` (str) — optional, may not be in dict

**Usage:**
```python
import parser_listings

html = read_file(filepath)
listings = parser_listings.parse_listings_from_html(html_text=html)
# listings is List[Dict]

# Parser does NOT filter - caller must filter
# Example filtering:
filtered = []
for listing in listings:
    # Time filter (implement based on time_left or end_clock)
    # Qty filter: listing["qty"] >= min_qty
    # Blacklist filter: check listing["filter_flags"]
    if passes_filters(listing):
        filtered.append(listing)
```

**IMPORTANT:**
- Parser only accepts `html_text` as positional arg
- Optional kwargs: `filter_terms`, `numismatic_flag_patterns`
- **Does NOT accept:** `max_time_hours`, `default_min_qty`, `keyword_blacklist`
- **Caller must implement all filtering logic**

---

### silver_monitor → classifier

**Function:** `classify_listings(listings)`  
**Input:** `List[Any]` (objects with attributes)  
**Returns:** `List[Evaluated]`

**Preparation (ListingAdapter):**
```python
class ListingAdapter:
    """Bridge: Dict → Object with attribute access."""
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def __getattr__(self, name: str):
        return self._data.get(name)

# Convert dicts to objects
dict_listings = parser_listings.parse_listings_from_html(html)
obj_listings = [ListingAdapter(d) for d in dict_listings]
results = classifier.classify_listings(obj_listings)
```

---

### classifier → silver_math

**Function:** `calc_silver(listing)`  
**Input:** Object with attributes: `oz` (or `silver_oz`), `qty`, `total_price`  
**Returns:** `dict` with keys:
- `oz` (float)
- `melt_value` (float)
- `pawn_exit` (float)
- `rec_max_unit` (float)
- `rec_max_total` (float)
- `margin_pct` (float or None)

**Usage:**
```python
import silver_math

for listing in obj_listings:
    calc = silver_math.calc_silver(listing)
    is_hit = (listing.total_price <= calc["rec_max_total"])
```

---

### silver_monitor → email_builder

**Limited Integration - Skeleton Only:**

```python
import email_builder

# Can use for subject format:
subject = email_builder.build_email_subject(
    earliest_time=earliest_time_str,
    new_count=len(new_hits)
)

# CANNOT use build_email_body_skeleton() for production
# Must implement email body building inline in silver_monitor.py
```

**What silver_monitor.py must implement:**
- Email body formatting with actual HIT data
- Melt value, margin, profit calculations displayed
- Listing details (title, price, qty, time, links)
- Per Contract v1.2 Section 2 formatting

---

### silver_monitor → price_store

**Functions:**

```python
import price_store

# Load at start of run
store = price_store.load_store()
# Returns: Dict[str, list]

# Update for each eligible listing
success = price_store.update_price(
    store=store,
    key="morgan_dollar|1921|D",
    total_price=42.50,
    bid_count=5,
    qty=1,
    title="1921-D Morgan Dollar AU"
)
# Returns: True if updated (eligible), False if ineligible

# Save after updates
price_store.save_store(store)
# Returns: None (side effect: updates price_store.json)
```

**Eligibility (enforced automatically by update_price):**
- Function checks all eligibility rules internally
- Returns False (no-op) if ineligible
- Returns True if update applied

**Key Construction:**
- Caller must construct key (e.g., "coin_type|year|mint")
- Key format is caller's responsibility

---

## Component Boundaries

### What Lives Where

**silver_monitor.py:**
- File discovery (glob HTML folder)
- Main loop (cycle control)
- **Filtering logic** (time/qty/blacklist) — parser only provides flags
- Console output formatting (inline)
- **Email body building** (inline) — email_builder only has skeleton
- Deduplication logic (seen_hits.json)
- ListingAdapter class
- Orchestration (calls other modules)

**classifier.py:**
- Classification logic (HIT/MISS)
- Evaluated dataclass
- Sorting by end time

**silver_math.py:**
- All math formulas (Contract Section 3)
- Silver content extraction

**parser_listings.py:**
- HTML parsing (BeautifulSoup)
- Title extraction
- Price/bid/time extraction
- **Flag generation only** (filter_flags, numismatic_flags)
- **No filtering** — caller must filter

**email_builder.py:**
- Skeleton/placeholder functions only
- Subject line formatting helper
- **Not suitable for production email bodies**

**price_store.py:**
- JSON file I/O
- EMA calculation and update
- Eligibility enforcement (internal)
- Key-based storage/retrieval

**config.py:**
- All configuration constants
- No logic, just values

---

## Sprint History

| Sprint | Files Created/Modified | Status |
|--------|------------------------|--------|
| 01 | utils.py | Stable |
| 02 | email_builder.py (skeleton), price_store.py | Stable |
| 03 | parser_listings.py | Stable |
| 04 | price_store.py (EMA updates) | Stable |
| 05 | prospect_score.py | Stable |
| 05.1 | parser_listings.py (extended with pricing) | Stable |
| 05.5 | silver_monitor.py, classifier.py, silver_math.py, config.py | Requires re-implementation |
| 06.1 | (next: diagnostics) | Planned |

---

## Critical Notes for Sprint 05.5

**What Changed from SRM v1.4:**

1. **Parser does NOT filter**
   - v1.4 showed: `parse_listings_from_html(html_text, max_time_hours, default_min_qty, keyword_blacklist)`
   - Reality: `parse_listings_from_html(html_text)` only
   - silver_monitor.py must implement all filtering inline

2. **price_store function names**
   - v1.4 showed: `load_price_store()`, `save_price_store()`, `capture_ema_from_listings()`
   - Reality: `load_store()`, `save_store()`, `update_price()`

3. **email_builder is skeleton only**
   - v1.4 implied: Production email building available
   - Reality: Only skeleton/placeholders, must implement inline

4. **Parser returns comprehensive dict**
   - Includes: item_price, ship_price, total_price, bids, time_left, end_clock
   - All fields available for filtering and display

---

**SRM v1.5 — Authoritative as of December 31, 2025**
**Verified against actual source code from Sprints 02-05.1**