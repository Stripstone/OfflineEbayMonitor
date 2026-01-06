# Sprint 05.6 Plan — Price Store Key Normalization

**Goal:** Normalize price_store keys to enable proper EMA aggregation across similar coins

**Contract Version:** v1.2 + Clarification Issue #5 (January 6, 2026)  
**SRM Version:** v1.4  
**Master Sprint Plan Reference:** Ad-hoc foundation fix (between Sprint 05.5 and Sprint 06)

---

## Files in Scope

### To Modify:

#### `parser_listings.py`
**Changes:**
- Add coin metadata extraction function
- Extract: coin series, year, mint mark from title
- Return metadata dict with each listing

**Contract Reference:** Contract v1.2 Clarification Issue #5

---

#### `price_store.py`
**Changes:**
- Change key format from title-based to normalized
- New format: `"<CoinSeries>|<Year>|<Mint>"`
- Update all read/write operations

**Contract Reference:** Contract v1.2 Clarification Issue #5

---

### Reference Only:

- `silver_monitor.py` — No changes (calls remain same)
- `config.py` — No changes
- `classifier.py` — No changes

---

## Acceptance Criteria

### 1. **Coin Metadata Extraction**
- **Contract:** Clarification Issue #5, Parsing Rules
- **Verification:**
  - Parser extracts coin series from title
  - Parser extracts 4-digit year (1794-2099)
  - Parser extracts mint mark (P/D/S/O/CC) or empty string
  - Returns dict: `{"series": str, "year": str, "mint": str}`

### 2. **Normalized Keys Generated**
- **Contract:** Clarification Issue #5, Key Format
- **Verification:**
  - Keys format: `"Morgan Dollar|1881|CC"`
  - Keys format: `"Peace Dollar|1922|P"`
  - Keys format: `"Kennedy Half|1964|"` (no mint)
  - No title text in keys

### 3. **Price Store Schema Updated**
- **Contract:** Contract v1.2 Section 7 + Clarification Issue #5
- **Verification:**
  - Keys are normalized format
  - Values remain: `[price, qty, ema, timestamp, count]`
  - File: `price_store.json`

### 4. **Backward Compatibility**
- **Contract:** SRM v1.4, integration contracts
- **Verification:**
  - `silver_monitor.py` calls unchanged
  - Existing price_store.json migrated or cleared
  - No errors on cold start with old format

### 5. **Supported Coin Series**
- **Contract:** Clarification Issue #5, Series list
- **Verification:**
  - "Morgan Dollar"
  - "Peace Dollar"
  - "Kennedy Half"
  - "Walking Liberty Half"
  - "Franklin Half"
  - "Barber Half"
  - "Seated Liberty Half"

---

## Out of Scope

**Explicitly NOT included in Sprint 05.6:**

- ❌ EMA calculation changes
- ❌ Console output changes
- ❌ Email output changes
- ❌ Classification logic changes
- ❌ Diagnostic output changes
- ❌ New coin series beyond list above

---

## Integration Points

### `parser_listings.py` → `price_store.py`

**New function in parser:**
```python
def extract_coin_metadata(title: str) -> dict:
    """
    Extract normalized coin metadata from title.
    
    Returns:
        {
            "series": str,  # e.g., "Morgan Dollar"
            "year": str,    # e.g., "1881"
            "mint": str     # e.g., "CC" or ""
        }
    """
```

**Usage in silver_monitor:**
```python
for listing in dict_listings:
    metadata = parser_listings.extract_coin_metadata(listing["title"])
    listing["coin_metadata"] = metadata
```

---

### `price_store.py` Key Generation

**Old format:**
```python
key = listing["title"][:100]  # Title-based
```

**New format:**
```python
metadata = listing.get("coin_metadata", {})
series = metadata.get("series", "")
year = metadata.get("year", "")
mint = metadata.get("mint", "")

if series and year:
    key = f"{series}|{year}|{mint}"
else:
    key = None  # Skip invalid listings
```

---

## Parsing Rules (Contract Clarification Issue #5)

### Coin Series Detection:
- "Morgan" + "Dollar" → "Morgan Dollar"
- "Peace" + "Dollar" → "Peace Dollar"
- "Kennedy" + ("Half" or "50") → "Kennedy Half"
- "Walking Liberty" + ("Half" or "50") → "Walking Liberty Half"
- "Franklin" + ("Half" or "50") → "Franklin Half"
- "Barber" + ("Half" or "50") → "Barber Half"
- "Seated" + ("Half" or "50") → "Seated Liberty Half"

### Year Extraction:
- Pattern: `\b(1[7-9]\d{2}|20\d{2})\b` (1700-2099)
- Match first valid 4-digit year in title

### Mint Mark Extraction:
- Pattern: `\b([PDSOC]{1,2})\b` after year
- CC = Carson City (two letters)
- P/D/S/O = Single letter mints
- Empty string if no mint found

---

## Example Transformations

**Input Title:** `"1881 CC MORGAN DOLLAR GSA MS62 OLD Soap Box..."`
**Output Key:** `"Morgan Dollar|1881|CC"`

**Input Title:** `"1922 PEACE SILVER DOLLAR- UNCIRCULATED"`
**Output Key:** `"Peace Dollar|1922|"`

**Input Title:** `"1964 Kennedy Half Dollar"`
**Output Key:** `"Kennedy Half|1964|"`

**Input Title:** `"Walking Liberty Half 1942 D"`
**Output Key:** `"Walking Liberty Half|1942|D"`

---

## Migration Strategy

**Option 1: Clear old data**
- Delete existing `price_store.json`
- Start fresh with normalized keys

**Option 2: Migrate existing data**
- Parse old keys (titles)
- Extract metadata
- Rebuild store with new keys

**RECOMMENDATION:** Option 1 (clear old data) - simpler, Sprint 06.1 just completed so limited data loss

---

## Success Criteria

**Sprint 05.6 PASSES if:**

✅ Parser extracts coin metadata correctly  
✅ Keys format: `"Series|Year|Mint"`  
✅ All 7 coin series supported  
✅ Year extraction works (1794-2099)  
✅ Mint marks extracted correctly  
✅ price_store.json uses normalized keys  
✅ No changes to silver_monitor.py integration  
✅ Cold start works (no errors)

**Sprint 05.6 FAILS if:**

❌ Keys still contain title text  
❌ Metadata extraction fails  
❌ Unsupported coin series in list  
❌ Integration with silver_monitor broken  
❌ price_store.json format invalid

---

## Handoff Package

**To Build Studio (Chat C):**

1. This Sprint Plan (Sprint_05.6_Plan.md)
2. Contract Packet v1.2 + Clarification Issue #5
3. SRM v1.4
4. Source files:
   - `parser_listings.py` (modify)
   - `price_store.py` (modify)
   - `silver_monitor.py` (reference only)

**Expected Deliverables:**

1. `parser_listings.py` (modified - add metadata extraction)
2. `price_store.py` (modified - normalized key format)

---

**Sprint 05.6 Plan — Ready for Handoff**  
**Approved:** January 6, 2026  
**Authority:** Contract Vault Ruling + PM

---

**END OF SPRINT 05.6 PLAN**
