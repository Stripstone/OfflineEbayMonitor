markdown# SYSTEM RESPONSIBILITY MAP v1.4
**Updated:** December 31, 2025  
**Previous Version:** v1.3 (deprecated — had incorrect parser function name)

---

## Changes from v1.3

**Critical Corrections:**
1. Parser function name: `parse_ebay_search_html()` → `parse_listings_from_html()`
2. Parser return type: Clarified as `List[Dict[str, Any]]` (not objects)
3. Added ListingAdapter as approved architectural component
4. Corrected integration flow documentation

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
  - `email_builder` (send alerts)
  - `config` (all settings)
- **Key Responsibilities:**
  - Discover HTML files in watch folder
  - Parse each file via `parser_listings.parse_listings_from_html()`
  - Apply filters (time/qty/blacklist)
  - Convert dicts → objects via ListingAdapter
  - Classify listings via `classifier.classify_listings()`
  - Deduplicate HITs (cross-run)
  - Print console output
  - Send email alerts
  - Capture EMA data via `price_store`
- **Integration Points:**
  - Calls `parser_listings.parse_listings_from_html(html_text, ...)` → `List[Dict]`
  - Calls `classifier.classify_listings(obj_listings)` → `List[Evaluated]`
  - Calls `email_builder.build_email_body_simple(new_hits)` → `str`
  - Calls `price_store.capture_ema_from_listings(eligible_listings)`

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
  - `MAX_TIME_HOURS` — Time filter threshold
  - `SILVER_FILENAME_KEYWORDS` — File selection keywords
  - SMTP settings
- **Integration Points:**
  - Imported by all modules needing config values

---

### Parser & Data (Sprints 02-03 — Stable)

#### `parser_listings.py`
- **Owner:** Sprint 03
- **Purpose:** Parse eBay search result HTML into structured data
- **Stability:** Stable (do not modify without PM approval)
- **Dependencies:** `beautifulsoup4`, `utils`
- **Key Function:**
```python
  def parse_listings_from_html(
      html_text: str,
      max_time_hours: float = None,
      default_min_qty: int = None,
      keyword_blacklist: List[str] = None
  ) -> List[Dict[str, Any]]
```
- **Returns:** List of dicts with keys:
  - `title`, `qty`, `filter_flags`, `total_price`, `bids`
  - `time_left`, `end_clock`, `url`, `item_id`, `image_url`
- **Filter Flags:**
  - `time_ok`: True if ending within `max_time_hours`
  - `qty_ok`: True if qty >= `default_min_qty`
  - `blacklist_ok`: True if no blacklist keywords in title
- **Integration Points:**
  - Called by `silver_monitor.py`: `parse_listings_from_html(html)`
  - Returns dicts (NOT objects)

---

#### `price_store.py`
- **Owner:** Sprint 02
- **Purpose:** Offline EMA price database (benchmark storage)
- **Stability:** Stable (do not modify without PM approval)
- **Dependencies:** `json`
- **Key Functions:**
  - `capture_ema_from_listings(listings)` — Store eligible listings
  - `load_price_store()` → `dict`
  - `save_price_store(data)`
- **Schema:** See Contract v1.2 Section 7
- **Integration Points:**
  - Called by `silver_monitor.py` after classification

---

### Email (Sprint 02 — Stable)

#### `email_builder.py`
- **Owner:** Sprint 02
- **Purpose:** Format and send email alerts
- **Stability:** Stable (do not modify without PM approval)
- **Dependencies:** `smtplib`, `email`, `config`
- **Key Functions:**
  - `build_email_body_simple(hits: List[Evaluated]) -> str`
  - `send_email(subject: str, body: str) -> bool`
- **Integration Points:**
  - Called by `silver_monitor.py` when `new_hit_count > 0`

---

### Utilities (Sprint 01 — Stable)

#### `utils.py`
- **Owner:** Sprint 01
- **Purpose:** Helper functions (time parsing, file I/O, etc.)
- **Stability:** Stable
- **Dependencies:** None
- **Key Functions:**
  - Time parsing helpers
  - File read/write helpers
- **Integration Points:**
  - Imported by multiple modules as needed

---

## Architecture — Component Flow
[HTML Files]
↓
silver_monitor.py
↓ (reads files)
↓
parser_listings.parse_listings_from_html(html)
↓ (returns List[Dict])
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
├─→ Console output
├─→ email_builder.send_email(subject, body)
└─→ price_store.capture_ema_from_listings(eligible)

---

## Integration Contracts

### parser_listings → silver_monitor
**Function:** `parse_listings_from_html(html_text, max_time_hours, default_min_qty, keyword_blacklist)`  
**Returns:** `List[Dict[str, Any]]`  
**Dict Keys:** `title`, `qty`, `filter_flags`, `total_price`, `bids`, `time_left`, `end_clock`, `url`, `item_id`, `image_url`

**Usage:**
```python
import parser_listings

html = read_file(filepath)
listings = parser_listings.parse_listings_from_html(
    html_text=html,
    max_time_hours=config.MAX_TIME_HOURS,
    default_min_qty=config.DEFAULT_MIN_QUANTITY,
    keyword_blacklist=config.DEFAULT_BLACKLIST
)
# listings is List[Dict]
```

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
**Function:** `build_email_body_simple(hits)`  
**Input:** `List[Evaluated]` (with `is_hit=True`)  
**Returns:** `str` (formatted email body per Contract Section 2)

**Function:** `send_email(subject, body)`  
**Input:** `str`, `str`  
**Returns:** `bool` (True if sent successfully)

**Usage:**
```python
import email_builder

subject = f"{earliest_time} Offline eBay Silver HITS ({len(new_hits)} new)"
body = email_builder.build_email_body_simple(new_hits)
success = email_builder.send_email(subject, body)
```

---

### silver_monitor → price_store
**Function:** `capture_ema_from_listings(listings)`  
**Input:** `List[Dict]` (dicts with `filter_flags`, `item_id`, `total_price`, `qty`, `title`)  
**Returns:** None (side effect: updates `price_store.json`)

**Usage:**
```python
import price_store

# After classification, capture eligible listings
eligible = [d for d in dict_listings if all(d["filter_flags"].values())]
price_store.capture_ema_from_listings(eligible)
```

---

## Component Boundaries

### What Lives Where

**silver_monitor.py:**
- File discovery (glob HTML folder)
- Main loop (cycle control)
- Console output formatting
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
- Time parsing
- Filter flag generation

**email_builder.py:**
- Email body formatting
- SMTP sending

**price_store.py:**
- JSON file I/O
- EMA data schema
- Eligibility filtering for capture

**config.py:**
- All configuration constants
- No logic, just values

---

## Sprint History

| Sprint | Files Created/Modified | Status |
|--------|------------------------|--------|
| 01 | utils.py | Stable |
| 02 | email_builder.py, price_store.py | Stable |
| 03 | parser_listings.py | Stable |
| 04 | (planning/design) | N/A |
| 05 | (planning/design) | N/A |
| 05.5 | silver_monitor.py, classifier.py, silver_math.py, config.py | Re-verification needed |
| 06.1 | (next: diagnostics) | Planned |

---

**SRM v1.4 — Authoritative as of December 31, 2025**