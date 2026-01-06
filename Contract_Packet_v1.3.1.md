# CONTRACT PACKET v1.3.1
**Previous Version:** v1.3 (December 31, 2025)  
**Current Version:** v1.3.1 (January 6, 2026)  
**Status:** Authoritative

---

## CHANGELOG: v1.3 → v1.3.1

**Clarifications Added:**
- **Clarification Issue #5:** Price store key format specification (Contract Vault ruling January 6, 2026)
  - Normalized format: `"<CoinSeries>|<Year>|<Mint>"`
  - Coin series detection rules
  - Year extraction pattern
  - Mint mark extraction pattern

**Unchanged:**
- All 8 sections (1-8)
- Clarifications #1-4

---

## CHANGELOG: v1.2 → v1.3

**Major Changes:**
- **Section 2 (Email UX Contract):** Replaced minimal 4-line specification with complete end-state specification including:
  - Full subject line format with field references
  - Header section (spot, pawn, margins, time filter)
  - Melt entry format (detailed multi-line breakdown)
  - Numismatic entry format (dealer payout, FMV, CoinBook links)
  - Footer (generated timestamp + signature)
  - Field legend (30+ fields with formulas)
  - Link construction rules
  - Entry dividers and numbering

**Unchanged:**
- Section 1 (Console UX Contract)
- Section 3 (Math Contract)
- Section 4 (Link Contract)
- Section 5 (Process Non-Negotiables)
- Section 6 (Unchanging Constants)
- Section 7 (EMA & Price Store Contract)
- Section 8 (Diagnostic Observability Addendum)
- All 4 Clarifications from v1.2

**Implementation Note:**
Section 2 defines **end-state email format** (after all sprints complete). Sprints implement progressively:
- Sprint 05.5: Melt entries only (placeholders for numismatic fields)
- Sprint 06.3: Adds numismatic entries
- Unimplemented fields show placeholders until relevant sprint

---

## CLARIFICATION ADDENDUM (5 Total)

**Issues #1-4:** Retained from v1.2 (December 31, 2025)  
**Issue #5:** Added in v1.3.1 (January 6, 2026)

### Issue #1: Console Output Format — Counts Line

**Original Contract (Section 1):**
> Counts line (Found / Eligible / HITs / PROS)

**CLARIFICATION — OFFICIAL FORMAT:**
```
Found: <count> | Eligible: <count> | HITs: <count> | New: <count>
```

**Requirements:**
- Labels: "Found:", "Eligible:", "HITs:", "New:" (exact capitalization)
- Separator: ` | ` (space-pipe-space between each field)
- Spacing: Single space after colon before number
- Numbers: Integer count (no decimals)
- Order: Fixed (Found, Eligible, HITs, New)

**Example:**
```
Found: 62 | Eligible: 62 | HITs: 0 | New: 0
```

---

### Issue #2: Table Column — Target Definition

**Original Contract (Section 1):**
> Table columns (fixed, in order): Target | Found | Hit? | Price | QTY | Time Left | Title

**CLARIFICATION — TARGET COLUMN:**
- **Value:** Static string "Silver" for all listings
- **Justification:** All monitored files are silver-related searches
- **Future:** May become dynamic in later sprints (filename-based detection)
- **Sprint 05.5:** Hardcoded as "Silver"

**Example:**
```
Target  | Found | Hit? | Price    | QTY | Time Left            | Title
Silver  | 12    | HIT  | $125.00  | 10  | 2h 15m (ends 3:45p) | 1964 Kennedy Half...
```

---

### Issue #3: Parser Integration — Function Name & Return Type

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

**CLARIFICATION — LISTINGADAPTER STATUS:**

**Component:** ListingAdapter class (in `silver_monitor.py` or dedicated module)

**Purpose:** Bridge parser output (dicts) → classifier input (objects)

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

### Issue #5: Price Store Key Format

**Context:** Contract v1.2 Section 7 did not specify key format

**Ambiguity:** Keys were title-based (inconsistent, non-deterministic)

**CLARIFICATION — PRICE STORE KEY FORMAT:**

**Format:**
```
"<CoinSeries>|<Year>|<Mint>"
```

**Parsing Rules:**

**Coin Series Detection:**
- "Morgan" + "Dollar" → "Morgan Dollar"
- "Peace" + "Dollar" → "Peace Dollar"
- "Kennedy" + ("Half" or "50") → "Kennedy Half"
- "Walking Liberty" + ("Half" or "50") → "Walking Liberty Half"
- "Franklin" + ("Half" or "50") → "Franklin Half"
- "Barber" + ("Half" or "50") → "Barber Half"
- "Seated" + ("Half" or "50") → "Seated Liberty Half"

**Year Extraction:**
- Pattern: `\b(1[7-9]\d{2}|20\d{2})\b` (1794-2099)
- Match first valid 4-digit year in title

**Mint Mark Extraction:**
- Pattern: `\b([PDSOC]{1,2})\b` after year
- CC = Carson City (two letters)
- P/D/S/O = Single letter mints
- Empty string if no mint found

**Examples:**
- `"1881 CC MORGAN DOLLAR..."` → `"Morgan Dollar|1881|CC"`
- `"1922 PEACE SILVER DOLLAR"` → `"Peace Dollar|1922|"`
- `"1964 Kennedy Half Dollar"` → `"Kennedy Half|1964|"`

**Authority:** Contract Vault ruling January 6, 2026

---

## SECTION 1: Console UX Contract

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

## SECTION 2: Email UX Contract (Complete Specification)

**Status:** End-state specification (progressive implementation across sprints)

### Subject Line Format
```
[A1] Offline eBay Silver HITS ([A6] new)
```
- `[A1]` = Earliest listing time (h:mm AM/PM format)
- `[A6]` = Total number of HITs included in this email

### Header Section
```
Spot: [A2] | Pawn: [A3]%
Bid offset: [A4]
Target margin: [A5-min]%—[A5-max]%
Max time left: [A7] hours
Total HITs: [A6]
```

**Field Definitions (Header):**
- `[A2]` = Spot price per ounce (USD)
- `[A3]` = Pawn payout fraction (%)
- `[A4]` = Bid offset (USD)
- `[A5-min]` / `[A5-max]` = Target margin range (%)
- `[A6]` = Total HIT count (same as subject)
- `[A7]` = Max time left filter (hours)

### Melt Entry Format
```
----------------------------------------
#[N] [F1]
Title: [F2]

Current Total: [B3] (item [B1] + ship [B2])
Current Profit (pawn): [D1] ([D2] margin vs pawn)
RecMaxBid: [D4] ([D3] incl. ship) | [D5$] ([D5%] margin vs pawn)

Qty: [C1] | oz/coin: [C2] | Total oz: [C3]
Melt: [C4] | Pawn payout: [C5]
Time left: [T1] ([T2])

Links: Link to Listing | Link to Ebay Sales
----------------------------------------
```

**Field Definitions (Melt Entry):**
- `[N]` = Entry number (sequential)
- `[F1]` = Listing filename / ID
- `[F2]` = Listing title (full text, no truncation)
- `[B1]` = Item price (USD)
- `[B2]` = Shipping (USD, default 0 if missing)
- `[B3]` = Current Total = `B1 + B2`
- `[C1]` = Quantity
- `[C2]` = oz per coin (from coin-type table lookup)
- `[C3]` = Total oz = `C1 * C2`
- `[C4]` = Melt = `C3 * A2` (spot price)
- `[C5]` = Pawn payout = `C4 * (A3 / 100)`
- `[D1]` = Current Profit (pawn) = `C5 - B3`
- `[D2]` = Current margin % = `D1 / B3 * 100`
- `[D3]` = RecMaxTotal incl. ship (computed to satisfy target margin min)
- `[D4]` = RecMaxBid (item only) = `D3 - B2 - A4`
- `[D5$]` = Profit at max bid = `C5 - D3`
- `[D5%]` = Margin at max bid = `D5$ / D3 * 100`
- `[T1]` = Time left string (e.g., "32s", "52m", "3h 42m")
- `[T2]` = Time left absolute (e.g., "Today 03:32 PM")

### Numismatic Entry Format
```
----------------------------------------
#[N] [F1]
Title: [F2]
<<<< Numismatic override: [F3] >>>>

Est. dealer payout (@[E-dealer-%]%): [E2] (est. profit: [E3$], [E3-margin]% margin vs current)
FMV floor (G—VG): [E1] | Source: Offline EMA [E-source-version]
Current Total: [B3] (item [B1] + ship [B2])
Current Profit: [D1] ([D2] margin)
RecMaxTotal (incl. ship): [D3]
RecMaxBid (item only): [D4]

Qty: [C1] | oz/coin: [C2] | Total oz: [C3]
Melt: [C4] | Pawn payout: [C5]
Time left: [T1] ([T2])

Links: Link to Listing | Link to Ebay Sales | Link to CoinBook
----------------------------------------
```

**Additional Field Definitions (Numismatic Entry):**
- `[F3]` = Numismatic override title (optional, for clarity)
- `[E1]` = FMV floor (from EMA source / historical data)
- `[E2]` = Est. dealer payout = `E1 * dealer_fraction`
- `[E3$]` = Dealer profit = `E2 - B3`
- `[E3-margin]` = Dealer margin % = `E3$ / B3 * 100`
- `[E-dealer-%]` = Dealer payout fraction (%)
- `[E-source-version]` = EMA data source version identifier

### Footer
```
Generated at: [A8]
```
- `[A8]` = Timestamp of email render (YYYY-MM-DD HH:MM:SS)

### Entry Rules
- **Sorting:** Entries ordered strictly by earliest time left (ascending)
- **Numbering:** Sequential from #1
- **Dividers:** Each entry preceded and followed by 40-dash line
- **Title:** Full text (no truncation) in email
- **Links:** 
  - "Link to Listing" → eBay item page
  - "Link to Ebay Sales" → eBay sold listings search
  - "Link to CoinBook" → Coin directory (numismatic only)

### Link Construction Rules

**eBay Listing URL:**
```
https://www.ebay.com/itm/<item_id>
```

**eBay Sales URL:**
```
https://www.ebay.com/sch/i.html?_nkw=<series>+<year>+<mint>&LH_Sold=1&LH_Complete=1
```
- Include series, year, mint mark
- Add grade placeholder if available

**CoinBook URL:**
```
https://www.pcgs.com/coinfacts/<series-slug>
```
- Series-level directory only (no deep links to specific years/mints)

### Formatting Rules
- All dollar amounts: `$X.XX` format (2 decimals)
- All percentages: Integer format (1 decimal if needed for clarity)
- All margins: Cost-basis calculation
- Dividers: 40 dashes (`-` character)
- Spacing: Exact as shown in templates

---

## SECTION 3: Math Contract

**Formula #1: Melt Value**
```
melt_value = oz * spot_price
```

**Formula #2: Pawn Exit (Guaranteed Floor)**
```
pawn_exit = melt_value * (pawn_payout_pct / 100)
```

**Formula #3: Recommended Max Bid (Melt-Only)**
```
rec_max_unit = pawn_exit / (1 + min_margin_pct / 100)
rec_max_total = rec_max_unit * qty
```

**Formula #4: Margin Calculation (If Purchase)**
```
If total_price provided:
    margin_pct = ((pawn_exit - total_price) / total_price) * 100
Else:
    margin_pct = None
```

**Formula #5: Dealer Payout (Numismatic)**
```
dealer_payout = fmv_floor * (dealer_payout_pct / 100)
dealer_profit = dealer_payout - total_price
dealer_margin = (dealer_profit / total_price) * 100
```

**Rounding Rules:**
- All dollar amounts: Round to 2 decimals (half-up)
- All percentages: Round to nearest integer (half-up), 1 decimal if needed for clarity
- Intermediate calculations: Full precision until final output

**Edge Cases:**
- If `oz = 0` → `melt_value = 0`, `rec_max = 0`
- If `qty = 0` → `rec_max_total = 0`
- If `total_price = 0` → `margin_pct = None` (undefined)
- If `total_price > pawn_exit` → `margin_pct` will be negative (valid)

---

## SECTION 4: Link Contract

**eBay Listing URL Format:**
```
https://www.ebay.com/itm/<item_id>
```

**Requirements:**
- `item_id` extracted from parser output
- No query parameters
- No trailing slashes
- Must be clickable hyperlink in email

**eBay Sales Search URL:**
- Include series + year + mint mark
- Add grade placeholder if available
- Include LH_Sold=1 and LH_Complete=1 parameters

**CoinBook URL:**
- Series-level directory only
- No deep links to specific years/mints/grades

---

## SECTION 5: Process Non-Negotiables

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

## SECTION 6: Unchanging Constants

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
```python
["morgan", "peace", "barber", "seated", "franklin", "kennedy", "walking", "silver"]
```

---

## SECTION 7: EMA & Price Store Contract

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
    "timestamp": "ISO8601 string",
    "title": "string",
    "source": "ebay_offline"
  }
}
```

**Source Rendering:**
- All stored prices have `source: "ebay_offline"`
- Never infer or fetch live prices
- Only capture from processed HTML files

---

## SECTION 8: Diagnostic Observability Addendum (Sprint 06)

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

**END OF CONTRACT PACKET v1.3.1**
