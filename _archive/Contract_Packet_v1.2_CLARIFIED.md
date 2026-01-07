markdown# CONTRACT PACKET v1.2 + CLARIFICATIONS
**Original Contract:** v1.2 (December 2025)  
**Clarifications Added:** December 31, 2025  
**Status:** Authoritative

---

## CLARIFICATION ADDENDUM — December 31, 2025

### Issue #1: Console Output Format — Counts Line

**Original Contract (Section 1, line 18):**
> Counts line (Found / Eligible / HITs / PROS)

**Ambiguity:** Exact format not specified (separators, labels, spacing)

**CLARIFICATION — OFFICIAL FORMAT:**
Found: <count> | Eligible: <count> | HITs: <count> | New: <count>

**Requirements:**
- Labels: "Found:", "Eligible:", "HITs:", "New:" (exact capitalization)
- Separator: ` | ` (space-pipe-space between each field)
- Spacing: Single space after colon before number
- Numbers: Integer count (no decimals)
- Order: Fixed (Found, Eligible, HITs, New)

**Example:**
Found: 62 | Eligible: 62 | HITs: 0 | New: 0

---

### Issue #2: Table Column — Target Definition

**Original Contract (Section 1):**
> Table columns (fixed, in order): Target | Found | Hit? | Price | QTY | Time Left | Title

**Ambiguity:** "Target" column listed but source not specified

**CLARIFICATION — TARGET COLUMN:**
- **Value:** Static string "Silver" for all listings
- **Justification:** All monitored files are silver-related searches
- **Future:** May become dynamic in later sprints (filename-based detection)
- **Sprint 05.5:** Hardcoded as "Silver"

**Example:**
Target  | Found | Hit? | Price    | QTY | Time Left            | Title
Silver  | 12    | HIT  | $125.00  | 10  | 2h 15m (ends 3:45p) | 1964 Kennedy Half...

---

### Issue #3: Parser Integration — Function Name & Return Type

**Original Contract:** Did not specify parser function details

**Ambiguity:** SRM v1.3 documented non-existent function name

**CLARIFICATION — PARSER INTEGRATION:**

**Function:**
```python
parser_listings.parse_listings_from_html(
    html_text: str,
    max_time_hours: float = None,
    default_min_qty: int = None,
    keyword_blacklist: List[str] = None
) -> List[Dict[str, Any]]
```

**Returns:** List of dictionaries with keys:
- `title` (str)
- `qty` (int)
- `filter_flags` (dict)
- `total_price` (float)
- `bids` (int)
- `time_left` (str)
- `end_clock` (str)
- `url` (str)
- `item_id` (str)
- `image_url` (str)

**Integration Pattern:**
```python
html = read_file(filepath)
listings = parser_listings.parse_listings_from_html(html)
# listings is List[Dict[str, Any]]
```

**Note:** Parser returns dicts, not objects. If downstream code expects objects, an adapter layer is required.

---

### Issue #4: ListingAdapter Component

**Context:** Not mentioned in original Contract v1.2

**CLARIFICATION — LISTINGADAPTER STATUS:**

**Component:** ListingAdapter class (in `silver_monitor.py` or dedicated module)

**Purpose:** Bridge parser output (dicts) → classifier input (objects)

**Justification:**
- Parser outputs: `List[Dict[str, Any]]`
- Classifier expects: Objects with attribute access (e.g., `listing.total_price`)
- Adapter converts dict keys to object attributes

**Status:** **Approved architectural component** (not scope creep)

**Implementation:**
```python
class ListingAdapter:
    """Adapter: dict → object with attribute access."""
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def __getattr__(self, name: str):
        return self._data.get(name)
```

**Usage:**
```python
dict_listings = parser_listings.parse_listings_from_html(html)
obj_listings = [ListingAdapter(d) for d in dict_listings]
results = classifier.classify_listings(obj_listings)
```

**Requirement:** If using ListingAdapter, document in implementation notes why it exists.

---

## ORIGINAL CONTRACT v1.2 (Unchanged)

[Original contract content below — no changes to original sections]

---

### Section 1: Console UX Contract

**Per-Cycle Output Structure:**
1. Banner line: `[HH:MM:SS] Starting scan cycle #N...`
2. Config block (4 lines):
   - Spot price
   - Pawn payout %
   - Margin gates (min/max)
   - Time filter (if active)
3. Counts line: `Found: X | Eligible: Y | HITs: Z | New: W` (see Clarification #1)
4. Per-file tables (if listings found)
5. Email status line
6. Blank line (cycle separator)

**Per-File Table Format:**
- Header: `--- [filename] (X found) ---`
- Columns (fixed order): `Target | Found | Hit? | Price | QTY | Time Left | Title`
- Target value: "Silver" (see Clarification #2)
- Found: Integer count
- Hit?: "HIT" or "MISS"
- Price: `$X.XX` format
- QTY: Integer
- Time Left: `Xh Ym (ends H:MMa/p)` format
- Title: Truncated to 50 chars max

**Time Format Rules:**
- Console timestamps: `[HH:MM:SS]` (24-hour, leading zeros)
- Listing end times: `3:45p` / `11:30a` (12-hour, lowercase am/pm)
- Time remaining: `2h 15m` (no leading zeros on hours)

---

### Section 2: Email UX Contract

**Subject Line:**
<earliest_end_time> Offline eBay Silver HITS (N new)

**Body Structure:**
New HITs found: N
[Entry 1]
[Entry 2]
...
Sent from eBay Offline Silver Monitor

**Entry Format (each HIT):**
[HIT] <Title>
Price: $X.XX | QTY: Y | Melt: $M.MM | Rec Max: $R.RR | Margin: P%
Time: <time_remaining> (ends H:MMa/p)
Link: <url>

**Entry Rules:**
- Sorted by earliest ending time first
- Title: Full text (no truncation)
- All prices: `$X.XX` format (2 decimals)
- Margin: Integer percentage
- Time: Same format as console

---

### Section 3: Math Contract

**Formula #1: Melt Value**
melt_value = oz * spot_price

**Formula #2: Pawn Exit (Guaranteed Floor)**
pawn_exit = melt_value * (pawn_payout_pct / 100)

**Formula #3: Recommended Max Bid (Melt-Only)**
rec_max_unit = pawn_exit / (1 + min_margin_pct / 100)
rec_max_total = rec_max_unit * qty

**Formula #4: Margin Calculation (If Purchase)**
If total_price provided:
margin_pct = ((pawn_exit - total_price) / total_price) * 100
Else:
margin_pct = None

**Rounding Rules:**
- All dollar amounts: Round to 2 decimals (half-up)
- All percentages: Round to nearest integer (half-up)
- Intermediate calculations: Full precision until final output

**Edge Cases:**
- If `oz = 0` → `melt_value = 0`, `rec_max = 0`
- If `qty = 0` → `rec_max_total = 0`
- If `total_price = 0` → `margin_pct = None` (undefined)
- If `total_price > pawn_exit` → `margin_pct` will be negative (valid)

---

### Section 4: Link Contract

**eBay Listing URL Format:**
https://www.ebay.com/itm/<item_id>

**Requirements:**
- `item_id` extracted from parser output
- No query parameters
- No trailing slashes
- Must be clickable hyperlink in email

---

### Section 5: Process Non-Negotiables

**Sprint Gates:**
1. Sprint Plan must cite Contract sections
2. Acceptance criteria must be verifiable
3. Build cannot proceed without Sprint Plan
4. Verifier validates against Contract + Sprint Plan

**Handoff Rules:**
- PM → Build: Sprint Plan + Contract + SRM
- Build → Verifier: Implementation + Sprint Plan
- Verifier → PM: PASS or FAIL (no suggestions)

**Scope Discipline:**
- Sprint Plan defines boundaries
- Out-of-scope items explicitly listed
- Build cannot add unlisted features
- PM cannot override Verifier FAIL without Contract Vault

---

### Section 6: Unchanging Constants

**File System:**
- HTML folder: `C:\Users\Triston Barker\Desktop\EbayMiner\ebay_pages`
- Price store: `price_store.json` (same directory as scripts)
- Seen hits: `seen_hits.json` (same directory as scripts)

**SMTP Config:**
- Host: `smtp.gmail.com`
- Port: `587`
- TLS: Required
- Auth: Username/password from config
- From: `tbarker.srs@gmail.com`
- To: `tbarker.srs@gmail.com`

**Silver Filename Keywords:**
`["morgan", "peace", "barber", "seated", "franklin", "kennedy", "walking", "silver"]`

---

### Section 7: EMA & Price Store Contract

**Eligibility Rules:**
- Listing must have `filter_flags["time_ok"] = True`
- Listing must have `filter_flags["qty_ok"] = True`
- Listing must have `filter_flags["blacklist_ok"] = True`
- No bids OR final sold price available

**Capture Trigger:**
- Run at end of scan cycle (after classification)
- Only capture listings that passed eligibility

**Data Schema:**
```json
{
  "item_id": {
    "total_price": float,
    "qty": int,
    "unit_price": float,
    "timestamp": ISO8601 string,
    "title": string,
    "source": "ebay_offline"
  }
}
```

**Source Rendering:**
- All stored prices have `source: "ebay_offline"`
- Never infer or fetch live prices
- Only capture from processed HTML files

---

### Section 8: Diagnostic Observability Addendum (Sprint 06)

**Invariants:**
- Sprint 05.5 foundation must pass verification first
- Diagnostics do not change HIT/MISS classification logic
- Diagnostics do not change console/email output for HITs
- Diagnostics add observability, not new features

**Scope:**
- Rejection reasons (why MISS happened)
- PROS detection (placeholder for Sprint 06.3)
- Filter diagnostics (time/qty/blacklist)
- No user-facing changes to HIT workflow

---

**END OF CONTRACT PACKET v1.2 + CLARIFICATIONS**